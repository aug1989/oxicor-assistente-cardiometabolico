"""Observabilidade local equivalente: traces persistentes, eventos, duração e status."""
import json
import sqlite3
import time
import uuid
from functools import wraps
from contextlib import contextmanager
from datetime import datetime, timezone

from config import ensure_parent, get_setting, runtime_path, setting_enabled
from privacy import redact_text, redact_value

@contextmanager
def database():
    path = ensure_parent(runtime_path('OXICOR_TRACE_DB', 'observability.sqlite3'))
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS traces (id TEXT PRIMARY KEY, started_at TEXT, question TEXT, status TEXT, duration REAL, route TEXT, answer TEXT, events TEXT, error_type TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS langfuse_exports (trace_id TEXT PRIMARY KEY, state TEXT, http_status INTEGER)')
    try:
        with db:
            yield db
    finally:
        db.close()

def observed_request(function):
    @wraps(function)
    def wrapped(question, *args, **kwargs):
        question = redact_text(question)
        if not setting_enabled('OXICOR_OBSERVABILITY_ENABLED'):
            callback = kwargs.get('on_event')
            if callback:
                def safe_callback(event):
                    callback(redact_value(dict(event)))
                kwargs['on_event'] = safe_callback
            return redact_value(function(question, *args, **kwargs))

        trace_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc).isoformat()
        timer = time.monotonic()
        events = []
        callback = kwargs.get('on_event')
        def on_event(event):
            safe_event = redact_value(dict(event, elapsed_seconds=round(time.monotonic()-timer, 3)))
            events.append(safe_event)
            with database() as db:
                db.execute('UPDATE traces SET events=?,duration=? WHERE id=?', (json.dumps(events, ensure_ascii=False), time.monotonic()-timer, trace_id))
            if callback:
                callback(safe_event)
        kwargs['on_event'] = on_event
        with database() as db:
            db.execute('INSERT INTO traces VALUES (?,?,?,?,?,?,?,?,?)', (trace_id, started, question, 'executando', 0, '', '', '[]', None))
        status, result, error = 'erro', {}, None
        try:
            result = function(question, *args, **kwargs)
            result = redact_value(result)
            status = 'controle' if result.get('route') in ('CONTROLE DE USO', 'ORIENTAÇÃO') else 'concluído'
            result['trace_id'] = trace_id
            return result
        except Exception as exc:
            error = type(exc).__name__  # Não gravar credenciais contidas em erros HTTP.
            raise
        finally:
            with database() as db:
                safe_result = redact_value(result)
                db.execute('UPDATE traces SET status=?,duration=?,route=?,answer=?,events=?,error_type=? WHERE id=?', (status, time.monotonic()-timer, safe_result.get('route', ''), safe_result.get('answer', ''), json.dumps(events, ensure_ascii=False), error, trace_id))
            # Só o fluxo atual é exportado; não enviar históricos antigos automaticamente.
            try:
                from langfuse_export import export_trace
                outcome=export_trace(dict(id=trace_id,started_at=started,question=question,status=status,duration=time.monotonic()-timer,route=safe_result.get('route',''),answer=safe_result.get('answer',''),events=events))
                with database() as db:
                    db.execute('INSERT OR REPLACE INTO langfuse_exports VALUES (?,?,?)',(trace_id,outcome['state'],outcome['http_status']))
            except Exception:
                # Falha de observabilidade não pode mascarar resultado/erro do atendimento.
                pass
    return wrapped

def read_traces(limit=100):
    with database() as db:
        rows = db.execute('SELECT * FROM traces ORDER BY started_at DESC LIMIT ?', (limit,)).fetchall()
    return [redact_value(dict(row, events=json.loads(row['events']))) for row in rows]

