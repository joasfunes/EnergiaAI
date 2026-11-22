"""Regresiones de la Etapa 04.4 sin Ollama ni Chroma reales."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from energia_ai.rag.chunking import (
    CHUNK_STRATEGY, clean_retrieval_text, split_text_recursive,
    corpus_fingerprint, RagChunk,
)
from energia_ai.rag.vector_store import infer_season, RagSearcher
from energia_ai.rag.retrieval import recuperar_consejos
from energia_ai.rag.corpus import SOURCES
from scripts.backup_rag_04_4 import backup, restore, INDEX, MANIFEST, BASELINE
from scripts.compare_rag_04_4 import comparison


class FakeIndex:
    def __init__(self):
        self.items = [
            ('Consejos exclusivos de invierno. Mantener la calefacción.', 'EPRE-INV-2022', 'winter', 0.8),
            ('Consejos de verano. Apagar el aire al salir.', 'EPRE-VER-2025', 'summer', 0.9),
            ('Consejos nacionales sobre ventanas.', 'ARG-RES-2024', 'general', 1.0),
        ]
    def count(self):
        return len(self.items)
    def query(self, *, query_embeddings, n_results, include):
        entries = self.items[:n_results]
        return {
            'documents': [[v[0] for v in entries]],
            'metadatas': [[{'page': 0 if v[1] != 'ARG-RES-2024' else 4,
                            'title': v[1], 'source_id': v[1], 'url':
                            next(s.official_url for s in SOURCES if s.id == v[1]), 'season':v[2]}
                           for v in entries]],
            'distances': [[v[3] for v in entries]],
        }


def report_for_compare():
    return {'schema_version': '04.3.1', 'k': 3, 'casos': [{
        'id':'A', 'tipo':'dominio', 'fuente_esperada':SOURCES[1].id,
        'rango_primera_fuente_esperada':1, 'resultados': [{'posicion':1, 'relevancia_manual':None, 'senales_chunking':[]}], 'estado':'ok',
    }]}


class TestQuality(unittest.TestCase):
    def test_preserve_paragraph(self):
        text = ('Primera recomendación bien definida. ' * 4 + '\n\n' +
                'Segunda recomendación bien definida. ' * 4)
        parts = split_text_recursive(text, size=190, overlap=45)
        self.assertEqual(len(parts), 2)
        self.assertTrue(parts[0].startswith('Primera'))
        self.assertTrue(parts[1].startswith('Segunda'))

    def test_splits_long_sentences(self):
        parts = split_text_recursive('palabra ' * 200, size=150, overlap=20)
        self.assertGreater(len(parts), 3)
        self.assertTrue(all(len(s) <= 150 for s in parts))

    def test_rechaza_parametros_invalidos(self):
        with self.assertRaises(ValueError): split_text_recursive('Texto.', size=40)
        with self.assertRaises(ValueError): split_text_recursive('Texto.', size=180, overlap=95)

    def test_empty(self):
        self.assertEqual(split_text_recursive(' \n\n '), [])

    def test_cleaning_preserves_numbers(self):
        dirty='Luminarias eﬁcientes: 20%. Secretaría de Energía Subsecretaría de Transición y Planeamiento Energético'
        clean=clean_retrieval_text(dirty)
        self.assertIn('eficientes: 20%', clean)
        self.assertNotIn('Subsecretaría', clean)

    def test_strategy_in_fingerprint(self):
        chunks=[RagChunk(id='id', text='hola', metadata={'page':0,'sha256_raw':'a'*64})]
        self.assertIn('recursive',CHUNK_STRATEGY)
        self.assertEqual(corpus_fingerprint(chunks,model='m',size=900,overlap=130),
                         corpus_fingerprint(chunks,model='m',size=900,overlap=130))

    def test_season_inference(self):
        self.assertEqual(infer_season('Mucho calor en verano'), 'summer')
        self.assertEqual(infer_season('Uso de caloventores'), 'winter')
        self.assertIsNone(infer_season('¿Cómo mejorar el aislamiento de la vivienda?'))
        self.assertIsNone(infer_season('Comparar invierno y verano'))

    def test_season_filter_and_national_source(self):
        s=object.__new__(RagSearcher)
        s.embedder=type('Embed', (), {'embed':lambda _self, docs:[[1.,0.]]})()
        s.manifest={'embedding_dimensions':2}
        s.collection=FakeIndex()
        summer=s.search('¿Cómo consumir menos durante una ola de calor?', k=3)
        self.assertEqual([p['source_id'] for p in summer], ['EPRE-VER-2025','ARG-RES-2024'])
        winter=s.search('¿Cómo ahorrar en calefacción de invierno?',k=3)
        self.assertEqual([p['source_id'] for p in winter], ['EPRE-INV-2022','ARG-RES-2024'])
        neutral=s.search('Consejos para ahorrar electricidad',k=3)
        self.assertEqual(len(neutral),3)

    def test_abstain_high_distances(self):
        source=SOURCES[1]
        class Mock:
            def search(self, question, *, k=3):
                return [{'source_id':source.id,'source_url':source.official_url,
                         'text':'Documento oficial pero no relacionado con la consulta.',
                         'page':None,'distance':1.7}]
        result=recuperar_consejos('¿Cómo configurar una impresora?',buscador=Mock())
        self.assertEqual(result['estado'],'sin_resultados')
        self.assertEqual(result['cantidad_resultados'],0)

    def test_keep_low_distance(self):
        source=SOURCES[1]
        class Mock:
            def search(self, question, *, k=3):
                return [{'source_id':source.id,'source_url':source.official_url,
                         'text':'Mantener la calefacción solo en los ambientes usados.',
                         'page':None,'distance':0.8}]
        result=recuperar_consejos('¿Cómo usar calefacción?',buscador=Mock())
        self.assertEqual(result['estado'],'ok')
        self.assertEqual(result['cantidad_resultados'],1)

    def test_backup_restore_without_rag_remote(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            (root/INDEX).mkdir(parents=True)
            (root/INDEX/'db.bin').write_bytes(b'old')
            (root/MANIFEST).write_text('{"fingerprint":"abc"}', 'utf-8')
            doc=root/'data/processed/rag/evaluacion_04_3.json'
            doc.parent.mkdir(parents=True)
            doc.write_text('{}','utf-8')
            snap=backup(root)
            self.assertTrue((root/BASELINE).exists())
            (root/INDEX/'db.bin').write_bytes(b'new')
            restore(root, snap.name)
            self.assertEqual((root/INDEX/'db.bin').read_bytes(), b'old')
            self.assertEqual((root/MANIFEST).read_text('utf-8'), '{"fingerprint":"abc"}')

    def test_bad_snapshot_rejected(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):restore(Path(temp),'../external')

    def test_compare_only_identical_cases(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            directory=root/'data/processed/rag'
            directory.mkdir(parents=True)
            base=report_for_compare(); other=report_for_compare()
            (directory/'evaluacion_04_3_baseline.json').write_text(json.dumps(base),'utf-8')
            (directory/'evaluacion_04_4.json').write_text(json.dumps(other),'utf-8')
            result=comparison(root)
            self.assertEqual(result['automaticas_antes']['casos_dominio'],1)
            self.assertTrue(result['revisiones_pendientes'])
            other['casos'][0]['id']='B'
            (directory/'evaluacion_04_4.json').write_text(json.dumps(other),'utf-8')
            with self.assertRaises(ValueError): comparison(root)

if __name__ == '__main__':unittest.main()
