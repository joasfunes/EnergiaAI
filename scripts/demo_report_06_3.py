"""Crea PDF de muestra sin LLM, desde servicios reales de consumo y ahorro.

Ejecutar desde la raíz: python scripts/demo_report_06_3.py
Es una DEMOSTRACIÓN: no representa una factura ni recupera consejos RAG.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from pathlib import Path

from energia_ai.services.consumption import Electrodomestico
from energia_ai.services.savings import simular_ahorro_escenarios
from energia_ai.services.tariffs import consultar_tarifa_catalogo
from energia_ai.reporting.pdf_report import generar_informe_pdf
from energia_ai.reporting.extraction import _validar_simulacion


def main():
    original = Electrodomestico('aire_1', 'Aire acondicionado', Decimal('1500'),Decimal('5'),10)
    propuesto = Electrodomestico('aire_1', 'Aire acondicionado',Decimal('1500'),Decimal('3'),10)
    tarifa = consultar_tarifa_catalogo(distribuidora='EDEMSA', fecha=date(2026,11,15),
                                      consumo_kwh_bimestral=350,regimen='SIN_SEF')
    datos = simular_ahorro_escenarios(periodo_dias=60,equipos_actuales=[original],
        equipos_propuestos=[propuesto],consumo_hogar_bimestral_kwh=350,tarifa_consultada=tarifa)
    analisis = _validar_simulacion(datos)
    analisis['generado_en'] = '2026-11-23 · DEMO de funcionamiento'
    analisis['evidencias_rag'] = []  # No inventamos fragmentos que no se recuperaron.
    pdf = generar_informe_pdf(analisis)
    destino = Path('data/processed/reports/demo_06_3.pdf')
    destino.parent.mkdir(parents=True,exist_ok=True)
    destino.write_bytes(pdf)
    print(f'Informe de demostración: {destino} ({len(pdf)} bytes)')
    print('Ahorro kWh:',analisis['ahorro_kwh'])
    print('Importe disponible:',analisis['monetario_disponible'])
    print('No se generaron fuentes RAG ficticias ni facturas completas.')

if __name__ == '__main__':
    main()
