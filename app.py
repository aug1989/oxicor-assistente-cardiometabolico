import json
import re
import os
import uuid
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
import streamlit as st

DB_PATH = Path(os.environ.get('CHAT_HISTORY_DB', '/app/data/history.sqlite3'))


def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.execute('CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, title TEXT NOT NULL, session_id TEXT NOT NULL, messages TEXT NOT NULL, created_at TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    return db


def save_chat(cid):
    chat = st.session_state.chats[cid]
    # Somente dados do histórico; nunca serializar ambiente ou session_state inteiro.
    messages = [{k: m[k] for k in ('role', 'content', 'created_at', 'error', 'mode', 'pending') if k in m}
                for m in chat['messages']]
    with database() as db:
        db.execute('INSERT INTO chats VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title, messages=excluded.messages',
                   (cid, chat['title'], chat['session_id'], json.dumps(messages, ensure_ascii=False), chat['created_at']))
    db.close()


def save_active(cid):
    with database() as db:
        db.execute("INSERT INTO settings VALUES ('active_chat_id', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (cid,))
    db.close()


def load_history():
    with database() as db:
        rows = db.execute('SELECT id,title,session_id,messages,created_at FROM chats ORDER BY created_at,id').fetchall()
        active = db.execute("SELECT value FROM settings WHERE key='active_chat_id'").fetchone()
    db.close()
    chats = {cid: {'title': title, 'session_id': sid, 'messages': json.loads(messages), 'created_at': created}
             for cid, title, sid, messages, created in rows}
    for item in chats.values():
        for message in item['messages']:
            if message.get('pending'):
                message['error'] = 'Resposta interrompida antes de ser salva por completo.'
    return chats, active[0] if active and active[0] in chats else next(iter(chats), None)


def now():
    return datetime.now(timezone.utc).isoformat()


def new_chat():
    """Callback: cria uma conversa sem apagar as anteriores."""
    cid = str(uuid.uuid4())
    st.session_state.chats[cid] = {
        'title': f'Conversa {len(st.session_state.chats) + 1}',
        'messages': [], 'session_id': cid, 'created_at': now(),
    }
    st.session_state.active_chat_id = cid
    save_chat(cid)
    save_active(cid)


def select_chat(cid):
    """Callback: seleciona mensagens e sessão Flowise correspondentes."""
    st.session_state.active_chat_id = cid
    # Reabre a versão persistida, inclusive atualizações feitas por outra aba.
    chats, _ = load_history()
    st.session_state.chats[cid] = chats[cid]
    save_active(cid)


def sse_events(response):
    """Lê eventos SSE completos e o envelope JSON nativo do Flowise."""
    event, data = 'message', []
    response.encoding = 'utf-8'
    for line in response.iter_lines(chunk_size=1, decode_unicode=True):
        if line == '':
            if data:
                raw = '\n'.join(data)
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = raw
                if isinstance(payload, dict) and 'event' in payload:
                    yield payload['event'], payload.get('data')
                else:
                    yield event, payload
            event, data = 'message', []
        elif line.startswith('event:'):
            event = line[6:].lstrip()
        elif line.startswith('data:'):
            data.append(line[5:].lstrip(' '))


class PresentationFilter:
    """Retém blocos internos, inclusive marcadores divididos entre tokens SSE.

    Não interpreta/reformula conteúdo científico. Prefixos de planejamento
    sem abertura ficam retidos até um fechamento explícito de thinking.
    """
    tags = ('think', 'thinking', 'reasoning', 'analysis', 'tool_call', 'tool_calls')
    internal_prefixes = ('okay, the user', 'okay, let me', 'okay the user', 'let me think',
                         'i need to check', 'i need to figure', 'i need to answer')

    def __init__(self):
        self.pending = ''
        self.initial = True
        self.hidden = []

    def feed(self, text, final=False):
        self.pending += text
        output = []
        if self.initial:
            prefix = self.pending.lstrip().lower()
            if not final and (not prefix or any(p.startswith(prefix) for p in self.internal_prefixes)):
                return ''
            if any(prefix.startswith(p) for p in self.internal_prefixes):
                self.hidden = ['think']
            self.initial = False
        while self.pending:
            start = self.pending.find('<')
            if start < 0:
                if not self.hidden:
                    output.append(self.pending)
                self.pending = ''
                break
            if not self.hidden:
                output.append(self.pending[:start])
            self.pending = self.pending[start:]
            stop = self.pending.find('>')
            if stop < 0:
                # Nunca deixar escapar um marcador ainda incompleto.
                if final:
                    if not self.hidden and not any(
                        marker.startswith(self.pending.lower())
                        for name in self.tags for marker in ('<' + name + '>', '</' + name + '>')
                    ):
                        output.append(self.pending)
                    self.pending = ''
                break
            tag = self.pending[:stop + 1]
            match = re.fullmatch(r'<\s*(/?)\s*(' + '|'.join(self.tags) + r')\s*>', tag, re.I)
            if match:
                name = match[2].lower()
                if match[1]:
                    if self.hidden:
                        self.hidden.pop()
                    if not self.hidden:
                        # Uma rodada de ferramenta pode iniciar outro bloco sem abertura.
                        self.initial = True
                        remainder = self.pending[stop + 1:]
                        self.pending = ''
                        output.append(self.feed(remainder, final=final))
                        return ''.join(output)
                else:
                    self.hidden.append(name)
            elif not self.hidden:
                output.append(tag)
            self.pending = self.pending[stop + 1:]
        return ''.join(output)


def visible_answer(text):
    # Só apresentação: nunca regrava o conteúdo antigo do SQLite.
    return PresentationFilter().feed(text, final=True)


def flowise_tokens(question, chat, message):
    headers = {'Authorization': f'Bearer {API_KEY}'} if API_KEY else {}
    with requests.post(
        API_URL, headers=headers,
        json={'question': question, 'streaming': True,
              'chatId': chat['session_id'],
              'overrideConfig': {'sessionId': chat['session_id']}},
        stream=True, timeout=(10, 180),
    ) as response:
        response.raise_for_status()
        if 'text/event-stream' not in response.headers.get('Content-Type', ''):
            data = response.json()
            answer = (data.get('text') or data.get('answer')) if isinstance(data, dict) else None
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError('Resposta sem texto')
            message['mode'] = 'integral'
            answer = visible_answer(answer)
            if not answer.strip():
                raise ValueError('Resposta final ausente')
            message['content'] = answer
            yield answer
            return
        message['mode'] = 'SSE'
        ended = False
        presentation = PresentationFilter()
        for event, data in sse_events(response):
            if event == 'token' and isinstance(data, str):
                visible = presentation.feed(data)
                if visible:
                    message['content'] += visible
                    yield visible
            elif event in ('error', 'abort'):
                raise ValueError('Fluxo interrompido')
            elif event == 'end':
                ended = True
                break
            # Eventos de thinking e metadados não são exibidos como resposta.
        tail = presentation.feed('', final=True)
        if tail:
            message['content'] += tail
            yield tail
        if not ended or not message['content'].strip():
            raise ValueError('Stream incompleto ou vazio')


st.set_page_config(page_title='OXICOR · Chat e Relatórios', page_icon='💬')
area = st.sidebar.radio('Área', ['Chat', 'Relatórios'], key='oxicor_area')
if area == 'Relatórios':
    from reports_ui import render_reports
    render_reports()
    st.stop()
API_URL = os.environ.get('FLOWISE_API_URL', '').strip()
API_KEY = os.environ.get('FLOWISE_API_KEY', '').strip()
parsed_url = urlparse(API_URL)
url_valid = parsed_url.scheme in ('http', 'https') and bool(parsed_url.netloc)
if 'chats' not in st.session_state:
    st.session_state.chats, st.session_state.active_chat_id = load_history()
    if not st.session_state.chats:
        new_chat()

st.title('💬 OXICOR')
st.caption('Converse com seu assistente. Histórico salvo localmente neste computador.')
st.caption('Assistente educacional sobre saúde cardiometabólica. Não substitui avaliação profissional. Evite informar dados pessoais.')
with st.expander('Exemplos de perguntas à base científica'):
    st.write('• Segundo a base OXICOR, quais valores definem hipertensão arterial?')
    st.write('• Segundo a base OXICOR, como a obesidade se relaciona ao risco cardiovascular?')
    st.write('• Segundo a base OXICOR, qual é a relação entre diabetes tipo 2 e risco cardiovascular?')
if not url_valid:
    st.error('Configuração incompleta: confira FLOWISE_API_URL no .env e recrie somente o container Streamlit.')
with st.sidebar:
    st.header('Conversas')
    st.button('Nova conversa', on_click=new_chat, use_container_width=True)
    for cid, item in reversed(list(st.session_state.chats.items())):
        st.button(item['title'], key=f'chat_{cid}', on_click=select_chat,
                  args=(cid,), use_container_width=True,
                  type='primary' if cid == st.session_state.active_chat_id else 'secondary')
    st.caption('Histórico local compartilhado entre as abas deste aplicativo, preservado após atualizar a página.')
    if not API_KEY or API_KEY == 'INSIRA_SUA_CHAVE_AQUI':
        st.info('Confira FLOWISE_API_KEY no .env se o fluxo exigir autenticação.')

chat = st.session_state.chats[st.session_state.active_chat_id]
for message in chat['messages']:
    with st.chat_message(message['role']):
        st.markdown(visible_answer(message['content']) if message['role'] == 'assistant' else message['content'])
        if message.get('error'):
            st.error(message['error'])
        if message.get('mode') == 'integral':
            st.caption('O Flowise retornou uma resposta integral, sem streaming nesta chamada.')

if question := st.chat_input('Digite sua mensagem…', disabled=not url_valid):
    if not chat['messages']:
        chat['title'] = question[:40] + ('…' if len(question) > 40 else '')
    chat['messages'].append({'role': 'user', 'content': question, 'created_at': now()})
    with st.chat_message('user'):
        st.markdown(question)
    answer = {'role': 'assistant', 'content': '', 'created_at': now(), 'pending': True}
    chat['messages'].append(answer)
    save_chat(st.session_state.active_chat_id)
    with st.chat_message('assistant'):
        try:
            with st.spinner('Aguardando resposta do Flowise…'):
                st.write_stream(flowise_tokens(question, chat, answer))
        except requests.HTTPError as exc:
            code = exc.response.status_code
            answer['error'] = ('Autenticação recusada. Confira a chave no .env.' if code in (401, 403)
                               else f'Flowise retornou HTTP {code}. Confira o fluxo e o endpoint.')
        except requests.Timeout:
            answer['error'] = 'Tempo de espera excedido. A resposta parcial, se houver, foi preservada.'
        except (requests.RequestException, ValueError):
            answer['error'] = 'A resposta foi interrompida ou inválida. Confira o Flowise; o texto parcial foi preservado.'
        finally:
            answer['pending'] = False
            save_chat(st.session_state.active_chat_id)
    st.rerun()
