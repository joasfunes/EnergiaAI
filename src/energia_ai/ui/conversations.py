"""Índice local de conversaciones; el contenido se mantiene en el SqliteSaver.

Prototipo de UN SOLO USUARIO, sin autenticación. Nunca desplegar públicamente.
"""
from __future__ import annotations
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4

from energia_ai.services.home_inventory import validar_hogar_id
from energia_ai.agent.session import configuracion_thread


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class IndiceConversaciones:
    def __init__(self, ruta: str | Path):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._conexion()) as conn, conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS conversaciones_ui (
                thread_id TEXT PRIMARY KEY,
                hogar_id TEXT NOT NULL,
                titulo TEXT NOT NULL,
                creada_utc TEXT NOT NULL,
                ultima_utc TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversaciones_hogar ON conversaciones_ui(hogar_id, ultima_utc)")

    def _conexion(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.ruta), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def crear(self, hogar_id: str, *, titulo: str = "Nueva conversación") -> str:
        validar_hogar_id(hogar_id)
        if not isinstance(titulo, str) or not 1 <= len(titulo.strip()) <= 80:
            raise ValueError("Título inválido")
        identificador = "chat_" + uuid4().hex[:24]
        ahora = _utc()
        with closing(self._conexion()) as conn, conn:
            conn.execute("INSERT INTO conversaciones_ui VALUES (?,?,?,?,?)",
                         (identificador, hogar_id, titulo.strip(), ahora, ahora))
        return identificador

    def listar(self, hogar_id: str) -> list[dict[str, str]]:
        validar_hogar_id(hogar_id)
        with closing(self._conexion()) as conn:
            filas = conn.execute("""SELECT thread_id,hogar_id,titulo,creada_utc,ultima_utc
              FROM conversaciones_ui WHERE hogar_id=? ORDER BY ultima_utc DESC, thread_id DESC""",
              (hogar_id,)).fetchall()
        return [dict(f) for f in filas]

    def comprobar(self, hogar_id: str, thread_id: str) -> None:
        validar_hogar_id(hogar_id)
        configuracion_thread(thread_id)
        with closing(self._conexion()) as conn:
            fila = conn.execute("SELECT 1 FROM conversaciones_ui WHERE hogar_id=? AND thread_id=?",
                                (hogar_id, thread_id)).fetchone()
        if fila is None:
            raise ValueError("La conversación no pertenece al hogar activo")

    def actualizar(self, hogar_id: str, thread_id: str) -> None:
        self.comprobar(hogar_id, thread_id)
        with closing(self._conexion()) as conn, conn:
            conn.execute("UPDATE conversaciones_ui SET ultima_utc=? WHERE hogar_id=? AND thread_id=?",
                         (_utc(), hogar_id, thread_id))
