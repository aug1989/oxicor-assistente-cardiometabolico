"""Application configuration shared by local and Streamlit Community Cloud runs."""
from pathlib import Path
import os
import tempfile

from streamlit.errors import StreamlitSecretNotFoundError


def get_setting(name, default=""):
    """Read an environment variable first, then a Streamlit secret."""
    value = os.getenv(name)
    if value is not None and value.strip():
        return value

    import streamlit as st

    try:
        value = st.secrets.get(name, default)
    except StreamlitSecretNotFoundError:
        return default
    return default if value is None else str(value)


def setting_enabled(name, default=False):
    value = get_setting(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def runtime_data_dir():
    configured = get_setting("OXICOR_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path(tempfile.gettempdir()) / "oxicor"


def runtime_path(setting_name, filename):
    configured = get_setting(setting_name, "").strip()
    path = Path(configured).expanduser() if configured else runtime_data_dir() / filename
    return path


def ensure_parent(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def chat_llm_settings():
    """Explicit OpenRouter settings take precedence over legacy local settings.

    No model is selected automatically: the deployment owner chooses its cost.
    The openai/ prefix selects CrewAI's OpenAI-compatible adapter, not OpenAI's endpoint.
    """
    router_model = get_setting("OPENROUTER_MODEL").strip()
    router_key = get_setting("OPENROUTER_API_KEY").strip()
    if router_model or router_key:
        return {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/" + router_model if router_model else "",
            "api_key": router_key,
            "configured": bool(router_model and router_key),
        }
    base = get_setting("CREWAI_BASE_URL").strip().rstrip("/")
    model = get_setting("CREWAI_LLM").strip()
    key = get_setting("CREWAI_API_KEY").strip()
    local_model = model.startswith(("ollama/", "ollama_chat/"))
    if local_model:
        model = "openai/" + model.split("/", 1)[1]
        if base and not base.endswith("/v1"):
            base += "/v1"
        key = key or "ollama"
    return {"base_url": base, "model": model, "api_key": key,
            "configured": bool(base and model and (key or local_model))}
