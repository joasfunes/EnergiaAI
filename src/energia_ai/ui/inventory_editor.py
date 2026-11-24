"""Normalización de la tabla editable sin depender de Streamlit ni del LLM."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from energia_ai.services.consumption import Electrodomestico

CAMPOS = ("id", "nombre", "potencia_watts", "horas_efectivas_por_dia",
          "dias_de_uso", "cantidad")


def _numero_texto(value: Any, campo: str) -> str:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{campo}: número inválido")
    texto = str(value).strip().replace(",", ".")
    try:
        n = Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(f"{campo}: número inválido") from exc
    if not n.is_finite():
        raise ValueError(f"{campo}: número no finito")
    return str(n)


def _entero(value: Any, campo: str) -> int:
    n = Decimal(_numero_texto(value, campo))
    if n != n.to_integral_value():
        raise ValueError(f"{campo}: debe ser un entero")
    return int(n)


def normalizar_tabla(filas: list[Mapping[str, Any]], *, periodo_dias: int) -> list[dict[str, Any]]:
    """Valida toda la tabla, sin eliminar filas incompletas silenciosamente."""
    if len(filas) > 30:
        raise ValueError("Máximo 30 electrodomésticos por hogar")
    resultado = []
    ids: set[str] = set()
    for numero, fila in enumerate(filas, 1):
        try:
            equipo = Electrodomestico(
                id=str(fila.get("id", "")).strip(),
                nombre=str(fila.get("nombre", "")).strip(),
                potencia_watts=_numero_texto(fila.get("potencia_watts"), "potencia_watts"),
                horas_efectivas_por_dia=_numero_texto(fila.get("horas_efectivas_por_dia"), "horas_efectivas_por_dia"),
                dias_de_uso=_entero(fila.get("dias_de_uso"), "dias_de_uso"),
                cantidad=_entero(fila.get("cantidad"), "cantidad"),
            )
            if equipo.dias_de_uso > periodo_dias:
                raise ValueError("dias_de_uso supera el período del hogar")
            if equipo.id in ids:
                raise ValueError("ID duplicado")
            ids.add(equipo.id)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Fila {numero}: {exc}") from exc
        resultado.append({"id": equipo.id, "nombre": equipo.nombre,
                          "potencia_watts": str(equipo.potencia_watts),
                          "horas_efectivas_por_dia": str(equipo.horas_efectivas_por_dia),
                          "dias_de_uso": equipo.dias_de_uso, "cantidad": equipo.cantidad})
    return resultado


def mostrar_editor_inventario(hogar_id: str, *, estado_dir: Any) -> None:
    """Página CRUD aislada del agente. Solo este método importa Streamlit."""
    import pandas as pd
    import streamlit as st
    from energia_ai.services.home_inventory import InventarioHogar

    repo = InventarioHogar(estado_dir / "inventario.sqlite3")
    repo.asegurar_hogar(hogar_id, periodo_dias=60)
    clave = f"inventario_tabla_base_{hogar_id}"
    if clave not in st.session_state:
        st.session_state[clave] = repo.consultar(hogar_id)
    original = st.session_state[clave]

    st.subheader("Mis electrodomésticos")
    flash = f"inventario_guardado_{hogar_id}"
    if flash in st.session_state:
        st.success(st.session_state.pop(flash))
    revision = f"inventario_editor_rev_{hogar_id}"
    st.session_state.setdefault(revision, 0)
    st.caption("Agregá filas, editá sus valores o eliminá filas desde la tabla. "
               "Los cambios solo se aplican cuando presionás Guardar. No se utiliza Qwen.")
    st.info(f"Hogar: {hogar_id} · Período: {original['periodo_dias']} días · "
            "Máximo 30 equipos. Eliminaciones y ediciones se guardan juntas.")

    datos = pd.DataFrame(original["equipos"], columns=CAMPOS)
    if datos.empty:
        datos = pd.DataFrame({"id": pd.Series(dtype="str"),
                              "nombre": pd.Series(dtype="str"),
                              "potencia_watts": pd.Series(dtype="float64"),
                              "horas_efectivas_por_dia": pd.Series(dtype="float64"),
                              "dias_de_uso": pd.Series(dtype="int64"),
                              "cantidad": pd.Series(dtype="int64")})
    else:
        for campo in ("potencia_watts", "horas_efectivas_por_dia"):
            datos[campo] = datos[campo].astype(float)
    editada = st.data_editor(
        datos, hide_index=True, num_rows="dynamic", use_container_width=True,
        key=f"inventario_editor_{hogar_id}_{original['version']}_{st.session_state[revision]}",
        column_config={
            "id": st.column_config.TextColumn("ID único", help="1–32 letras, números, _ o -", required=True),
            "nombre": st.column_config.TextColumn("Electrodoméstico", required=True),
            "potencia_watts": st.column_config.NumberColumn("Potencia (W)", min_value=0.01, max_value=20000.0, step=1.0, required=True),
            "horas_efectivas_por_dia": st.column_config.NumberColumn("Horas/día", min_value=0.0, max_value=24.0, step=0.05, format="%.2f", required=True),
            "dias_de_uso": st.column_config.NumberColumn("Días de uso", min_value=0, max_value=original["periodo_dias"], step=1, required=True),
            "cantidad": st.column_config.NumberColumn("Cantidad", min_value=1, max_value=30, step=1, required=True),
        },
    )

    col_guardar, col_descartar = st.columns(2)
    if col_guardar.button("💾 Guardar tabla", type="primary", use_container_width=True):
        try:
            filas = normalizar_tabla(editada.to_dict(orient="records"), periodo_dias=original["periodo_dias"])
            repo.reemplazar_equipos(hogar_id, equipos=filas, version_esperada=original["version"])
        except ValueError as exc:
            st.error(f"No se guardó ningún cambio: {exc}")
        else:
            st.session_state.pop(clave, None)
            st.session_state[revision] += 1
            st.session_state[flash] = f"Inventario guardado: {len(filas)} equipos."
            st.rerun()
    if col_descartar.button("Descartar y recargar", use_container_width=True):
        st.session_state.pop(clave, None)
        st.session_state[revision] += 1
        st.rerun()

    consumo = repo.consumo_inventario(hogar_id)
    st.metric("Equipos guardados", repo.consultar(hogar_id)["cantidad_equipos"])
    if consumo.get("consumo_total_kwh") is not None:
        st.metric("Consumo estimado de los equipos guardados", f"{consumo['consumo_total_kwh']} kWh")
    st.caption("El consumo de estos equipos no tiene que coincidir con la factura del hogar.")
