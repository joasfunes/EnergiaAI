"""Runtime local 05.3. SQLite para historial y perfil, con ciclos de vida controlados."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from energia_ai.agent.full_agent import SYSTEM_PROMPT, herramientas_energia_ai
from energia_ai.agent.inventory_tools import crear_tools_inventario
from energia_ai.agent.local_llm import crear_modelo
from energia_ai.services.home_inventory import InventarioHogar, validar_hogar_id

PROMPT_ANTERIOR = """- Si el usuario agrega un electrodoméstico, no afirmes que existe un inventario
  persistente: esta etapa conserva solo el historial del thread en RAM.
"""

PROMPT_INVENTARIO = """
INVENTARIO PERSISTENTE DEL HOGAR:
- consultar_inventario: consultá siempre los datos reales antes de afirmar qué equipos
  están registrados o calcular consumos basados en el inventario.
- El inventario se administra EXCLUSIVAMENTE desde la sección "Mis electrodomésticos"
  de Streamlit. No disponés de herramientas para registrar, editar ni eliminar equipos.
- Si te piden guardar o modificar electrodomésticos por chat, explicá cómo hacerlo
  desde esa sección; no afirmes que realizaste cambios.
- El hogar activo está fijado por la aplicación: no solicites ni inventes hogar_id.
- Las herramientas son la fuente de verdad. El historial no sustituye al inventario.
- Para calcular consumos o simular ahorros, recuperá primero el inventario y llamá
  las herramientas energéticas; no inventes potencias u horas ausentes.
"""


@dataclass(frozen=True)
class RuntimeEnergiaAI:
    agente: Any
    repositorio: InventarioHogar
    hogar_id: str
    archivo_historial: Path
    archivo_inventario: Path


def crear_agente_persistente(*, checkpointer: Any, repositorio: InventarioHogar,
                             hogar_id: str, modelo: Any = None) -> Any:
    """Crea agente con 4 herramientas energéticas + 1 consulta de inventario."""
    from langchain.agents import create_agent

    tools = list(herramientas_energia_ai()) + list(crear_tools_inventario(repositorio, hogar_id))
    return create_agent(
        model=modelo if modelo is not None else crear_modelo(),
        tools=tools, system_prompt=SYSTEM_PROMPT.replace(PROMPT_ANTERIOR, "") + PROMPT_INVENTARIO,
        checkpointer=checkpointer,
    )


@contextmanager
def abrir_runtime_persistente(*, hogar_id: str, carpeta_estado: str | Path = "data/state",
                              periodo_dias: int = 60, modelo: Any = None) -> Iterator[RuntimeEnergiaAI]:
    """Mantiene abierto SqliteSaver DURANTE toda la sesión de chat."""
    validar_hogar_id(hogar_id)
    from langgraph.checkpoint.sqlite import SqliteSaver
    carpeta = Path(carpeta_estado)
    carpeta.mkdir(parents=True, exist_ok=True)
    historial = carpeta / "conversaciones.sqlite3"
    inventario = carpeta / "inventario.sqlite3"
    repo = InventarioHogar(inventario)
    repo.asegurar_hogar(hogar_id, periodo_dias=periodo_dias)

    # from_conn_string es context manager, no constructor directo.
    with SqliteSaver.from_conn_string(str(historial)) as saver:
        saver.setup()
        agente = crear_agente_persistente(checkpointer=saver, repositorio=repo,
                                         hogar_id=hogar_id, modelo=modelo)
        yield RuntimeEnergiaAI(agente=agente, repositorio=repo, hogar_id=hogar_id,
                               archivo_historial=historial, archivo_inventario=inventario)
