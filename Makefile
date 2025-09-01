PY?=python

.PHONY: venv lint test decode events watch

venv:
	$(PY) -m venv .venv
	. .venv/Scripts/activate && $(PY) -m pip install -U pip && $(PY) -m pip install -e ".[dev]"

lint:
	$(PY) -m ruff check .
	$(PY) -m black --check .

test:
	$(PY) -m pytest -q tools/tests

decode:
	$(PY) tools/wtvb_decode_5561.py wtvb_stream.csv wtvb_decoded.csv

events:
	$(PY) tools/events_from_csv.py wtvb_decoded.csv wtvb_events.csv 120 0.20

watch:
	$(PY) tools/watch_events.py wtvb_decoded.csv --thr 120 --gap-s 0.20 --hz 25 --from-start
