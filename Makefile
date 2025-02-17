.PHONY: install run test lint format clean help docker-up docker-down venv db-up db-down

PYTHON := python3.11
PIP := pip
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_DB := docker-compose -f docker-compose.db.yml
VENV_NAME := venv
VENV_BIN := $(VENV_NAME)/bin
VENV_ACTIVATE := . $(VENV_BIN)/activate


help:
	@echo "Available commands:"
	@echo "  make venv        - Create Python virtual environment"
	@echo "  make install     - Install dependencies"
	@echo "  make run        - Run the development server"
	@echo "  make db-up      - Start PostgreSQL database"
	@echo "  make db-down    - Stop PostgreSQL database"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run flake8 linter"
	@echo "  make format     - Format code with black"
	@echo "  make clean      - Remove Python file artifacts and virtual environment"
	@echo "  make docker-up  - Start all Docker containers"
	@echo "  make docker-down - Stop all Docker containers"

venv:
	$(PYTHON) -m venv $(VENV_NAME)
	@echo "Virtual environment created. To activate, run: source $(VENV_NAME)/bin/activate"

install: venv
	$(VENV_BIN)/pip install -r requirements.txt
	$(VENV_BIN)/pip install black flake8 pytest pytest-django

db-up:
	$(DOCKER_COMPOSE_DB) up -d
	sleep 5  # Give the container a moment to start
	@echo "Creating database if it doesn't exist..."
	@PGPASSWORD=${POSTGRES_PASSWORD} createdb -h 127.0.0.1 -U ${POSTGRES_USER} ${POSTGRES_DB} 2>/dev/null || true

db-down:
	$(DOCKER_COMPOSE_DB) down
	sleep 2  # Wait for container to stop properly

run:
	$(PYTHON) manage.py migrate
	$(PYTHON) manage.py runserver 0.0.0.0:8000

test:
	if [ -d "/app" ]; then \
		DJANGO_SETTINGS_MODULE=faucet_project.test_settings python -m pytest; \
	else \
		DJANGO_SETTINGS_MODULE=faucet_project.test_settings PYTHONPATH=$(PWD) python -m pytest; \
	fi

test-v:
	if [ -d "/app" ]; then \
		DJANGO_SETTINGS_MODULE=faucet_project.test_settings python -m pytest -v; \
	else \
		DJANGO_SETTINGS_MODULE=faucet_project.test_settings PYTHONPATH=$(PWD) python -m pytest -v; \
	fi

test-cov:
	if [ -d "/app" ]; then \
		DJANGO_SETTINGS_MODULE=faucet_project.test_settings python -m pytest --cov=faucet --cov-report=term-missing; \
	else \
		DJANGO_SETTINGS_MODULE=faucet_project.test_settings PYTHONPATH=$(PWD) python -m pytest --cov=faucet --cov-report=term-missing; \
	fi

lint:
	flake8 . --max-line-length=100 --exclude=venv,migrations,.git,__pycache__

format:
	black . --exclude=venv/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	rm -rf $(VENV_NAME)

docker-up:
	$(DOCKER_COMPOSE) up --build -d
	$(DOCKER_COMPOSE) exec web python manage.py migrate

docker-down:
	$(DOCKER_COMPOSE) down 