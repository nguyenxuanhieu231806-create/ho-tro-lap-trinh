"""Run existing bounded acceptance checks and export only fresh test artifacts."""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAG = ROOT / 'specs/006-document-rag-student-import/validation'
RUN = ROOT / 'specs/005-run-four-languages/validation'
GROUPS = {
    'backend': [
        (RAG / 'verify-accounts.py', RAG / 'accounts-results.json'),
        (RAG / 'verify-import-api.py', RAG / 'import-api-results.json'),
        (RAG / 'verify-storage.py', RAG / 'storage-results.json'),
        (RUN / 'verify-runner.py', RUN / 'runner-results.json'),
        (RUN / 'verify-api.py', RUN / 'api-results.json'),
    ],
    'browser': [
        (RAG / 'verify-ui-regression.cjs', RAG / 'legacy-ui-results.json'),
        (RAG / 'verify-ui-rag.cjs', RAG / 'ui-rag-results.json'),
        (RUN / 'verify-ui.cjs', RUN / 'ui-results.json'),
    ],
    'compiler': [(RUN / 'verify-live.py', RUN / 'live-results.json')],
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in GROUPS:
        raise SystemExit('Usage: python scripts/ci_checks.py backend|browser|compiler')
    group = sys.argv[1]
    output = ROOT / 'ci-results' / group
    output.mkdir(parents=True, exist_ok=True)
    summary = {'group': group, 'checks': [], 'state': 'running'}
    if group == 'backend':
        for filename in ROOT.glob('*.py'):
            ast.parse(filename.read_text(encoding='utf-8-sig'), str(filename))
    for script, result in GROUPS[group]:
        # Remove committed historical reports: they must never masquerade as this run.
        if result.exists():
            result.unlink()
        command = ['node', str(script)] if script.suffix == '.cjs' else [sys.executable, '-B', '-X', 'utf8', str(script)]
        started = time.monotonic()
        print('Running:', script.name, flush=True)
        try:
            run = subprocess.run(command, cwd=ROOT, timeout=360 if group == 'browser' else 240, check=False)
            code = run.returncode
        except subprocess.TimeoutExpired:
            code = 124
        item = {'script': str(script.relative_to(ROOT)), 'exit_code': code,
                'seconds': round(time.monotonic() - started, 2)}
        summary['checks'].append(item)
        if result.exists():
            shutil.copy2(result, output / result.name)
        if group == 'browser':
            for image in result.parent.glob('*.png'):
                if image.stat().st_mtime >= time.time() - (time.monotonic() - started) - 2:
                    shutil.copy2(image, output / (script.stem + '-' + image.name))
        summary['state'] = 'failed' if code else 'running'
        (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        if code:
            return code
    summary['state'] = 'passed'
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
