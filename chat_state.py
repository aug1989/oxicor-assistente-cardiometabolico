"""Conversation state held only in the current Streamlit browser session."""
from datetime import datetime, timezone
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def new_chat(state):
    chat_id = str(uuid.uuid4())
    state["chats"][chat_id] = {
        "title": f"Conversa {len(state['chats']) + 1}",
        "messages": [],
        "session_id": chat_id,
        "created_at": now(),
    }
    state["active_chat_id"] = chat_id
    return chat_id


def initialize_chats(state):
    if "chats" not in state:
        state["chats"] = {}
    if not state["chats"]:
        new_chat(state)
    elif state.get("active_chat_id") not in state["chats"]:
        state["active_chat_id"] = next(iter(state["chats"]))


def select_chat(state, chat_id):
    if chat_id not in state["chats"]:
        raise KeyError("A conversa não pertence à sessão atual.")
    state["active_chat_id"] = chat_id
