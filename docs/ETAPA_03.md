# Etapa 03 — Motor energético y herramientas

**Estado:** etapa en desarrollo. **Subetapa 03.1:** servicio `calcular_consumo` y adaptador LangChain listos para validar en Windows.

## Alcance y orden

- 03.1: consumo por equipo (kWh), validaciones y tool `calcular_consumo`. **Este paquete**.
- 03.2: servicio `consultar_tarifa`, lectura de catálogo Python en RAM. Se definirá explícitamente el manejo sin SEF y de cobertura antes de calcular dinero.
- 03.3: `simular_ahorro`, comparación energética y económica *solo* para regímenes totalmente definidos. No inventar tasas, impuestos ni reglas de SEF.
- 03.4: pruebas de integración de las tres tools. La integración con `create_agent` y el LLM será en la Etapa 06.

## Distinción esencial

`consumption.py` = **lógica del negocio, Python puro**. `consumption_tool.py` = **adaptador LangChain** que admite argumentos estructurados y expone un schema para el LLM. El modelo NO hace las cuentas.

El cálculo de potencia constante es `cantidad * potencia_watts * horas_efectivas_por_dia * dias_de_uso / 1000` en kWh. El tiempo informado es tiempo efectivo a la potencia modelada. No confundir las 24 horas enchufada de una heladera con 24 horas de compresor a potencia nominal.

## Contrato de entrada

```json
{
  "periodo_dias": 30,
  "equipos": [
    {
      "id": "tv_1",
      "nombre": "Televisor",
      "potencia_watts": 100,
      "horas_efectivas_por_dia": 5,
      "dias_de_uso": 20,
      "cantidad": 1
    }
  ]
}
```

ID estable y único por equipo. Requiere 1–30 equipos; potencia finita en (0,20000] W; horas efectivas en [0,24]; días de uso entre 0 y el período; cantidad entera entre 1 y 30. `periodo_dias` entre 1 y 366.

## Contrato de salida

```json
{
  "estado": "ok",
  "periodo_dias": 30,
  "consumo_total_kwh": "10.0000",
  "equipos": [
    {"id": "tv_1", "nombre": "Televisor", "cantidad": 1, "consumo_kwh": "10.0000"}
  ],
  "metodo": "potencia_constante_estimada",
  "advertencias": ["...supuestos...", "...horas efectivas...", "...sin costo monetario..."]
}
```

Los números decimales de salida viajan como cadenas para evitar pérdida de precisión y se muestran con 4 decimales. La tool devuelve `{estado:"error", codigo:"DATOS_INVALIDOS", mensaje:"..."}` para errores de dominio. Si falta un campo o el esquema JSON no coincide, Pydantic puede rechazar antes de ejecutar la tool; el agente pedirá nuevamente datos.

## Instalación incremental en PowerShell

Desde raíz `energia-ai` (sin sobrescribir el código previo):

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\demo_consumption.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para probar **la tool real** de LangChain (necesita internet solo al instalar paquetes):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-tools.txt
.\.venv\Scripts\python.exe scripts\demo_consumption_tool.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Pruebas anteriores: 26. Nuevas: 18 de servicio + 2 de adaptador = 46 totales (sin paquetes de LangChain disponibles, las 2 últimas aparecen como `skipped`, no `OK` completo del adaptador). No afirmar que el adaptador fue validado hasta ejecutarlo con `langchain-core` instalado.

## Criterios de aceptación

1. Demo determinística devuelve 120 kWh del aire, 10 kWh del TV y 130 kWh totales.
2. LangChain `calcular_consumo.invoke(...)` devuelve 10 kWh del TV en el ejemplo y declara correctamente su `name`.
3. Los casos negativos y datos imposibles producen errores controlados.
4. No se calcula ningún precio ni importe de factura desde esta tool.
5. Las pruebas anteriores continúan pasando, y se registra el nuevo commit.

## Trazabilidad

- HU-01: consumo por electrodoméstico.
- Futuras HU-02 y HU-04: consulta de tarifas y simulación de ahorro.
- Fuentes: la fórmula es física elemental (Wh / 1000 = kWh). Los datos tarifarios siguen sin modificarse en `tariff_catalog.py`.
- Fecha objetivo de presentación: 27 de noviembre de 2026.
