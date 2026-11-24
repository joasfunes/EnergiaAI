"""Extrae evidencia REAL de ToolMessages; no analiza ni confía en texto del LLM.

Solo reúne mensajes de UNA interacción del usuario. No combina una tarifa
antigua con una simulación posterior, ni inventa fuentes RAG ausentes.
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Sequence
import json
import math

from energia_ai.agent.session import configuracion_thread
from energia_ai.data.tariff_catalog import CATALOGO_EDEMSA_221_2026


class InformeNoDisponible(ValueError):
    """No hay un análisis verificable para producir un PDF."""


FUENTES_APROBADAS = {
    'ARG-RES-2024': 'https://www.argentina.gob.ar/sites/default/files/guia_residencial_enereficiente.pdf',
    'EPRE-INV-2022': 'https://epremendoza.gob.ar/consejos-para-ahorrar-energia-en-el-invierno/',
    'EPRE-VER-2025': 'https://epremendoza.gob.ar/ola-de-calor-recomendaciones-para-un-uso-eficiente-y-racional-de-la-energia/',
}


def _decimal(value: Any, key: str, *, allow_negative: bool = False) -> Decimal:
    if value is None or isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise InformeNoDisponible(f'Falta un valor numérico válido: {key}')
    try:
        n = Decimal(str(value))
    except InvalidOperation as exc:
        raise InformeNoDisponible(f'Número inválido: {key}') from exc
    if not n.is_finite() or (n < 0 and not allow_negative) or abs(n) > Decimal('1000000000000'):
        raise InformeNoDisponible(f'Valor fuera de rango: {key}')
    return n


def _parse_tool(m: Any) -> tuple[str, dict[str, Any]] | None:
    if getattr(m, 'type', None) not in {'tool', 'ToolMessage'}:
        return None
    nombre = getattr(m, 'name', None)
    if not isinstance(nombre, str) or nombre not in {'simular_ahorro', 'buscar_consejos'}:
        return None
    contenido = getattr(m, 'content', None)
    if isinstance(contenido, dict):
        salida = contenido
    elif isinstance(contenido, str):
        try:
            salida = json.loads(contenido)
        except (TypeError, ValueError):
            return None
    else:
        return None
    return (nombre, salida) if isinstance(salida, dict) else None


def _equipos(s: Any, campo: str) -> tuple[list[dict[str, str]], Decimal]:
    if not isinstance(s, dict) or s.get('estado') != 'ok':
        raise InformeNoDisponible(f'{campo}: el servicio no confirmó un cálculo válido')
    registros = s.get('equipos')
    if not isinstance(registros, list) or not 1 <= len(registros) <= 30:
        raise InformeNoDisponible(f'{campo}: faltan electrodomésticos')
    equipos: list[dict[str, str]] = []
    total = Decimal('0')
    ids = set()
    for r in registros:
        if not isinstance(r, dict):
            raise InformeNoDisponible('Registro de equipo inválido')
        eid = r.get('id')
        nombre = r.get('nombre')
        if not isinstance(eid, str) or not eid or eid in ids or not isinstance(nombre, str) or not nombre.strip():
            raise InformeNoDisponible('ID o nombre de equipo inválido/duplicado')
        ids.add(eid)
        kwh = _decimal(r.get('consumo_kwh'), 'consumo_kwh')
        total += kwh
        equipos.append({'id': eid[:32], 'nombre': nombre.strip()[:100],
                        'consumo_kwh': str(kwh)})
    declarado = _decimal(s.get('consumo_total_kwh'), 'consumo_total_kwh')
    if abs(total - declarado) > Decimal('0.001'):
        raise InformeNoDisponible(f'{campo}: total incoherente con el detalle de equipos')
    return equipos, declarado


def _seguro_texto(v: Any, limite: int = 450) -> str:
    return ' '.join(v.split())[:limite] if isinstance(v, str) else ''


def _validar_simulacion(sim: dict[str, Any]) -> dict[str, Any]:
    if sim.get('estado') != 'ok' or sim.get('tipo_resultado') != 'comparacion_de_escenarios_no_factura':
        raise InformeNoDisponible('La tool simular_ahorro no devolvió una simulación válida')
    periodo = sim.get('periodo_dias')
    if isinstance(periodo, bool) or not isinstance(periodo, int) or not 1 <= periodo <= 366:
        raise InformeNoDisponible('Período inválido')
    actuales, total_actual = _equipos(sim.get('escenario_actual'), 'escenario_actual')
    propuestos, total_nuevo = _equipos(sim.get('escenario_propuesto'), 'escenario_propuesto')
    if {x['id'] for x in actuales} != {x['id'] for x in propuestos}:
        raise InformeNoDisponible('Los equipos no coinciden entre escenarios')
    ahorro = _decimal(sim.get('ahorro_kwh'), 'ahorro_kwh', allow_negative=True)
    if abs(total_actual - total_nuevo - ahorro) > Decimal('0.001'):
        raise InformeNoDisponible('El ahorro no coincide con la diferencia de escenarios')
    porcentaje = sim.get('ahorro_porcentual_equipos')
    if porcentaje is not None:
        pct = _decimal(porcentaje, 'ahorro_porcentual_equipos', allow_negative=True)
        if total_actual > 0 and abs((ahorro / total_actual * 100) - pct) > Decimal('0.02'):
            raise InformeNoDisponible('El porcentaje es incoherente')
    else:
        pct = None
    disponible = sim.get('estimacion_monetaria_disponible') is True
    pesos = sim.get('ahorro_componente_variable_estimado_ars')
    fuente_tarifa = sim.get('fuente_tarifa')
    if disponible:
        importe = _decimal(pesos, 'ahorro_componente_variable_estimado_ars', allow_negative=True)
        if (not isinstance(fuente_tarifa, dict)
            or fuente_tarifa.get('estado_revision') != 'CONTRASTADO_CON_PDF_LOCAL'
            or fuente_tarifa.get('organismo') != 'EPRE Mendoza'
            or fuente_tarifa.get('url') != CATALOGO_EDEMSA_221_2026.fuente_url
            or fuente_tarifa.get('resolucion') != CATALOGO_EDEMSA_221_2026.resolucion):
            # No monetizar cuando no puede justificarse la fuente oficial.
            disponible, importe = False, None
    else:
        importe = None
    return {
        'periodo_dias': periodo, 'equipos_actuales': actuales, 'equipos_propuestos': propuestos,
        'consumo_actual_kwh': str(total_actual), 'consumo_propuesto_kwh': str(total_nuevo),
        'ahorro_kwh': str(ahorro), 'ahorro_porcentual': str(pct) if pct is not None else None,
        'consumo_hogar_actual_kwh': sim.get('consumo_hogar_bimestral_actual_kwh'),
        'consumo_hogar_proyectado_kwh': sim.get('consumo_hogar_bimestral_proyectado_kwh'),
        'categoria_actual': sim.get('categoria_actual'), 'categoria_proyectada': sim.get('categoria_proyectada'),
        'monetario_disponible': disponible, 'ahorro_variable_ars': str(importe) if importe is not None else None,
        'fuente_tarifa': fuente_tarifa if disponible else None,
        'motivo_sin_dinero': _seguro_texto(sim.get('motivo_sin_estimacion_monetaria'), 350)
            if not disponible else '',
        'advertencias': [_seguro_texto(x, 300) for x in sim.get('advertencias', [])[:8] if isinstance(x, str)]
            if isinstance(sim.get('advertencias'), list) else [],
    }


def _consejos(datos: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(datos, dict) or datos.get('estado') != 'ok':
        return []
    registros = datos.get('resultados')
    if not isinstance(registros, list):
        return []
    salida = []
    vistos = set()
    for r in registros[:5]:
        if not isinstance(r, dict):
            continue
        fid, url = r.get('fuente_id'), r.get('url')
        if not isinstance(fid, str) or FUENTES_APROBADAS.get(fid) != url:
            continue
        texto = _seguro_texto(r.get('texto'), 480)
        if not texto:
            continue
        clave = (fid, texto)
        if clave in vistos:
            continue
        vistos.add(clave)
        pagina = r.get('pagina')
        if isinstance(pagina, bool) or not isinstance(pagina, int) or not 1 <= pagina <= 1000:
            pagina = None
        salida.append({'fuente_id': fid, 'url': url,
                       'documento': _seguro_texto(r.get('documento'), 120) or fid,
                       'pagina': pagina, 'texto': texto})
        if len(salida) == 3:
            break
    return salida


def extraer_ultimo_analisis(mensajes: Sequence[Any]) -> dict[str, Any]:
    """Extrae último turno con simulación válida. NO mezcla tools entre turnos.

    Soporta reabrir una conversación persistente y exportar un análisis anterior.
    """
    if not isinstance(mensajes, (list, tuple)):
        raise InformeNoDisponible('No existe un historial de mensajes')
    turnos: list[list[Any]] = []
    for m in mensajes:
        tipo = getattr(m, 'type', None)
        if tipo in {'human', 'HumanMessage'}:
            turnos.append([])
        elif turnos:
            turnos[-1].append(m)
    for turno in reversed(turnos):
        decodificados = [t for m in turno if (t := _parse_tool(m)) is not None]
        simulaciones = [d for nombre, d in decodificados if nombre == 'simular_ahorro' and d.get('estado') == 'ok']
        if not simulaciones:
            continue
        analisis = _validar_simulacion(simulaciones[-1])
        fuentes = [d for nombre, d in decodificados if nombre == 'buscar_consejos' and d.get('estado') == 'ok']
        analisis['evidencias_rag'] = _consejos(fuentes[-1]) if fuentes else []
        analisis['origen'] = 'resultados reales de tools de un mismo turno'
        analisis['generado_en'] = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %z')
        return analisis
    raise InformeNoDisponible('No hay una simulación válida en la conversación. Pedí al agente un análisis con simular_ahorro.')


def extraer_desde_agente(agente: Any, thread_id: str) -> dict[str, Any]:
    estado = agente.get_state(configuracion_thread(thread_id))
    valores = getattr(estado, 'values', None)
    if not isinstance(valores, dict):
        raise InformeNoDisponible('No se encontró estado de conversación')
    return extraer_ultimo_analisis(valores.get('messages', []))
