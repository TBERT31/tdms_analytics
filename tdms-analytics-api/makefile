.PHONY: help install dev start stop clean test lint format docs

# Default target
help:
	@echo "TDMS Analytics API - Available commands:"
	@echo ""
	@echo "  install     Install dependencies"
	@echo "  dev         Install development dependencies"
	@echo "  start       Start the application"
	@echo "  stop        Stop all services"
	@echo "  clean       Clean up containers and volumes"
	@echo "  test        Run tests"
	@echo "  lint        Run linting"
	@echo "  format      Format code"
	@echo "  docs        Generate documentation"
	@echo "  init-db     Initialize ClickHouse database"
	@echo "  docker-up   Start ClickHouse with Docker"
	@echo "  docker-down Stop Docker services"

# Installation
install:
	poetry install

dev:
	poetry install --with dev
	poetry install --extras fast

# Application
start:
	poetry run python src/tdms_analytics/main.py

start-dev:
	poetry run uvicorn tdms_analytics.main:app --reload --host 0.0.0.0 --port 8000

# Docker services
docker-up:
	docker-compose up -d clickhouse
	@echo "Waiting for ClickHouse to be ready..."
	@sleep 10

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f clickhouse

# Database
init-db: docker-up
	@echo "Initializing ClickHouse database..."
	@sleep 5
	poetry run python src/tdms_analytics/scripts/init_db.py

# Development
test:
	poetry run pytest -v

test-cov:
	poetry run pytest --cov=tdms_analytics --cov-report=html

lint:
	poetry run flake8 src/
	poetry run mypy src/

format:
	poetry run black src/
	poetry run isort src/

format-check:
	poetry run black --check src/
	poetry run isort --check-only src/

# Cleanup
clean:
	docker-compose down -v
	docker system prune -f

clean-all: clean
	poetry env remove --all

# Full setup for new environment
setup: install docker-up init-db
	@echo "✅ Setup complete! You can now run 'make start' to launch the API"

# Quick development setup
dev-setup: dev docker-up init-db
	@echo "✅ Development setup complete!"

# Documentation
docs:
	@echo "API documentation available at:"
	@echo "  Swagger UI: http://localhost:8000/docs"
	@echo "  ReDoc: http://localhost:8000/redoc"

# Health check
health:
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ API not responding"

# Example TDMS file generation
generate-sample:
	poetry run python -c "
import numpy as np
import datetime as dt
from nptdms import TdmsWriter, ChannelObject

N = 1_000_000  # 1M points for demo
FS = 10_000
t = np.arange(N, dtype=np.float64) / FS
sig1 = np.sin(2*np.pi*50*t).astype(np.float32)
start = dt.datetime(2024, 1, 1, 0, 0, 0)

def props(unit='V'):
    return {
        'NI_UnitDescription': unit,
        'wf_start_time': start,
        'wf_increment': 1.0 / FS,
        'wf_samples': N,
    }

with TdmsWriter('sample.tdms') as w:
    ch1 = ChannelObject('Demo', 'Sine50Hz', sig1, properties=props())
    w.write_segment([ch1])

print('Generated sample.tdms')
"

# Test ingestion
test-ingest: generate-sample
	@curl -X POST "http://localhost:8000/ingest" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@sample.tdms" \
		-s | python -m json.tool