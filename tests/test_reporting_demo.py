import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import reporting


class DemoReportingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = self.root / "demo.duckdb"
        self.environment = patch.dict(
            os.environ,
            {
                "OXICOR_DUCKDB_PATH": str(self.database_path),
                "OXICOR_DATA_DIR": str(self.root),
                "POSTGRES_HOST": "",
                "POSTGRES_DB": "",
                "POSTGRES_USER": "",
                "POSTGRES_PASSWORD": "",
            },
            clear=True,
        )
        self.environment.start()
        import duckdb_tools

        self.duckdb_tools = duckdb_tools
        self.database_override = patch.object(duckdb_tools, "DB_PATH", self.database_path)
        self.database_override.start()
        duckdb_tools.initialize_database(
            Path(__file__).resolve().parents[1] / "data"
        )

    def tearDown(self):
        self.database_override.stop()
        self.environment.stop()
        self.temporary.cleanup()

    def test_missing_postgres_uses_local_demo_data_and_existing_fields(self):
        with patch("reporting.connection", side_effect=AssertionError("PostgreSQL must not be used")):
            result = reporting.load_overview()
        source = pd.read_csv(
            Path(__file__).resolve().parents[1] / "data" / "triagens.csv"
        )

        self.assertEqual(result["source"], "demo")
        self.assertEqual(result["participantes"], 7)
        self.assertEqual(result["triagens"], 9)
        self.assertEqual(set(result["risco"]["risco"]), set(source["risco"]))
        self.assertEqual(
            set(result["sindrome"]["status_sindrome_metabolica"]),
            set(source["status_sindrome_metabolica"]),
        )
        self.assertEqual(
            len(result["alertas"]),
            int(
                source["alerta_critico"]
                .astype(str)
                .str.lower()
                .isin({"true", "t", "1", "yes"})
                .sum()
            ),
        )
        self.assertEqual(
            int(result["risco"]["total_triagens"].sum()),
            result["triagens"],
        )
        self.assertEqual(
            int(result["sindrome"]["total_triagens"].sum()),
            result["triagens"],
        )
        self.assertEqual(
            int(result["valores_alerta"]["total_triagens"].sum()),
            result["triagens"],
        )
        self.assertTrue(result["alertas"]["alerta_critico"].all())

    def test_demo_queries_are_read_only_and_latest_pressure_is_from_existing_id(self):
        before = self.database_path.read_bytes()
        overview = reporting.load_overview()
        patient_id = overview["pacientes"].iloc[0]["paciente_id"]

        latest = reporting.latest_pressure(patient_id, source="demo")

        self.assertEqual(self.database_path.read_bytes(), before)
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest.iloc[0]["paciente_id"], patient_id)

    def test_partial_postgres_configuration_is_reported_instead_of_hidden(self):
        with patch.dict(os.environ, {"POSTGRES_HOST": "db.example.invalid"}):
            with self.assertRaisesRegex(reporting.ReportsUnavailable, "incompleta"):
                reporting.load_overview()

    def test_postgres_backend_remains_available_when_fully_configured(self):
        answers = [
            pd.DataFrame({"conexao_ok": [1]}),
            pd.DataFrame({"total_participantes": [7]}),
            pd.DataFrame({"total_triagens": [9]}),
            pd.DataFrame({"participantes_pressao_acima": [2]}),
            pd.DataFrame({"risco": ["alto"], "total_triagens": [9]}),
            pd.DataFrame({"status_sindrome_metabolica": ["registrado"], "total_triagens": [9]}),
            pd.DataFrame({"alerta_critico": [True], "total_triagens": [9]}),
            pd.DataFrame({"paciente_id": ["fixture"]}),
            pd.DataFrame({"data_type": ["boolean"]}),
            pd.DataFrame({
                "triagem_id": [1],
                "paciente_id": ["fixture"],
                "data_coleta": ["2026-01-01"],
                "pas": [120],
                "pad": [80],
                "risco": ["baixo"],
                "alerta_critico": [False],
            }),
        ]
        with patch.dict(
            os.environ,
            {
                "POSTGRES_HOST": "db.example.invalid",
                "POSTGRES_DB": "oxicor",
                "POSTGRES_USER": "readonly",
                "POSTGRES_PASSWORD": "fake-secret-for-test",
            },
        ), patch("reporting.connection"), patch(
            "reporting.dataframe", side_effect=answers
        ):
            result = reporting.load_overview()

        self.assertEqual(result["source"], "postgresql")
        self.assertEqual(result["participantes"], 7)
        self.assertEqual(result["alerta_tipo"], "boolean")

    def test_interface_labels_demo_data(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run()
        self.assertEqual(app.exception, [])
        app.radio[0].set_value("Relatórios")
        app.run()

        self.assertTrue(
            any("Dados fictícios de demonstração" in item.value for item in app.info)
        )
        self.assertEqual(app.exception, [])


if __name__ == "__main__":
    unittest.main()
