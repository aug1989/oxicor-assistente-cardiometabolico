import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb_tools
from multi_agents import select_routes, ml_evidence, grounded_response, assemble_verified

class RoutingTests(unittest.TestCase):
    def test_added_clinical_claim_is_rejected(self):
        evidence = 'Probabilidade estimada: 0.5%. Não substitui avaliação clínica.'
        self.assertEqual(grounded_response(evidence + ' Risco cardíaco baixo.', evidence), evidence)

    def test_condenser_cannot_add_or_drop_evidence(self):
        parts = [('ML', '0.5%'), ('RAG', 'Não há evidência suficiente.')]
        output = assemble_verified('{"order":[0],"answer":"risco cardíaco baixo"}', parts)
        self.assertIn('0.5%', output)
        self.assertIn('Não há evidência suficiente.', output)
        self.assertNotIn('cardíaco', output)

    def test_condenser_can_reorder_verified_blocks(self):
        self.assertEqual(assemble_verified('{"order":[1,0]}', [('A','primeiro'),('B','segundo')]), '### B\nsegundo\n\n### A\nprimeiro')

    def test_generic(self):
        self.assertEqual(select_routes('Olá, o que você faz?'), ['GERAL'])

    def test_ml_without_variables(self):
        self.assertEqual(select_routes('Eu consigo predizer diabetes?'), ['ML'])

    def test_compound_request(self):
        self.assertEqual(select_routes('Quantos participantes há? Explique segundo a base científica a relação com diabetes.'), ['DADOS', 'RAG'])

    def test_ml_and_rag(self):
        self.assertEqual(select_routes('Faça uma previsão com BMI=24 e explique segundo a base científica.'), ['ML', 'RAG'])

    def test_missing_model(self):
        with patch('ml_traditional.resolve_model_path', return_value=None):
            self.assertIn('indisponível', ml_evidence('predizer diabetes'))

class DuckDBTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'participantes.csv').write_text('paciente_id,idade,sexo\n1,40,M\n2,60,F\n')
        (self.root / 'triagens.csv').write_text('paciente_id,pas,pad,risco\n1,120,80,baixo\n2,140,90,alto\n')
        (self.root / 'cdc_diabetes_health_indicators.csv').write_text('BMI,Diabetes_binary\n24,0\n30,1\n')
        self.patch = patch.object(duckdb_tools, 'DB_PATH', self.root / 'test.duckdb')
        self.patch.start()
        duckdb_tools.initialize_database(self.root)

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_counts(self):
        result = json.loads(duckdb_tools.query_data('total de participantes'))
        self.assertEqual(result['resultado'][0]['total_participantes'], 2)

    def test_pressure_filter(self):
        result = json.loads(duckdb_tools.query_data('quantos têm pressão acima'))
        self.assertEqual(result['resultado'][0]['participantes_pressao_acima'], 1)

    def test_no_user_sql(self):
        duckdb_tools.query_data('DROP TABLE participantes; ATTACH database;')
        self.assertEqual(json.loads(duckdb_tools.query_data('total de participantes'))['resultado'][0]['total_participantes'], 2)

    def test_cdc_summary(self):
        result = json.loads(duckdb_tools.query_data('resumo dataset CDC'))['resultado'][0]
        self.assertEqual(result['registros'], 2)
        self.assertEqual(result['imc_medio'], 27)

    def test_initialization_preserves_existing(self):
        before = duckdb_tools.DB_PATH.read_bytes()
        duckdb_tools.initialize_database(self.root)
        self.assertEqual(before, duckdb_tools.DB_PATH.read_bytes())

if __name__ == '__main__':
    unittest.main()
