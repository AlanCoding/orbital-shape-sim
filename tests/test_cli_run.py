import subprocess, sys, os
from pathlib import Path

def test_leo_100km_cli_completes_under_timeout():
    repo_root = Path(__file__).resolve().parents[1]
    cmd = ["timeout", "3", sys.executable, "sims/run_leo_100km.py", "--config", "configs/leo_100km.yaml"]
    subprocess.run(cmd, cwd=repo_root, check=True, env={**os.environ, "PYTHONPATH": "src"})