def render_observability():
    import streamlit as st
    if not setting_enabled('OXICOR_ADMIN_PAGES_ENABLED') or not setting_enabled('OXICOR_OBSERVABILITY_ENABLED'):
        st.error('Observabilidade está desativada. Habilite-a somente em ambiente controlado e protegido.')
        return
    st.title('Observabilidade · OXICOR')
    from langfuse_export import configured
    if configured():
        st.info('Langfuse conectado por configuração. Confira abaixo a confirmação de envio de cada solicitação. Perguntas e respostas novas são enviadas ao projeto configurado; evite dados pessoais.')
        st.link_button('Abrir Langfuse',get_setting('LANGFUSE_BASE_URL','https://us.cloud.langfuse.com'))
        with database() as db:
            exports=[dict(row) for row in db.execute('SELECT * FROM langfuse_exports ORDER BY rowid DESC LIMIT 20')]
        if exports:
            st.dataframe(exports,hide_index=True,use_container_width=True)
    st.caption('Monitoramento local equivalente: cada solicitação recebe um identificador e registra ferramentas, agentes, duração e resultado. Horários em UTC.')
    st.button('Atualizar registros')
    traces = read_traces()
    completed = [t for t in traces if t['status'] == 'concluído']
    a,b,c = st.columns(3)
    a.metric('Solicitações registradas', len(traces))
    b.metric('Concluídas com agentes', len(completed))
    c.metric('Erros', sum(t['status']=='erro' for t in traces))
    st.info('Execução local com Ollama: sem tarifa de API de LLM. Energia e hardware não são contabilizados. Tokens aparecem somente quando informados pelo provedor.')
    if not traces:
        st.write('Faça uma pergunta no Chat para gerar o primeiro trace.')
        return
    st.dataframe([dict(ID=t['id'][:8], início=t['started_at'], status=t['status'], rota=t['route'], segundos=round(t['duration'],1), pergunta=t['question']) for t in traces], hide_index=True, use_container_width=True)
    st.download_button('Baixar traces em JSON', json.dumps(traces, ensure_ascii=False, indent=2), 'oxicor_traces.json', 'application/json')
    selected = st.selectbox('Detalhar solicitação', [t['id'] for t in traces], format_func=lambda value: next(t['question'][:80]+' · '+value[:8] for t in traces if t['id']==value))
    current = next(t for t in traces if t['id']==selected)
    st.code(current['id'])
    for event in current['events']:
        with st.expander(f"{event.get('elapsed_seconds',0):.1f}s · {event['agent']} · {event.get('kind','resultado')}"):
            st.markdown(event.get('content',''), unsafe_allow_html=False)
            if event.get('token_usage'):
                st.json(event['token_usage'])
    if current['error_type']:
        st.error(current['error_type'])
    st.markdown(current['answer'], unsafe_allow_html=False)

def render_evaluation():
    import streamlit as st
    if not setting_enabled('OXICOR_ADMIN_PAGES_ENABLED'):
        st.error('Avaliação é uma página administrativa e está desativada neste ambiente.')
        return
    st.title('Avaliação · Golden dataset')
    st.caption('Suíte local equivalente, com critérios determinísticos publicados. Não usa DeepEval nem um juiz LLM.')
    path = runtime_path('OXICOR_EVAL_RESULT', 'evaluation/results.json')
    if not path.exists():
        st.info('A avaliação ainda não foi executada. Nenhum resultado foi presumido.')
        return
    result = json.loads(path.read_text(encoding='utf-8'))
    st.write(result.get('methodology',''))
    rows = result['results']
    a,b = st.columns(2)
    a.metric('Perguntas executadas',len(rows))
    b.metric('Critérios atendidos', f"{sum(r['passed'] for r in rows)}/{len(rows)}")
    st.dataframe([{k:r.get(k) for k in ('id','question','route','expected_route','relevance','grounding','passed','seconds')} for r in rows], hide_index=True, use_container_width=True)
    st.download_button('Baixar resultados completos', json.dumps(result, ensure_ascii=False, indent=2), 'golden_results.json', 'application/json')
    for row in rows:
        with st.expander(f"{row['id']} · {'Passou' if row['passed'] else 'Revisar'} · {row['question'][:70]}"):
            st.markdown(row.get('answer',''), unsafe_allow_html=False)
            st.write('Critérios:', row.get('checks'))
            st.caption('Trace: '+row.get('trace_id','não disponível'))
