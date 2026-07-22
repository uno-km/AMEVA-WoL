# Contributing to AMEVA-WoL

Thank you for your interest in contributing to **AMEVA-WoL**!

## Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/<OWNER>/AMEVA-WoL.git
   cd AMEVA-WoL
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```

4. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with test parameters
   ```

## Running Tests & Quality Checks

Run the full test suite before submitting a pull request:
```bash
pytest -q
pytest --cov=ameva_wol --cov-report=term-missing
```

Run code formatting and linting checks:
```bash
ruff check src tests
mypy src
```

## Pull Request Guidelines

- Ensure all existing unit tests pass cleanly without real network access.
- Write unit tests for new features or bug fixes.
- Follow PEP 8 guidelines, include type annotations, and maintain minimal dependencies.
- Never commit `.env`, `devices.json`, or log files.
