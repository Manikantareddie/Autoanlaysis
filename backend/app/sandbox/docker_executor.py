from __future__ import annotations
import json, shutil, subprocess, tempfile
from pathlib import Path
from fastapi import HTTPException, status

IMAGE = 'insightpilot-python-sandbox:local'

def run_python_sandbox(code: str, dataset_path: Path, timeout_seconds: int = 20) -> dict:
    if shutil.which('docker') is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Secure Python execution is unavailable: Docker is not installed.')
    with tempfile.TemporaryDirectory(prefix='insightpilot-job-') as temp:
        root = Path(temp); job_dir = root / 'job'; output_dir = root / 'output'; job_dir.mkdir(); output_dir.mkdir()
        (job_dir / 'job.json').write_text(json.dumps({'code': code}), encoding='utf-8')
        command = ['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','64','--memory','512m','--cpus','1','--mount',f'type=bind,src={dataset_path.parent},dst=/input,readonly','--mount',f'type=bind,src={job_dir},dst=/job,readonly','--mount',f'type=bind,src={output_dir},dst=/output',IMAGE]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        except subprocess.TimeoutExpired as error:
            raise HTTPException(status_code=408, detail='Python sandbox execution timed out.') from error
        if result.returncode != 0:
            raise HTTPException(status_code=422, detail='Python sandbox execution failed.')
        artifacts = [path.name for path in output_dir.glob('*.png') if path.stat().st_size <= 5_000_000]
        return {'stdout': result.stdout[:10000], 'artifacts': artifacts}
