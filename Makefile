PY ?= .venv/bin/python

.PHONY: install data analysis industries figures value-tests labour-power regulation full all test lint notebooks clean-cache clean-output clean

install:
	@if command -v uv >/dev/null 2>&1; then \
		uv venv --python 3.11; \
		uv pip install --python .venv/bin/python -e ".[dev]"; \
	else \
		python3 -m venv .venv; \
		.venv/bin/python -m pip install -U pip; \
		.venv/bin/python -m pip install -e ".[dev]"; \
	fi

data:
	$(PY) -m usa_marxian fetch

analysis:
	$(PY) -m usa_marxian analyze

industries:
	$(PY) -m usa_marxian industries

figures:
	$(PY) -m usa_marxian figures

value-tests:
	$(PY) -m usa_marxian value-tests

labour-power:
	$(PY) -m usa_marxian labour-power

regulation:
	$(PY) -m usa_marxian regulation

full: analysis industries figures value-tests labour-power regulation

all: data full

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests

notebooks:
	$(PY) -m jupyter lab notebooks

clean-cache:
	rm -rf data/raw

clean-output:
	rm -rf data/processed output/tables output/figures output/report.json

clean: clean-output clean-cache
