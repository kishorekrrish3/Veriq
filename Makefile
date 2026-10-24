# Makefile for VERIQ
# Tagline: Code is generated. Proof is earned.

.PHONY: install run test smoke benchmark lint clean docker-build docker-up

PYTHON ?= python

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

test:
	$(PYTHON) -m pytest tests -v

smoke:
	$(PYTHON) scripts/smoke_test.py

benchmark:
	$(PYTHON) scripts/benchmark.py

lint:
	$(PYTHON) -m ruff check app tests scripts || true

docker-build:
	docker build -t veriq:latest .
	docker build -t veriq-sandbox:latest ./sandbox

docker-up:
	docker compose up -d

clean:
	rm -rf __pycache__ .pytest_cache data/test_veriq.db data/workspaces/*
