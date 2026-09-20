"""Duas intenções em português, com SQL fixo e parâmetros separados."""
import re
import unicodedata


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if unicodedata.category(c) != 'Mn')


def interpret(question):
    text = normalize(question.strip())
    # Aceita somente perguntas completas do escopo; nunca executa texto como SQL.
    if re.fullmatch(r'quantos participantes (?:tiveram|tem|possuem) (?:pressao(?: arterial)?|pa) (?:acima(?: da faixa(?: esperada)?)?|elevada|alterada)\s*\??', text):
        return 'pressure_count', None
    match = re.fullmatch(r'qual (?:foi |e )?a ultima (?:pressao(?: arterial)?|pa)(?: registrada)? (?:do|da) (?:paciente|participante) ([a-z0-9_-]{1,80})\s*\??', text)
    if match:
        # Mantém caixa do ID original, pois o identificador no banco é sensível a caixa.
        identifier = re.search(r'([\w-]{1,80})\s*\??$', question.strip()).group(1)
        return 'latest_pressure', identifier
    return None, None
