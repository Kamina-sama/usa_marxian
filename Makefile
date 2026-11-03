PY ?= .venv/bin/python

.PHONY: install data analysis all test lint notebooks clean-cache clean-output clean

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

all: data analysis

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
