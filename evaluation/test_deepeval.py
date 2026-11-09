"""DeepEval sobre respostas reais do fluxo OXICOR, sem juiz LLM adicional."""
import json
import time
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from evaluate_golden import evaluate
from local_rag import consult_local
from multi_agents import run_multi_agent


GOLDEN_CASES = json.loads(
    Path(__file__).with_name('golden.json').read_text(encoding='utf-8')
)
_last_started = None


class GoldenCompatibilityMetric(BaseMetric):
    """Reutiliza, sem alterações, os critérios da avaliação determinística atual."""

    def __init__(self, case, result):
        self.case = case
        self.route = result['route']
        self.trace = result.get('trace', [])
        self.threshold = 1.0
        self.async_mode = False
        self.include_reason = True
        self.score = None
        self.success = None
        self.reason = None
        self.error = None

    @property
    def __name__(self):
        return 'OXICOR golden compatibility'

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        assessment = evaluate(
            self.case,
            {
                'answer': test_case.actual_output,
                'route': self.route,
                'trace': self.trace,
            },
        )
        self.score = float(assessment['passed'])
        self.success = assessment['passed']
        grounding = assessment['grounding']
        self.reason = (
            f"rota correta={self.route == self.case['expected_route']}; "
            f"relevância={assessment['relevance']:.3f}; "
            f"grounding={'não aplicável' if grounding is None else grounding}; "
            f"grupos atendidos={sum(assessment['checks'])}/{len(assessment['checks'])}"
        )
        return self.score

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            self.success = (
                self.score is not None
                and self.threshold is not None
                and self.score >= self.threshold
            )
        return self.success

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case, *args, **kwargs)


@pytest.mark.parametrize('case', GOLDEN_CASES, ids=[case['id'] for case in GOLDEN_CASES])
def test_golden_case_through_real_app(case):
    global _last_started
    if _last_started is not None:
        time.sleep(max(0, 16 - (time.monotonic() - _last_started)))

    started = time.monotonic()
    _last_started = started
    result = run_multi_agent(case['question'], consult_local)
    test_case = LLMTestCase(
        input=case['question'],
        actual_output=result['answer'],
        retrieval_context=[
            item['content']
            for item in result.get('trace', [])
            if item.get('kind') == 'ferramenta'
        ],
    )
    assert_test(
        test_case,
        [GoldenCompatibilityMetric(case, result)],
        run_async=False,
    )
