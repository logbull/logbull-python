lint:
	uv run ruff format . && uv run ruff check . --fix && uv run mypy logbull/

test:
	uv run pytest

test-cov:
	uv run pytest --cov=logbull --cov-report=html --cov-report=term-missing

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/

build:
	uv build

install-dev:
	uv sync --dev

pre-commit-install:
	uv run pre-commit install

pre-commit:
	uv run pre-commit run --all-files
