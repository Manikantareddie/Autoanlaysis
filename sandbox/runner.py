import json, os, runpy, sys
from pathlib import Path

job = json.loads(Path('/job/job.json').read_text(encoding='utf-8'))
code = job.get('code', '')
if not isinstance(code, str) or len(code) > 20000:
    raise SystemExit('invalid job')
os.chdir('/output')
namespace = {'__name__': '__main__'}
exec(compile(code, '<generated-analysis>', 'exec'), namespace, namespace)
