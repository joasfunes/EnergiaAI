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
INVENTARIO PERSISTENTE DEL HOGAR (Etapa 05.3):
- registrar_electrodomestico: usar SOLO cuando el usuario pida guardar un equipo nuevo
  y se conozcan id, nombre, potencia W, horas efectivas/día y días de uso.
  No inferir potencia, no registrar datos ambiguos, ni modificar equipos existentes.
- consultar_inventario: usar para verificar qué equipos están guardados y al
  calcular un consumo de todos los equipos; devolver exactamente datos registrados.
- El hogar activo está fijado por la aplicación; nunca solicites ni inventes hogar_id.
- Si falta un dato indispensable, preguntalo, NO lo inventes.
- Las herramientas son la fuente de verdad. El historial NO sustituye el inventario.
- Si el usuario pide registrar y luego consultar, ejecutá primero
  registrar_electrodomestico, ESPERÁ su resultado y recién después consultar_inventario.
  Nunca solicites ambas herramientas en paralelo. Una respuesta anterior al registro
  NO demuestra el inventario actualizado.
- registrar_electrodomestico ya devuelve inventario_actualizado tras la escritura:
  si existe una lectura anterior obsoleta, confiá en este resultado posterior.
- No afirmes que guardaste un equipo si la tool devolvió estado=error.
- Si el usuario solicita registrar un equipo y después
consultar el inventario, respeta este orden obligatorio:
  1. Ejecuta registrar_electrodomestico.
  2. Espera y verifica su resultado.
  3. Ejecuta consultar_inventario.
  4. Responde usando el inventario actualizado.

- No solicites ambas herramientas en paralelo.
- Nunca presentes una consulta anterior al registro
como si fuera el estado actualizado del inventario.

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
    """Crea agente con 4 herramientas previas + 2 de inventario (no cambia 05.2)."""
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
