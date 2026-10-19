import os
import unittest
from unittest.mock import patch,Mock
from langfuse_export import payload,export_trace

class LangfuseTests(unittest.TestCase):
    def example(self):
        return dict(id='00000000-0000-0000-0000-000000000001',started_at='2026-10-19T21:00:00+00:00',duration=2,status='concluído',question='Pergunta fictícia',answer='Resposta verificada',route='DADOS',events=[dict(agent='Especialista DuckDB',kind='resultado',content='7 participantes',elapsed_seconds=2,seconds=1,token_usage=dict(prompt_tokens=10,completion_tokens=3,total_tokens=13))])
    def test_parent_child_and_usage(self):
        spans=payload(self.example())['resourceSpans'][0]['scopeSpans'][0]['spans']
        self.assertEqual(spans[1]['parentSpanId'],spans[0]['spanId'])
        self.assertEqual(len(spans[0]['traceId']),32)
        attrs={x['key']:x['value']['stringValue'] for x in spans[1]['attributes']}
        self.assertIn('"total": 13',attrs['langfuse.observation.usage_details'])
    def test_disabled_without_keys(self):
        with patch.dict(os.environ,{},clear=True),patch('langfuse_export.requests.post') as post:
            self.assertEqual(export_trace(self.example())['state'],'disabled');post.assert_not_called()
    def test_partial_failure_not_success(self):
        response=Mock(status_code=200,content=b'body');response.json.return_value={'partialSuccess':{'rejectedSpans':1}}
        with patch.dict(os.environ,{'LANGFUSE_PUBLIC_KEY':'test-public','LANGFUSE_SECRET_KEY':'test-secret'}),patch('langfuse_export.requests.post',return_value=response):
            self.assertEqual(export_trace(self.example())['state'],'partial_failure')
    def test_no_credentials_in_payload(self):
        import json
        with patch.dict(os.environ,{'LANGFUSE_SECRET_KEY':'not-to-export'}):
            self.assertNotIn('not-to-export',json.dumps(payload(self.example())))

if __name__=='__main__':unittest.main()
