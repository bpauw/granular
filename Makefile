.PHONY: build setup install create-exe

build:
	uv run ruff check --show-fixes --fix src/
	uv run ruff format src/
	uv run ty check src/

setup:
	uv sync --all-groups

install:
	uv tool install --reinstall .

create-exe:
	uv run pyinstaller --console --onefile --name gran src/granular/__init__.py
