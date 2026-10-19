"""Política local aplicada antes de importar CrewAI ou chamar serviços externos."""
import os
import re
import sqlite3
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path

class PolicyDenied(Exception):
    pass

def scope_reply(question):
    text = unicodedata.normalize('NFKD', question).encode('ascii', 'ignore').decode().lower().strip()
    if not text or len(question) > 3000:
        raise PolicyDenied('Envie uma pergunta de até 3.000 caracteres sobre o OXICOR ou saúde cardiometabólica.')
    if re.fullmatch(r'(oi|ola|bom dia|boa tarde|boa noite|obrigad[oa]|o que voce faz|ajuda)[!?.\s]*', text):
        return ('Posso consultar os dados do OXICOR, usar o modelo de diabetes com um perfil fictício e consultar a base científica cardiometabólica. '
                'Exemplos: **Quantos participantes há na base?** ou **Segundo a base OXICOR, qual a relação entre diabetes e risco cardiovascular?**')
    denied = r'\b(futebol|horoscopo|aposta|criptomoeda|bitcoin|romance|roteiro de viagem|campanha eleitoral|marketing|video game)\b|ignore.{0,30}(instruc|regra)|system prompt|\b(escreva|crie|gere|faca|resolva).{0,35}\b(codigo|script|poema|redacao|programa|software|site|equacao)\b'
    domain = r'\b(oxicor|diabetes|diabetico|hipertensao|pressao|obesidade|cardiovascular|cardiometabolic\w*|colesterol|glicemia|insulina|imc|bmi|highbp|highchol|participantes?|triagens?|duckdb|cdc|sindrome metabolica|sedentarismo|atividade fisica|alimentacao|tabagismo)\b'
    if re.search(denied, text) or not re.search(domain, text):
        raise PolicyDenied('Este assistente atende somente ao OXICOR e à saúde cardiometabólica. Reformule a pergunta nesse contexto. Nenhum agente foi acionado.')
    return None

def reserve_budget(path, now=None, hourly=30, daily=100, cooldown=15):
    now = time.time() if now is None else now
    with sqlite3.connect(path, timeout=5) as db:
        db.execute('CREATE TABLE IF NOT EXISTS usage (started REAL NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        rows = [row[0] for row in db.execute('SELECT started FROM usage WHERE started > ?', (now-86400,))]
        if rows and now-max(rows) < cooldown:
            raise PolicyDenied('Aguarde 15 segundos entre solicitações ao sistema.')
        if sum(value > now-3600 for value in rows) >= hourly:
            raise PolicyDenied('Limite compartilhado de 30 solicitações por hora atingido. Tente mais tarde.')
        if len(rows) >= daily:
            raise PolicyDenied('Limite compartilhado de 100 solicitações em 24 horas atingido. Tente mais tarde.')
        db.execute('DELETE FROM usage WHERE started <= ?', (now-86400,))
        db.execute('INSERT INTO usage VALUES (?)', (now,))

@contextmanager
def request_slot():
    import portalocker
    root = Path(os.getenv('OXICOR_USAGE_DIR', '/app/data/usage'))
    root.mkdir(parents=True, exist_ok=True)
    lock = portalocker.Lock(str(root/'active.lock'), mode='a', timeout=0)
    try:
        lock.acquire()
    except portalocker.exceptions.LockException:
        raise PolicyDenied('O sistema já está atendendo uma solicitação. Aguarde a conclusão e tente novamente.') from None
    try:
        reserve_budget(root/'usage.sqlite3')
        yield
    finally:
        lock.release()

def guarded_request(function):
    def wrapped(question, *args, **kwargs):
        try:
            reply = scope_reply(question)
            if reply is not None:
                return {'answer': reply, 'route': 'ORIENTAÇÃO', 'trace': []}
            with request_slot():
                return function(question, *args, **kwargs)
        except PolicyDenied as exc:
            return {'answer': str(exc), 'route': 'CONTROLE DE USO', 'trace': []}
    return wrapped
