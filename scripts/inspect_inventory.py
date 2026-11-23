"""Inspección determinística del perfil, sin Qwen ni streaming."""
from __future__ import annotations
import argparse
import json
from energia_ai.services.home_inventory import InventarioHogar


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hogar-id", default="hogar_demo")
    parser.add_argument("--archivo", default="data/state/inventario.sqlite3")
    args = parser.parse_args()
    repo = InventarioHogar(args.archivo)
    print(json.dumps(repo.consultar(args.hogar_id), ensure_ascii=False, indent=2))
    print("Consumo:", json.dumps(repo.consumo_inventario(args.hogar_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
