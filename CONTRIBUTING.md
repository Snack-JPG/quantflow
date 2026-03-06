# Contributing to QuantFlow

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/Snack-JPG/quantflow.git
cd quantflow

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

## Running Tests

```bash
# All tests
pytest backend/tests/ -v

# Unit tests only
pytest backend/tests/unit/

# Integration tests
pytest backend/tests/integration/

# Benchmarks
pytest backend/tests/benchmarks/ --benchmark-only
```

## Code Style

- **Python:** Follow PEP 8. Type hints encouraged.
- **TypeScript:** ESLint with strict mode enabled.
- **Commits:** Use conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a PR with a clear description of changes

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design.
See [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for the research behind the analytics.
