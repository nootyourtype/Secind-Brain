# Contributing to Second Brain

Thank you for your interest in contributing! 🧠

## Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. Follow the setup steps in the [README](README.md)

## How to Contribute

### 🐛 Reporting Bugs
Open a [GitHub Issue](../../issues) with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your OS, Python version, and Node version

### 💡 Suggesting Features
Open a GitHub Issue with the `enhancement` label and describe:
- The problem you're trying to solve
- Your proposed solution

### 🔧 Submitting Code

1. Create a branch: `git checkout -b feat/your-feature-name`
2. Make your changes
3. Commit with a clear message: `git commit -m "feat: add X feature"`
4. Push and open a **Pull Request**

## Code Style

- **Python**: Follow PEP 8. Use descriptive variable names.
- **JavaScript/React**: Keep components small and focused.
- **CSS**: Use the existing CSS custom properties (`var(--cyan)`, `var(--grad)`, etc.)

## Project Structure

```
├── api.py          # FastAPI REST endpoints
├── main.py         # Orchestrator & clipboard watcher
├── agent.py        # AI enrichment logic
├── ingest.py       # File parsing & indexing
├── synthesizer.py  # LLM prompt/response handling
├── web/src/        # React dashboard
└── test_brain.py   # Test suite
```

## Questions?

Open an issue — happy to help! 🚀
