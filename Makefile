setup:
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
lint:
ruff src sims tests
test:
pytest -q
run-100km:
python sims/run_leo_100km.py --config configs/leo_100km.yaml
sweep-extent:
python sims/run_sweep_extent.py
