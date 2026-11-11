"""Best-effort redaction for common, explicitly formatted identifiers."""
import re


_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_CPF = re.compile(r"(?<!\d)(?:\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?!\d)")
_BRAZIL_PHONE = re.compile(
    r"(?<!\w)(?:\+55[\s.-]*|\(\d{2}\)[\s.-]*|\d{2}[\s.-])"
    r"\d{4,5}[\s.-]\d{4}(?!\w)"
)
_LABELED_IDENTIFIER = re.compile(
    r"(?i)\b(cpf|telefone|celular|phone|e-mail|email)\b\s*[:=]\s*([+()\d.\s-]{8,})"
)
_LABELED_NAME = re.compile(
    r"(?i:\b(nome|paciente)\s*[:=]\s*)"
    r"([A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'-]*(?:\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'-]*){0,2})"
)
_LABELED_SECRET = re.compile(
    r"(?i)\b(api[_ -]?key|access[_ -]?token|token|secret|senha|password)\b"
    r"\s*[:=]\s*[^\s,;]+"
)

_REDACTED = "[DADO SENSÍVEL REMOVIDO]"


def redact_text(value):
    """Redact common identifiers without removing health terminology or values."""
    if not isinstance(value, str):
        return value
    value = _LABELED_SECRET.sub(lambda match: f"{match.group(1)}={_REDACTED}", value)
    def redact_labeled_identifier(match):
        label, candidate = match.group(1), match.group(2)
        digits = re.sub(r"\D", "", candidate)
        threshold = 11 if label.lower() == "cpf" else 10
        if threshold <= len(digits) <= 13:
            return f"{label}: {_REDACTED}"
        return match.group(0)

    value = _LABELED_IDENTIFIER.sub(redact_labeled_identifier, value)
    value = _LABELED_NAME.sub(lambda match: f"{match.group(1)}: [NOME REMOVIDO]", value)
    value = _EMAIL.sub("[E-MAIL REMOVIDO]", value)
    value = _CPF.sub("[CPF REMOVIDO]", value)
    return _BRAZIL_PHONE.sub("[TELEFONE REMOVIDO]", value)


def redact_value(value):
    """Redact string leaves in JSON-like records without changing their shape."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    return value


def prepare_user_message(content, created_at):
    """Create the safe representation that the chat history persists."""
    return {
        "role": "user",
        "content": redact_text(content),
        "created_at": created_at,
    }


def prepare_flowise_payload(question, session_id):
    """Build the external request only from the minimized user question."""
    return {
        "question": redact_text(question),
        "streaming": True,
        "chatId": session_id,
        "overrideConfig": {"sessionId": session_id},
    }


def redact_stream(chunks):
    """Buffering lets redaction catch identifiers split across stream tokens."""
    return redact_text("".join(chunks))
