"""Pruebas de la evaluación 04.3 sin Ollama, ChromaDB ni LLM."""
import unittest

from energia_ai.rag.corpus import SOURCES
from energia_ai.rag.evaluation import (
    CASES, EvaluationCase, _revision_fragmento, evaluar_casos,
    metricas_automaticas, metricas_manuales,
)


def respuesta(source_index=1, texto="Recomendación concreta para un hogar.", estado="ok"):
    fuente = SOURCES[source_index]
    return {
        "estado": estado,
        "resultados": [{
            "texto": texto,
            "fuente_id": fuente.id,
            "url": fuente.official_url,
            "pagina": 1 if fuente.kind == "pdf" else None,
            "cita": fuente.title,
            "distancia_vectorial": 0.7,
        }],
        "advertencias": [],
    }


class TestEvaluacionRAG(unittest.TestCase):
    def setUp(self):
        self.caso = EvaluationCase("INV-T", "¿Cómo ahorrar calefacción?", SOURCES[1].id)
        self.ood = EvaluationCase("OOD-T", "¿Cómo instalar una impresora?", None, "fuera_de_dominio")

    def test_casos_oficiales_y_unicos(self):
        self.assertEqual(len(CASES), 10)
        self.assertEqual(len({c.id for c in CASES}), len(CASES))
        self.assertEqual(sum(c.tipo == "dominio" for c in CASES), 8)

    def test_rechaza_caso_sin_fuente(self):
        with self.assertRaises(ValueError):
            EvaluationCase("x", "consulta", "origen inventado")

    def test_rechaza_caso_ood_con_fuente(self):
        with self.assertRaises(ValueError):
            EvaluationCase("x", "consulta", SOURCES[0].id, "fuera_de_dominio")

    def test_valida_k_y_rechaza_booleanos(self):
        for k in [0, 6, True, 1.2]:
            with self.subTest(k=k), self.assertRaises(ValueError):
                evaluar_casos([self.caso], lambda q, k: respuesta(), k=k)

    def test_usa_la_consulta_y_k_de_la_tool(self):
        llamadas = []
        def fake(q, k):
            llamadas.append((q, k))
            return respuesta()
        reporte = evaluar_casos([self.caso], fake, k=3)
        self.assertEqual(llamadas, [(self.caso.consulta, 3)])
        self.assertEqual(reporte["casos"][0]["rango_primera_fuente_esperada"], 1)

    def test_calcula_source_hit_y_mrr(self):
        casos = [self.caso, EvaluationCase("VER-T", "¿Cómo ahorrar con calor?", SOURCES[2].id)]
        reporte = evaluar_casos(casos, lambda q, k: respuesta(1))
        metricas = metricas_automaticas(reporte)
        self.assertEqual(metricas["source_hit_at_k"], 0.5)
        self.assertEqual(metricas["source_mrr_at_k"], 0.5)

    def test_mrr_si_fuente_en_segunda_posicion(self):
        segunda = respuesta(1)["resultados"][0]
        primera = respuesta(2)["resultados"][0]
        reporte = evaluar_casos([self.caso], lambda q, k: {"estado": "ok", "resultados": [primera, segunda]})
        self.assertEqual(metricas_automaticas(reporte)["source_mrr_at_k"], 0.5)

    def test_ood_no_interfiere_en_hit(self):
        reporte = evaluar_casos([self.caso, self.ood], lambda q, k: respuesta())
        m = metricas_automaticas(reporte)
        self.assertEqual(m["casos_dominio"], 1)
        self.assertEqual(m["fuera_de_dominio_con_fragmentos"], 1)

    def test_senal_inicio_y_final_cortados(self):
        self.assertEqual(_revision_fragmento("ahorro eléctrico por"), ["posible_inicio_cortado", "posible_final_cortado"])
        self.assertFalse(_revision_fragmento("Recomendación completa."))

    def test_no_acepta_fuentes_inventadas(self):
        raw = respuesta()
        raw["resultados"][0]["url"] = "https://no-oficial.example/"
        r = evaluar_casos([self.caso], lambda q, k: raw)
        self.assertEqual(r["casos"][0]["estado"], "error")
        self.assertEqual(metricas_automaticas(r)["consultas_con_error"], 1)

    def test_no_acepta_distancia_nan(self):
        raw = respuesta()
        raw["resultados"][0]["distancia_vectorial"] = float("nan")
        r = evaluar_casos([self.caso], lambda q, k: raw)
        self.assertEqual(r["casos"][0]["estado"], "error")

    def test_error_controlado_de_tool(self):
        r = evaluar_casos([self.caso], lambda q, k: (_ for _ in ()).throw(RuntimeError("ruta-secreta")))
        self.assertEqual(r["casos"][0]["estado"], "error")
        self.assertNotIn("ruta-secreta", str(r))

    def test_error_por_identificadores_duplicados(self):
        with self.assertRaises(ValueError):
            evaluar_casos([self.caso, self.caso], lambda q, k: respuesta())

    def test_reporte_sin_revisar_no_se_puntua(self):
        r = evaluar_casos([self.caso], lambda q, k: respuesta())
        with self.assertRaisesRegex(ValueError, "Faltan evaluaciones"):
            metricas_manuales(r)

    def test_metricas_manual_pertinencia_y_utilidad(self):
        r = evaluar_casos([self.caso, self.ood], lambda q, k: respuesta(), k=1)
        for c in r["casos"]:
            for item in c["resultados"]:
                item.update(relevancia_manual=2 if c["tipo"] == "dominio" else 0,
                            cita_verificada_manual=True, fragmento_completo_manual=False)
        m = metricas_manuales(r)
        self.assertEqual(m["precision_tematica_at_k"], 1)
        self.assertEqual(m["precision_util_at_k"], 1)
        self.assertEqual(m["hit_util_at_k"], 1)
        self.assertEqual(m["fragmentos_completos"], "0/1")

    def test_true_no_es_calificacion_de_relevancia(self):
        r = evaluar_casos([self.caso], lambda q, k: respuesta())
        item = r["casos"][0]["resultados"][0]
        item.update(relevancia_manual=True, cita_verificada_manual=True, fragmento_completo_manual=True)
        with self.assertRaises(ValueError):
            metricas_manuales(r)


if __name__ == "__main__":
    unittest.main()
