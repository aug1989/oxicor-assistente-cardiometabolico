import unittest
from unittest.mock import patch
from config import chat_llm_settings


class OpenRouterConfigTests(unittest.TestCase):
    def settings(self, values):
        with patch("config.get_setting", side_effect=lambda name, default="": values.get(name, default)):
            return chat_llm_settings()

    def test_router_uses_exact_catalog_id_and_fixed_endpoint(self):
        result = self.settings({"OPENROUTER_MODEL": "openai/example-model", "OPENROUTER_API_KEY": "fixture-only"})
        self.assertEqual(result["model"], "openai/openai/example-model")
        self.assertEqual(result["base_url"], "https://openrouter.ai/api/v1")
        self.assertTrue(result["configured"])

    def test_partial_router_config_never_falls_back_to_local(self):
        for partial in ({"OPENROUTER_MODEL": "vendor/model"}, {"OPENROUTER_API_KEY": "fixture-only"}):
            with self.subTest(partial=list(partial)):
                result = self.settings(dict(CREWAI_BASE_URL="http://localhost:11434", CREWAI_LLM="ollama/test", **partial))
                self.assertFalse(result["configured"])
                self.assertEqual(result["base_url"], "https://openrouter.ai/api/v1")

    def test_existing_local_settings_remain_supported(self):
        result = self.settings({"CREWAI_BASE_URL": "http://localhost:11434", "CREWAI_LLM": "ollama/test"})
        self.assertTrue(result["configured"])
        self.assertEqual(result["base_url"], "http://localhost:11434/v1")
        self.assertEqual(result["model"], "openai/test")

    def test_unconfigured_chat_does_not_choose_a_model(self):
        self.assertFalse(self.settings({})["configured"])

    def test_remote_legacy_endpoint_requires_credential(self):
        self.assertFalse(self.settings({"CREWAI_BASE_URL": "https://example.invalid/v1", "CREWAI_LLM": "openai/test"})["configured"])
