"""Pruebas de aceptación 06.4. Sin LLM, Ollama, ChromaDB ni navegador.

Prueban la auditoría de ToolMessages, consistencia de PDF y aislamiento
LOCAL de datos. No confundir estos tests con una prueba E2E real del agente.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
import json
from tempfile import TemporaryDirectory
import unittest

from energia_ai.quality.acceptance import (
    auditar_ultimo_turno, verificar_informe, verificar_preparacion,
    ARCHIVOS_OBLIGATORIOS,
)
from energia_ai.services.consumption import Electrodomestico
from energia_ai.services.savings import simular_ahorro_escenarios
from energia_ai.services.tariffs import consultar_tarifa_catalogo
from energia_ai.services.home_inventory import InventarioHogar
from energia_ai.ui.conversations import IndiceConversaciones
from energia_ai.reporting.extraction import InformeNoDisponible, FUENTES_APROBADAS


@dataclass
class Mensaje:
    type: str
    content: str
    name: str = ''


def tool(nombre, dato):
    return Mensaje('tool', json.dumps(dato, ensure_ascii=False), nombre)


def escenario_simulado():
    actual = Electrodomestico('aire_1', 'Aire acondicionado', Decimal('1500'), Decimal('5'), 10)
    propuesto = Electrodomestico('aire_1', 'Aire acondicionado', Decimal('1500'), Decimal('3'), 10)
    return simular_ahorro_escenarios(periodo_dias=60,
        equipos_actuales=[actual], equipos_propuestos=[propuesto])


def conversacion_con_simulacion():
    return [Mensaje('human', 'Simulá este escenario'),
            tool('simular_ahorro', escenario_simulado()),
            Mensaje('ai', 'Resultado del agente')]


class TestAuditoriaHerramientas(unittest.TestCase):
    def test_01_no_hay_turno_humano(self):
        r = auditar_ultimo_turno([], requeridas=['calcular_consumo'])
        self.assertEqual(r['estado'], 'revision_requerida')

    def test_02_solicitud_no_es_ejecucion(self):
        r = auditar_ultimo_turno([Mensaje('human','hola'),
            Mensaje('ai','Invocaré calcular_consumo')], requeridas=['calcular_consumo'])
        self.assertIn('faltan_tools_requeridas', r['alertas'])

    def test_03_herramienta_ejecutada_exitosamente(self):
        r = auditar_ultimo_turno([Mensaje('human','calcular'),
            tool('calcular_consumo', {'estado':'ok', 'consumo_total_kwh':'10.0000'})],
            requeridas=['calcular_consumo'])
        self.assertEqual(r['estado'], 'ok')

    def test_04_falta_tool_requerida(self):
        r = auditar_ultimo_turno([Mensaje('human','calcular'),
            tool('calcular_consumo', {'estado':'ok'})],
            requeridas=['calcular_consumo','consultar_tarifa'])
        self.assertEqual(r['faltantes'], ['consultar_tarifa'])

    def test_05_error_de_tool(self):
        r = auditar_ultimo_turno([Mensaje('human','calcular'),
            tool('simular_ahorro', {'estado':'error'})], requeridas=['simular_ahorro'])
        self.assertIn('tool_sin_exito', r['alertas'])

    def test_06_resultado_json_invalido(self):
        r = auditar_ultimo_turno([Mensaje('human','calcular'),
            Mensaje('tool', '{sin-json', 'consultar_tarifa')])
        self.assertIn('tool_sin_exito', r['alertas'])

    def test_07_tool_no_admitida(self):
        r = auditar_ultimo_turno([Mensaje('human','abrir'),
            tool('herramienta_desconocida', {'estado':'ok'})])
        self.assertIn('tool_desconocida', r['alertas'])

    def test_08_orden_inventario_incorrecto(self):
        r = auditar_ultimo_turno([Mensaje('human','registrá y consultá'),
            tool('consultar_inventario', {'estado':'ok'}),
            tool('registrar_electrodomestico', {'estado':'ok'})])
        self.assertIn('lectura_inventario_obsoleta', r['alertas'])

    def test_09_orden_inventario_correcto(self):
        r = auditar_ultimo_turno([Mensaje('human','registrá y consultá'),
            tool('registrar_electrodomestico', {'estado':'ok'}),
            tool('consultar_inventario', {'estado':'ok'})])
        self.assertEqual(r['estado'],'ok')

    def test_10_no_usa_tools_de_turnos_viejos(self):
        r = auditar_ultimo_turno([Mensaje('human','antes'),
            tool('calcular_consumo', {'estado':'ok'}), Mensaje('human','ahora')],
            requeridas=['calcular_consumo'])
        self.assertEqual(r['faltantes'], ['calcular_consumo'])

    def test_11_orden_de_varias_escrituras(self):
        r = auditar_ultimo_turno([Mensaje('human','varios'),
            tool('registrar_electrodomestico', {'estado':'ok'}),
            tool('consultar_inventario', {'estado':'ok'}),
            tool('registrar_electrodomestico', {'estado':'ok'})])
        self.assertIn('lectura_inventario_obsoleta',r['alertas'])

    def test_12_no_devolver_preguntas_ni_nombres(self):
        r = auditar_ultimo_turno([Mensaje('human','contraseña-de-prueba'),
            tool('registrar_electrodomestico', {'estado':'ok', 'nombre':'dato-privado'})])
        self.assertNotIn('contraseña-de-prueba', json.dumps(r))
        self.assertNotIn('dato-privado', json.dumps(r))

    def test_13_rechaza_nombre_requerido_desconocido(self):
        with self.assertRaises(ValueError):
            auditar_ultimo_turno([], requeridas=['abrir_caja_fuerte'])


class TestReproducibilidad(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_14_archivos_ausentes(self):
        r = verificar_preparacion(self.root)
        self.assertIn('archivos_ausentes', r['alertas'])

    def test_15_ejemplo_completo(self):
        for item in ARCHIVOS_OBLIGATORIOS:
            ruta = self.root / item
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text('prueba', encoding='utf-8')
        (self.root / '.gitignore').write_text('.env\ndata/state/\ndata/processed/\ndata/vectorstore/\n', encoding='utf-8')
        self.assertEqual(verificar_preparacion(self.root)['estado'], 'ok')

    def test_16_gitignore_sin_estado(self):
        (self.root / '.gitignore').write_text('.env\ndata/processed/\ndata/vectorstore/\n', encoding='utf-8')
        r = verificar_preparacion(self.root)
        self.assertFalse(r['exclusiones_git']['data/state/'])


class TestIntegracionResultados(unittest.TestCase):
    def test_17_pdf_solo_con_simulacion(self):
        with self.assertRaises(InformeNoDisponible):
            verificar_informe([Mensaje('human','hola'), Mensaje('ai', 'Ahorrás 30 kWh')])

    def test_18_pdf_real_y_kwh(self):
        r = verificar_informe(conversacion_con_simulacion())
        self.assertEqual(r['estado'], 'ok')
        self.assertEqual(r['ahorro_kwh'], '30.0000')
        self.assertGreaterEqual(r['paginas'], 1)

    def test_19_sin_rag_no_cita_fuentes(self):
        r = verificar_informe(conversacion_con_simulacion())
        self.assertEqual(r['cantidad_fuentes'], 0)

    def test_20_pdf_con_rag_aceptado(self):
        rag = {'estado':'ok','resultados':[{'fuente_id':'EPRE-INV-2022',
             'url':FUENTES_APROBADAS['EPRE-INV-2022'],
             'texto':'Mantener climatizados los ambientes utilizados',
             'documento':'Consejos invierno'}]}
        msgs = conversacion_con_simulacion()
        msgs.insert(1,tool('buscar_consejos',rag))
        self.assertEqual(verificar_informe(msgs)['cantidad_fuentes'], 1)

    def test_21_pdf_ignora_url_no_aprobada(self):
        rag = {'estado':'ok','resultados':[{'fuente_id':'EPRE-INV-2022',
             'url':'https://ejemplo-no-oficial.invalid/',
             'texto':'Cita externa'}]}
        msgs = conversacion_con_simulacion()
        msgs.insert(1,tool('buscar_consejos',rag))
        self.assertEqual(verificar_informe(msgs)['cantidad_fuentes'], 0)

    def test_22_no_mezcla_fuentes_de_otro_turno(self):
        rag = {'estado':'ok','resultados':[{'fuente_id':'EPRE-INV-2022',
             'url':FUENTES_APROBADAS['EPRE-INV-2022'], 'texto':'Consejos'}]}
        msgs = [Mensaje('human','RAG anterior'),tool('buscar_consejos',rag)] + conversacion_con_simulacion()
        self.assertEqual(verificar_informe(msgs)['cantidad_fuentes'], 0)

    def test_23_persistencia_y_aislamiento_local(self):
        with TemporaryDirectory() as td:
            db = Path(td) / 'inventario.sqlite3'
            repo = InventarioHogar(db)
            repo.asegurar_hogar('h1')
            repo.asegurar_hogar('h2')
            repo.registrar_equipo('h1', id='tv', nombre='TV', potencia_watts='100',
                                 horas_efectivas_por_dia='5', dias_de_uso=20)
            self.assertEqual(InventarioHogar(db).consultar('h1')['cantidad_equipos'],1)
            self.assertEqual(repo.consultar('h2')['cantidad_equipos'],0)

    def test_24_indice_no_confunde_hogares(self):
        with TemporaryDirectory() as td:
            indice = IndiceConversaciones(Path(td) / 'conversaciones_ui.sqlite3')
            t = indice.crear('h1')
            indice.comprobar('h1', t)
            with self.assertRaises(ValueError):
                indice.comprobar('h2', t)

    def test_25_tarifa_y_simulacion_consistentes(self):
        tarifa=consultar_tarifa_catalogo(distribuidora='EDEMSA',fecha=date(2026,11,15),
                consumo_kwh_bimestral=350,regimen='SIN_SEF')
        orig = Electrodomestico('a','Aire', Decimal('1500'), Decimal('5'), 10)
        prop = Electrodomestico('a','Aire', Decimal('1500'), Decimal('3'), 10)
        sim=simular_ahorro_escenarios(periodo_dias=60,equipos_actuales=[orig],
               equipos_propuestos=[prop], consumo_hogar_bimestral_kwh=350,
               tarifa_consultada=tarifa)
        self.assertEqual(sim['ahorro_kwh'],'30.0000')
        self.assertEqual(sim['consumo_hogar_bimestral_proyectado_kwh'],'320.0000')
        self.assertEqual(tarifa['categoria'],'R2')


if __name__ == '__main__':
    unittest.main()
