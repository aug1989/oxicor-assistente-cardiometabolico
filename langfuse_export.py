"""Exportação OTLP/HTTP JSON para Langfuse, sem dependências adicionais.

Credenciais somente por variáveis de ambiente. Falha de telemetria não derruba o chat.
"""
import json
import os
import uuid
from datetime import datetime
import requests

def configured():
    return bool(os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY'))

def attributes(values):
    return [{'key':key,'value':{'stringValue':value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)}} for key,value in values.items() if value is not None]

def payload(trace):
    trace_id = uuid.UUID(trace['id']).hex
    root_id = uuid.uuid5(uuid.UUID(trace['id']),'root').hex[:16]
    start = int(datetime.fromisoformat(trace['started_at']).timestamp()*1_000_000_000)
    end = start+max(1,int(trace['duration']*1_000_000_000))
    common = {'langfuse.trace.name':'OXICOR chat', 'langfuse.environment':'academic-local', 'langfuse.trace.metadata':{'local_trace_id':trace['id'],'route':trace.get('route'),'status':trace['status']}}
    spans=[dict(traceId=trace_id,spanId=root_id,name='OXICOR chat',kind=1,startTimeUnixNano=str(start),endTimeUnixNano=str(end),status={'code':2 if trace['status']=='erro' else 1},attributes=attributes(dict(common,**{'langfuse.observation.type':'chain','langfuse.observation.input':trace['question'],'langfuse.observation.output':trace.get('answer','')})))]
    previous_end=start
    for i,event in enumerate(trace['events']):
        finish=min(end,start+int(event.get('elapsed_seconds',0)*1_000_000_000))
        duration=event.get('seconds')
        begin=max(start,finish-int(duration*1_000_000_000)) if duration is not None else previous_end
        finish=max(begin+1,finish)
        kind=event.get('kind')
        observation='generation' if kind=='resultado' else 'retriever' if kind=='ferramenta' and 'RAG' in event['agent'] else 'tool' if kind=='ferramenta' else 'span'
        values=dict(common,**{'langfuse.observation.type':observation,'langfuse.observation.input':event.get('prompt_input',trace['question']),'langfuse.observation.output':event['content'],'langfuse.observation.metadata':{'output_kind':'verified_application_output','timing':'measured_generation' if duration is not None else 'interval_between_events'}})
        if observation=='generation':
            values['langfuse.observation.model.name']=os.getenv('CREWAI_LLM','ollama/qwen3:4b-instruct-oxicor-cpu')
            usage=event.get('token_usage') or {}
            if usage:
                values['langfuse.observation.usage_details']={new:int(usage[old]) for old,new in [('prompt_tokens','input'),('completion_tokens','output'),('total_tokens','total')] if old in usage}
            if str(values['langfuse.observation.model.name']).startswith(('ollama/','ollama_chat/')):
                values['langfuse.observation.cost_details']={'input':0,'output':0,'total':0}
        spans.append(dict(traceId=trace_id,spanId=uuid.uuid5(uuid.UUID(trace['id']),str(i)).hex[:16],parentSpanId=root_id,name=event['agent']+' · '+str(kind),kind=1,startTimeUnixNano=str(begin),endTimeUnixNano=str(finish),attributes=attributes(values),status={'code':1}))
        previous_end=finish
    return {'resourceSpans':[{'resource':{'attributes':attributes({'service.name':'oxicor-streamlit'})},'scopeSpans':[{'scope':{'name':'oxicor.observability','version':'1.0'},'spans':spans}]}]}

def export_trace(trace):
    if not configured():
        return {'state':'disabled','http_status':None}
    base=os.getenv('LANGFUSE_BASE_URL','https://us.cloud.langfuse.com').rstrip('/')
    if not base.startswith('https://'):
        return {'state':'invalid_endpoint','http_status':None}
    try:
        response=requests.post(base+'/api/public/otel/v1/traces',auth=(os.environ['LANGFUSE_PUBLIC_KEY'],os.environ['LANGFUSE_SECRET_KEY']),json=payload(trace),headers={'x-langfuse-ingestion-version':'4'},timeout=(5,15),allow_redirects=False)
        if not 200<=response.status_code<300:
            return {'state':'failed','http_status':response.status_code}
        body=response.json() if response.content else {}
        partial=body.get('partialSuccess',{})
        if int(partial.get('rejectedSpans',0))>0:
            return {'state':'partial_failure','http_status':response.status_code}
        return {'state':'accepted','http_status':response.status_code}
    except (requests.RequestException,ValueError,TypeError):
        return {'state':'connection_error','http_status':None}
