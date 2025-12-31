.PHONY: help install dev test clean run stop restart logs

# Default target
help:
	@echo "FinSight AI Backend - Make Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install      Install Python dependencies"
	@echo "  dev          Install development dependencies"
	@echo "  run          Start FastAPI server"
	@echo "  test         Run tests"
	@echo "  clean        Clean cache and temporary files"
	@echo "  stop         Stop all processes"
	@echo "  logs         Show server logs"
	@echo ""

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -e .

# Install dev dependencies
dev:
	@echo "Installing development dependencies..."
	pip install -e ".[dev]"

# Start server
run:
	@echo "Starting FastAPI server..."
	python -m app.main

# Run tests
test:
	@echo "Running tests..."
	pytest -v

# Clean cache
clean:
	@echo "Cleaning cache and temporary files..."
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Stop server (kill process on port 8000)
stop:
	@echo "Stopping server..."
	-lsof -ti:8000 | xargs kill -9
	@echo "Server stopped."

# Restart server
restart: stop run

# Show logs (if running as background process)
logs:
	@echo "Check terminal output or use: tail -f logs/app.log"
