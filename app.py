import logging
import traceback
from pathlib import Path
import json
import re
from urllib.parse import urlparse
import requests
import streamlit as st

from chat_state import initialize_chats, new_chat, now, select_chat as select_session_chat
from config import chat_llm_settings, get_setting, setting_enabled
from privacy import (
    prepare_flowise_payload,
    prepare_user_message,
    redact_stream,
    redact_text,
    redact_value,
)

class ChatConfigurationError(Exception):
    pass


def create_session_chat():
    new_chat(st.session_state)


def select_chat(chat_id):
    select_session_chat(st.session_state, chat_id)


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
    question = redact_text(question)
    headers = {'Authorization': f'Bearer {API_KEY}'} if API_KEY else {}
    with requests.post(
        API_URL, headers=headers,
        json=prepare_flowise_payload(question, chat['session_id']),
        stream=True, timeout=(10, 180),
    ) as response:
        response.raise_for_status()
        if 'text/event-stream' not in response.headers.get('Content-Type', ''):
            data = response.json()
            answer = (data.get('text') or data.get('answer')) if isinstance(data, dict) else None
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError('Resposta sem texto')
            message['mode'] = 'integral'
            answer = redact_text(visible_answer(answer))
            if not answer.strip():
                raise ValueError('Resposta final ausente')
            message['content'] = answer
            yield answer
            return
        message['mode'] = 'SSE'
        ended = False
        presentation = PresentationFilter()
        buffered = []
        for event, data in sse_events(response):
            if event == 'token' and isinstance(data, str):
                visible = presentation.feed(data)
                if visible:
                    buffered.append(visible)
            elif event in ('error', 'abort'):
                raise ValueError('Fluxo interrompido')
            elif event == 'end':
                ended = True
                break
            # Eventos de thinking e metadados não são exibidos como resposta.
        tail = presentation.feed('', final=True)
        if tail:
            buffered.append(tail)
        if not ended:
            raise ValueError('Stream incompleto ou vazio')
        answer = redact_stream(buffered)
        if not answer.strip():
            raise ValueError('Stream incompleto ou vazio')
        message['content'] = answer
        yield answer


st.set_page_config(page_title='OXICOR · Chat, Relatórios e ML', page_icon='💬')
areas = ['Chat', 'Relatórios', 'ML Tradicional']
if setting_enabled('OXICOR_ADMIN_PAGES_ENABLED'):
    areas.extend(['Observabilidade', 'Avaliação'])
if st.session_state.get('oxicor_area') not in areas:
    st.session_state.pop('oxicor_area', None)
area = st.sidebar.radio('Área', areas, key='oxicor_area')
if area == 'Observabilidade':
    from observability import render_observability
    render_observability()
    st.stop()
if area == 'Avaliação':
    from observability import render_evaluation
    render_evaluation()
    st.stop()
if area == 'Relatórios':
    from reports_ui import render_reports
    render_reports()
    st.stop()
if area == 'ML Tradicional':
    from ml_traditional import render_ml_traditional
    render_ml_traditional()
    st.stop()
API_URL = get_setting('FLOWISE_API_URL').strip()
API_KEY = get_setting('FLOWISE_API_KEY').strip()
CHAT_MODEL = chat_llm_settings()['model']
CHAT_CONFIGURED = chat_llm_settings()['configured']

parsed_url = urlparse(API_URL)
url_valid = parsed_url.scheme in ('http', 'https') and bool(parsed_url.netloc)
initialize_chats(st.session_state)

st.title('💬 OXICOR')
st.caption('O histórico fica somente na sessão atual e não é persistido. Ele pode desaparecer ao fechar a sessão ou reiniciar o aplicativo.')
st.caption('Assistente educacional sobre saúde cardiometabólica. Não substitui avaliação profissional. Evite informar dados pessoais.')
if not CHAT_CONFIGURED:
    st.warning('O chat com IA depende da configuração de OPENROUTER_MODEL e OPENROUTER_API_KEY, ou das variáveis CREWAI_* para outro endpoint. Nenhuma resposta simulada será usada.')
with st.expander('Exemplos de perguntas à base científica'):
    st.write('• Segundo a base OXICOR, quais valores definem hipertensão arterial?')
    st.write('• Segundo a base OXICOR, como a obesidade se relaciona ao risco cardiovascular?')
    st.write('• Segundo a base OXICOR, qual é a relação entre diabetes tipo 2 e risco cardiovascular?')
if not url_valid and get_setting('OXICOR_RAG_BACKEND', 'local') == 'flowise':
    st.warning('FLOWISE_API_URL não configurada: perguntas que exigem RAG não poderão ser respondidas.')
