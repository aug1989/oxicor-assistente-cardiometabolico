"""Executa unittest e as funções de teste legadas sem dependência extra."""
import importlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from config import ensure_parent, runtime_path

root = Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parent / 'tests').resolve()
output = ensure_parent(Path(sys.argv[2]).resolve()) if len(sys.argv) > 2 else ensure_parent(runtime_path('OXICOR_UNIT_TEST_RESULT', 'evaluation/unit_tests.json'))
sys.path.insert(0,str(root))
suite = unittest.defaultTestLoader.discover(str(root),pattern='test_*.py')
module = importlib.import_module('test_ml_traditional')
for name in dir(module):
    if name.startswith('test_') and callable(getattr(module,name)):
        suite.addTest(unittest.FunctionTestCase(getattr(module,name)))
with tempfile.TemporaryDirectory() as temporary:
    previous = os.getcwd()
    try:
        os.chdir(temporary)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        os.chdir(previous)
output.write_text(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(), tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), passed=result.wasSuccessful()),indent=2),encoding='utf-8')
sys.exit(0 if result.wasSuccessful() else 1)
