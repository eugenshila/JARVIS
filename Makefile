.PHONY: install dev serve frontend doctor test clean

install:
	pip install -e . --break-system-packages

dev:
	pip install -e .[all,dev] --break-system-packages
	cd frontend && npm install

serve:
	PYTHONPATH=src python -m jarvis.cli.main serve --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

doctor:
	PYTHONPATH=src python -m jarvis.cli.main doctor

test:
	PYTHONPATH=src python -m pytest tests/ -v || PYTHONPATH=src python -m jarvis.cli.main ask "test" --mock

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