with st.sidebar:
    st.caption('Uso compartilhado: 1 atendimento por vez · 30 por hora · 100 em 24 horas. Perguntas de até 3.000 caracteres, no contexto OXICOR.')
    st.header('Conversas')
    st.button('Nova conversa', on_click=create_session_chat, use_container_width=True)
    for cid, item in reversed(list(st.session_state.chats.items())):
        st.button(redact_text(item['title']), key=f'chat_{cid}', on_click=select_chat,
                  args=(cid,), use_container_width=True,
                  type='primary' if cid == st.session_state.active_chat_id else 'secondary')
    st.caption('As conversas e os respectivos identificadores Flowise são privados desta sessão.')
    if not API_KEY or API_KEY == 'INSIRA_SUA_CHAVE_AQUI':
        st.info('FLOWISE_API_KEY não configurada; configure-a somente se o fluxo escolhido exigir autenticação.')
    st.caption(f"Modelo CrewAI configurado: {CHAT_MODEL or 'não configurado'}")

chat = st.session_state.chats[st.session_state.active_chat_id]
for message in chat['messages']:
    with st.chat_message(message['role']):
        st.markdown(
            redact_text(visible_answer(message['content'])) if message['role'] == 'assistant' else redact_text(message['content']),
            unsafe_allow_html=False,
        )
        if message.get('error'):
            st.error(message['error'])
        if message.get('route'):
            st.caption(f"Rota selecionada: {message['route']}")
        if message.get('agent_trace'):
            with st.expander('Ver handoffs e respostas dos agentes'):
                for step in message['agent_trace']:
                    st.markdown(f"**{step['agent']}**", unsafe_allow_html=False)
                    st.markdown(redact_text(step['content']), unsafe_allow_html=False)

if question := st.chat_input('Digite sua mensagem…', max_chars=3000):
    user_message = prepare_user_message(question, now())
    question = user_message['content']
    if not chat['messages']:
        chat['title'] = question[:40] + ('…' if len(question) > 40 else '')
    chat['messages'].append(user_message)
    with st.chat_message('user'):
        st.markdown(question)
    answer = {'role': 'assistant', 'content': '', 'created_at': now(), 'pending': True}
    chat['messages'].append(answer)
    with st.chat_message('assistant'):
        try:
            if not CHAT_CONFIGURED:
                raise ChatConfigurationError
            from multi_agents import run_multi_agent

            def consult_rag(prompt):
                backend = get_setting('OXICOR_RAG_BACKEND', 'local').strip().lower()
                if backend == 'local':
                    from local_rag import consult_local
                    return consult_local(prompt)
                if backend != 'flowise':
                    raise ValueError('OXICOR_RAG_BACKEND deve ser local ou flowise.')
                if not url_valid:
                    raise ValueError('FLOWISE_API_URL não configurada ou inválida.')
                tool_message = {'content': '', 'mode': None}
                return ''.join(flowise_tokens(prompt, chat, tool_message))

            def show_stage(agent_name):
                progress.update(label=f'Agente ativo: {agent_name}', state='running', expanded=True)

            def show_event(event):
                safe = dict(event)
                safe['content'] = redact_text(visible_answer(event['content']))
                safe = redact_value(safe)
                answer.setdefault('agent_trace', []).append(safe)
                st.markdown(f"**{safe['agent']} · {safe.get('kind', 'resultado')}**")
                st.markdown(safe['content'], unsafe_allow_html=False)

            with st.status('Iniciando orquestração CrewAI…', expanded=True) as progress:
                result = run_multi_agent(question, consult_rag, on_stage=show_stage, on_event=show_event)
                answer['content'] = redact_text(visible_answer(result['answer']))
                answer['route'] = result['route']
                answer['agent_trace'] = [
                    {**step, 'content': redact_text(visible_answer(step['content']))}
                    for step in result['trace']
                ]
                answer['mode'] = 'crewai'
                progress.update(label='Orquestração concluída', state='complete', expanded=False)
            st.markdown(answer['content'], unsafe_allow_html=False)
            with st.expander('Ver handoffs e respostas dos agentes'):
                for step in answer['agent_trace']:
                    st.markdown(f"**{step['agent']}**", unsafe_allow_html=False)
                    st.markdown(step['content'], unsafe_allow_html=False)
        except requests.HTTPError as exc:
            code = exc.response.status_code
            answer['error'] = ('Autenticação recusada. Confira a chave no .env.' if code in (401, 403)
                               else f'Flowise retornou HTTP {code}. Confira o fluxo e o endpoint.')
        except requests.Timeout:
            answer['error'] = 'Tempo de espera excedido. O texto parcial não foi mantido.'
        except (requests.RequestException, ValueError):
            answer['error'] = 'A resposta foi interrompida ou inválida. Confira o Flowise; o texto parcial não foi mantido.'
        except ChatConfigurationError:
            answer['error'] = 'Chat indisponível: configure CREWAI_BASE_URL e CREWAI_LLM com a credencial correspondente, ou OPENROUTER_MODEL e OPENROUTER_API_KEY.'
        except Exception as exc:
            frames = traceback.extract_tb(exc.__traceback__)
            locations = ' > '.join(f'{Path(frame.filename).name}:{frame.lineno}:{frame.name}' for frame in frames)
            logging.getLogger('oxicor').error('OXICOR_CHAT_FAILURE type=%s locations=%s', type(exc).__name__, locations)
            answer['error'] = 'Não foi possível concluir a orquestração. Confira a configuração do provedor de IA, seu saldo e seus limites de uso.'
        finally:
            answer['pending'] = False
    st.rerun()
