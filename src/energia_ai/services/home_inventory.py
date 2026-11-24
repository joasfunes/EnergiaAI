"""Inventario local de equipos: datos de negocio persistentes, separado del historial LLM.

Solo para piloto monousuario. Para producción se requiere identidad/autorización reales.
"""
from __future__ import annotations

from contextlib import closing
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping

from energia_ai.services.consumption import Electrodomestico, calcular_consumo_equipos

_HOME_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


def validar_hogar_id(hogar_id: str) -> str:
    if not isinstance(hogar_id, str) or not _HOME_ID.fullmatch(hogar_id):
        raise ValueError("hogar_id: use de 1 a 80 caracteres ASCII alfanumericos, _ o -")
    return hogar_id


class InventarioHogar:
    """Repositorio SQLite; cada operación usa su propia conexión y transacción."""

    def __init__(self, db_path: str | Path):
        path = Path(db_path)
        if path.name in {"", ".", ".."} or str(path) == ":memory:":
            raise ValueError("Se requiere un archivo SQLite local")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path
        self._crear_esquema()

    def _abrir(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _crear_esquema(self) -> None:
        with closing(self._abrir()) as conn, conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS hogares (
                hogar_id TEXT PRIMARY KEY,
                periodo_dias INTEGER NOT NULL CHECK(periodo_dias BETWEEN 1 AND 366)
            );
            CREATE TABLE IF NOT EXISTS equipos (
                hogar_id TEXT NOT NULL,
                equipo_id TEXT NOT NULL,
                nombre TEXT NOT NULL,
                potencia_watts TEXT NOT NULL,
                horas_efectivas_por_dia TEXT NOT NULL,
                dias_de_uso INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                PRIMARY KEY(hogar_id, equipo_id),
                FOREIGN KEY(hogar_id) REFERENCES hogares(hogar_id)
            );
            """)

    def asegurar_hogar(self, hogar_id: str, *, periodo_dias: int = 60) -> None:
        validar_hogar_id(hogar_id)
        if isinstance(periodo_dias, bool) or not isinstance(periodo_dias, int) or not 1 <= periodo_dias <= 366:
            raise ValueError("periodo_dias: entero entre 1 y 366")
        with closing(self._abrir()) as conn, conn:
            conn.execute("INSERT OR IGNORE INTO hogares (hogar_id, periodo_dias) VALUES (?, ?)",
                         (hogar_id, periodo_dias))
            actual = conn.execute("SELECT periodo_dias FROM hogares WHERE hogar_id=?", (hogar_id,)).fetchone()
            if actual["periodo_dias"] != periodo_dias:
                raise ValueError("El hogar ya existe con otro periodo_dias; no se cambia silenciosamente")

    def registrar_equipo(self, hogar_id: str, *, id: str, nombre: str,
                         potencia_watts: str, horas_efectivas_por_dia: str,
                         dias_de_uso: int, cantidad: int = 1) -> dict[str, Any]:
        validar_hogar_id(hogar_id)
        equipo = Electrodomestico(id=id, nombre=nombre, potencia_watts=potencia_watts,
                                  horas_efectivas_por_dia=horas_efectivas_por_dia,
                                  dias_de_uso=dias_de_uso, cantidad=cantidad)
        with closing(self._abrir()) as conn, conn:
            fila = conn.execute("SELECT periodo_dias FROM hogares WHERE hogar_id=?", (hogar_id,)).fetchone()
            if fila is None:
                raise ValueError("Hogar no registrado")
            # Reutilizar validación de período; evita datos incompatibles en el inventario.
            calcular_consumo_equipos(periodo_dias=fila["periodo_dias"], equipos=[equipo])
            try:
                conn.execute("""INSERT INTO equipos
                    (hogar_id,equipo_id,nombre,potencia_watts,horas_efectivas_por_dia,dias_de_uso,cantidad)
                    VALUES (?,?,?,?,?,?,?)""", (hogar_id, equipo.id, equipo.nombre,
                    str(equipo.potencia_watts), str(equipo.horas_efectivas_por_dia),
                    equipo.dias_de_uso, equipo.cantidad))
            except sqlite3.IntegrityError as exc:
                raise ValueError("El equipo ya existe; no se sobrescribe sin confirmación") from exc
        return {"estado": "ok", "hogar_id": hogar_id, "equipo_id": equipo.id, "accion": "registrado"}

    def consultar(self, hogar_id: str) -> dict[str, Any]:
        validar_hogar_id(hogar_id)
        with closing(self._abrir()) as conn:
            hogar = conn.execute("SELECT periodo_dias FROM hogares WHERE hogar_id=?", (hogar_id,)).fetchone()
            if hogar is None:
                return {"estado": "error", "codigo": "HOGAR_DESCONOCIDO"}
            filas = conn.execute("""SELECT equipo_id,nombre,potencia_watts,horas_efectivas_por_dia,
                                dias_de_uso,cantidad FROM equipos WHERE hogar_id=? ORDER BY equipo_id""",
                                (hogar_id,)).fetchall()
        equipos = self._filas_desde_sql(filas)
        return {"estado": "ok", "hogar_id": hogar_id, "periodo_dias": hogar["periodo_dias"],
                "equipos": equipos, "cantidad_equipos": len(equipos),
                "version": self._version_inventario(hogar["periodo_dias"], equipos)}

    @staticmethod
    def _filas_desde_sql(filas: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [{"id": f["equipo_id"], "nombre": f["nombre"],
                 "potencia_watts": f["potencia_watts"],
                 "horas_efectivas_por_dia": f["horas_efectivas_por_dia"],
                 "dias_de_uso": f["dias_de_uso"], "cantidad": f["cantidad"]}
                for f in filas]

    @staticmethod
    def _version_inventario(periodo_dias: int, equipos: list[dict[str, Any]]) -> str:
        """Huella determinística para detectar ediciones desde una vista obsoleta."""
        canonic = json.dumps({"periodo_dias": periodo_dias, "equipos": equipos},
                             sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return sha256(canonic.encode("utf-8")).hexdigest()

    def reemplazar_equipos(self, hogar_id: str, *, equipos: list[Mapping[str, Any]],
                           version_esperada: str) -> dict[str, Any]:
        """Guarda una tabla completa en una sola transacción (altas, ediciones y bajas).

        Si otro proceso modificó el inventario desde que se abrió el editor,
        se cancela todo el lote en vez de sobrescribir datos sin avisar.
        """
        validar_hogar_id(hogar_id)
        if not isinstance(version_esperada, str) or len(version_esperada) != 64:
            raise ValueError("Falta la versión original del inventario; recargá la tabla")
        if not isinstance(equipos, list) or len(equipos) > 30:
            raise ValueError("El inventario admite como máximo 30 electrodomésticos")
        validados = []
        for i, fila in enumerate(equipos, start=1):
            if not isinstance(fila, Mapping):
                raise ValueError(f"Fila {i}: formato inválido")
            try:
                equipo = Electrodomestico(**{
                    campo: fila[campo] for campo in
                    ("id", "nombre", "potencia_watts", "horas_efectivas_por_dia",
                     "dias_de_uso", "cantidad")
                })
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Fila {i}: {exc}") from exc
            validados.append(equipo)
        if validados:
            # La validación de consumo también revisa período y IDs duplicados.
            # El período se consulta dentro de la transacción a continuación.
            ids = [x.id for x in validados]
            if len(ids) != len(set(ids)):
                raise ValueError("Hay IDs de electrodomésticos duplicados")

        with closing(self._abrir()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            hogar = conn.execute("SELECT periodo_dias FROM hogares WHERE hogar_id=?", (hogar_id,)).fetchone()
            if hogar is None:
                raise ValueError("Hogar no registrado")
            periodo = hogar["periodo_dias"]
            if validados:
                calcular_consumo_equipos(periodo_dias=periodo, equipos=validados)
            previas = conn.execute("""SELECT equipo_id,nombre,potencia_watts,
                horas_efectivas_por_dia,dias_de_uso,cantidad FROM equipos
                WHERE hogar_id=? ORDER BY equipo_id""", (hogar_id,)).fetchall()
            version_actual = self._version_inventario(periodo, self._filas_desde_sql(previas))
            if version_actual != version_esperada:
                raise ValueError("Inventario modificado en otra sesión; recargá antes de guardar")
            conn.execute("DELETE FROM equipos WHERE hogar_id=?", (hogar_id,))
            conn.executemany("""INSERT INTO equipos
                (hogar_id,equipo_id,nombre,potencia_watts,horas_efectivas_por_dia,dias_de_uso,cantidad)
                VALUES (?,?,?,?,?,?,?)""", [
                (hogar_id, e.id, e.nombre, str(e.potencia_watts),
                 str(e.horas_efectivas_por_dia), e.dias_de_uso, e.cantidad)
                for e in validados])
        return {"estado": "ok", "hogar_id": hogar_id, "cantidad_equipos": len(validados)}

    def consumo_inventario(self, hogar_id: str) -> dict[str, Any]:
        datos = self.consultar(hogar_id)
        if datos["estado"] != "ok":
            return datos
        if not datos["equipos"]:
            return {"estado": "sin_equipos", "hogar_id": hogar_id,
                    "periodo_dias": datos["periodo_dias"], "consumo_total_kwh": None}
        equipos = [Electrodomestico(**registro) for registro in datos["equipos"]]
        res = calcular_consumo_equipos(periodo_dias=datos["periodo_dias"], equipos=equipos)
        return {**res, "hogar_id": hogar_id}
