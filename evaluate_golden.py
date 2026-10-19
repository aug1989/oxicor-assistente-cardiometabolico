"""Avalia o chat real; resultados e traces não são simulados."""
import json
import os
import sys
import time
import unicodedata
from pathlib import Path
from datetime import datetime, timezone
from multi_agents import run_multi_agent
from local_rag import consult_local

def normalized(value):
    return ' '.join(unicodedata.normalize('NFKD', value).encode('ascii','ignore').decode().lower().split())

def evaluate(case, result):
    answer = normalized(result.get('answer',''))
    checks = [any(normalized(term) in answer for term in alternatives) for alternatives in case['expected_groups']]
    relevance = sum(checks)/len(checks)
    evidence = [e['content'] for e in result.get('trace',[]) if e.get('kind')=='ferramenta']
    grounding = float(all(normalized(text) in answer for text in evidence)) if evidence else None
    correct_route = result.get('route') == case['expected_route']
    return dict(relevance=relevance, grounding=grounding, checks=checks, passed=correct_route and all(checks) and grounding != 0.0)

def main():
    cases = json.loads(Path(sys.argv[1] if len(sys.argv)>1 else '/app/evaluation/golden.json').read_text(encoding='utf-8'))
    destination = Path(os.getenv('OXICOR_EVAL_RESULT','/app/data/evaluation/results.json'))
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = dict(started_at=datetime.now(timezone.utc).isoformat(), methodology='Execução real do chat com CrewAI/Ollama. Relevância = fração de grupos de termos esperados presentes; aprovação exige todos e rota correta. Grounding = preservação integral das evidências das ferramentas na resposta (1 ou 0); sem ferramenta, não aplicável. São proxies determinísticos, não validação semântica completa nem comprovação clínica. Casos definidos antes da execução. Limites de uso mantidos.', results=[])
    for case in cases:
        start = time.monotonic()
        print('INICIO',case['id'],case['question'],flush=True)
        try:
            result = run_multi_agent(case['question'], consult_local)
            record = dict(case, **evaluate(case,result), route=result['route'], answer=result['answer'], trace_id=result.get('trace_id',''), seconds=round(time.monotonic()-start,2))
        except Exception as exc:
            record = dict(case, passed=False, relevance=0., grounding=None, checks=[], route='ERRO', answer='', error=type(exc).__name__, seconds=round(time.monotonic()-start,2))
        report['results'].append(record)
        report['updated_at'] = datetime.now(timezone.utc).isoformat()
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(destination)
        print('FIM',case['id'],record['passed'],record['seconds'],flush=True)
        # Respeitar o intervalo global entre solicitações, sem contornar quotas.
        time.sleep(max(0,16-(time.monotonic()-start)))
    print('RESULTADO',sum(row['passed'] for row in report['results']),len(cases),flush=True)

if __name__ == '__main__':
    main()
