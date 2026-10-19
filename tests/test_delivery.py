import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from observability import observed_request, read_traces
from evaluate_golden import evaluate

class DeliveryTests(unittest.TestCase):
    def test_trace_persists_events_and_result(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'OXICOR_TRACE_DB':str(Path(root)/'trace.db')}):
            @observed_request
            def fake(question, on_event=None):
                on_event({'agent':'Teste','content':'evidência','kind':'ferramenta'})
                return {'answer':'evidência','route':'DADOS','trace':[]}
            result = fake('pergunta fictícia')
            saved = read_traces()
            self.assertEqual(saved[0]['id'],result['trace_id'])
            self.assertEqual(saved[0]['status'],'concluído')
            self.assertEqual(saved[0]['events'][0]['content'],'evidência')

    def test_trace_records_failure_without_exception_message(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'OXICOR_TRACE_DB':str(Path(root)/'trace.db')}):
            @observed_request
            def fake(question, on_event=None):
                raise ValueError('secret-token-example')
            with self.assertRaises(ValueError):
                fake('fictícia')
            saved = read_traces()[0]
            self.assertEqual(saved['error_type'],'ValueError')
            self.assertNotIn('secret-token-example',json.dumps(saved))

    def test_evaluation_rejects_changed_tool_numbers(self):
        result = {'answer':'total 8','route':'DADOS','trace':[{'kind':'ferramenta','content':'total 7'}]}
        score = evaluate({'expected_groups':[['total']], 'expected_route':'DADOS'}, result)
        self.assertEqual(score['grounding'],0)
        self.assertFalse(score['passed'])

    def test_evaluation_rejects_wrong_route_even_when_terms_match(self):
        result = {'answer':'total 7','route':'RAG','trace':[]}
        self.assertFalse(evaluate({'expected_groups':[['7']], 'expected_route':'DADOS'},result)['passed'])

    def test_rag_returns_verbatim_local_excerpts(self):
        from local_rag import retrieve, consult_local
        question = 'Uma glicemia isolada confirma ou exclui diabetes?'
        hits = retrieve(question)
        self.assertTrue(hits)
        answer = consult_local(question)
        for hit in hits:
            self.assertIn(hit['text'],answer)
            self.assertIn(hit['source'],answer)

    def test_model_uses_validated_threshold(self):
        import pandas as pd
        import numpy as np
        from ml_traditional import load_model_artifact, resolve_model_path, predict_with_saved_model
        artifact = load_model_artifact()
        self.assertNotIn('ID',artifact['feature_columns'])
        data = pd.read_csv('/app/seed/cdc_diabetes_health_indicators.csv').iloc[:50]
        actual = predict_with_saved_model(resolve_model_path(),data)
        expected = artifact['model'].predict_proba(data[artifact['feature_columns']])[:,1] >= artifact['threshold']
        np.testing.assert_array_equal(actual.predicted_diabetes,expected.astype(int))

if __name__ == '__main__':
    unittest.main()
