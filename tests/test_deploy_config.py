import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chat_state import initialize_chats, select_chat
from config import ensure_parent, get_setting, runtime_data_dir, runtime_path
from observability import observed_request
from streamlit.testing.v1 import AppTest


class DeployConfigurationTests(unittest.TestCase):
    def test_environment_settings_are_read_without_secrets(self):
        with patch.dict(os.environ, {"CREWAI_BASE_URL": "https://llm.example.invalid"}, clear=True):
            self.assertEqual(get_setting("CREWAI_BASE_URL"), "https://llm.example.invalid")
            self.assertEqual(get_setting("NOT_CONFIGURED", "fallback"), "fallback")

    def test_runtime_paths_are_writable_and_configurable(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            os.environ, {"OXICOR_DATA_DIR": folder}, clear=True
        ):
            target = ensure_parent(runtime_path("OXICOR_DUCKDB_PATH", "oxicor.duckdb"))
            target.write_text("temporary fixture", encoding="utf-8")
            self.assertEqual(target.read_text(encoding="utf-8"), "temporary fixture")
            self.assertEqual(runtime_data_dir(), Path(folder))

    def test_default_usage_storage_does_not_depend_on_app_directory(self):
        from usage_policy import request_slot
        with tempfile.TemporaryDirectory() as folder, patch('config.get_setting', return_value=''), patch('usage_policy.get_setting', return_value=''), patch('config.tempfile.gettempdir', return_value=folder):
            with request_slot():
                self.assertTrue((Path(folder) / 'oxicor' / 'usage' / 'usage.sqlite3').is_file())
            self.assertEqual(runtime_data_dir(), Path(folder) / 'oxicor')

    def test_conversations_are_isolated_between_session_states(self):
        first_session = {}
        second_session = {}
        initialize_chats(first_session)
        first_id = first_session["active_chat_id"]
        first_session["chats"][first_id]["messages"].append(
            {"role": "user", "content": "pergunta fictícia"}
        )

        initialize_chats(second_session)

        self.assertNotIn(first_id, second_session["chats"])
        self.assertEqual(second_session["chats"][second_session["active_chat_id"]]["messages"], [])
        with self.assertRaises(KeyError):
            select_chat(second_session, first_id)

    def test_disabled_observability_does_not_create_global_trace_database(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            os.environ,
            {
                "OXICOR_DATA_DIR": folder,
                "OXICOR_TRACE_DB": str(Path(folder) / "trace.sqlite3"),
                "OXICOR_OBSERVABILITY_ENABLED": "false",
                "OXICOR_LANGFUSE_ENABLED": "false",
            },
            clear=True,
        ):
            @observed_request
            def fake(question, on_event=None):
                if on_event:
                    on_event({"agent": "fixture", "content": "resposta fictícia"})
                return {"answer": "resposta fictícia", "route": "RAG", "trace": []}

            result = fake("pergunta fictícia")

            self.assertEqual(result["answer"], "resposta fictícia")
            self.assertNotIn("trace_id", result)
            self.assertFalse((Path(folder) / "trace.sqlite3").exists())

    def test_chat_reports_missing_ai_configuration_without_running_a_model(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            os.environ,
            {
                "CREWAI_BASE_URL": "",
                "CREWAI_LLM": "",
                "OXICOR_DATA_DIR": folder,
                "OXICOR_ADMIN_PAGES_ENABLED": "false",
                "OXICOR_OBSERVABILITY_ENABLED": "false",
            },
            clear=True,
        ), patch("multi_agents.run_multi_agent") as run:
            app = AppTest.from_file(str(app_path)).run()
            self.assertTrue(any("depende da configuração" in item.value for item in app.warning))
            self.assertNotIn("Observabilidade", app.radio[0].options)
            self.assertNotIn("Avaliação", app.radio[0].options)

            app.chat_input[0].set_value("Explique a relação entre diabetes e risco cardiovascular.")
            app.run()

            self.assertTrue(any("configure CREWAI_BASE_URL e CREWAI_LLM" in item.value for item in app.error))
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
