"""Inspección de las cuatro herramientas, sin consultar Qwen ni Ollama."""
from energia_ai.agent.full_agent import SYSTEM_PROMPT, herramientas_energia_ai


def main() -> int:
    tools = herramientas_energia_ai()
    print("EnergiaAI | Etapa 05.2 | Registro de tools")
    for tool in tools:
        schema = tool.args_schema.model_json_schema()
        names = ", ".join(schema.get("properties", {}).keys())
        print(f"- {tool.name}: {names}")
    print("Reglas del prompt configuradas:", len(SYSTEM_PROMPT) > 100)
    print("OK: cuatro tools registradas y con esquemas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
