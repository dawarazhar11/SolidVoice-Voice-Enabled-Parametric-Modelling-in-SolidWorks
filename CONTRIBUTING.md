# Contributing to SolidWorks Voice AI

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

1. **Fork and clone** the repository
2. **Install Python dependencies**: `pip install -r requirements.txt`
3. **Install Rust toolchain**: [rustup.rs](https://rustup.rs)
4. **Start infrastructure**: Qdrant (`docker run -d -p 6333:6333 qdrant/qdrant`) and Ollama (`ollama pull nomic-embed-text`)

## How to Contribute

### Reporting Bugs

Open an issue using the **Bug Report** template. Include:
- Steps to reproduce
- Expected vs actual behaviour
- SolidWorks version, Python version, OS

### Suggesting Features

Open an issue using the **Feature Request** template. Describe:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you considered

### Submitting Code

1. Create a feature branch from `main`
2. Make your changes with clear, focused commits
3. Ensure existing functionality still works
4. Open a pull request with a clear description

## Code Style

- **Python**: Follow PEP 8. Use type hints where practical.
- **Rust**: Run `cargo fmt` and `cargo clippy` before committing.

## Project Areas

| Area | Files | Description |
|------|-------|-------------|
| Voice + CLI | `solidworks_sketch.py` | Main voice loop, Claude integration, command routing |
| Memory | `part_memory.py` | Vector memory (Qdrant + Ollama embeddings) |
| SolidWorks API | `pySldWrap/` | COM API wrapper |
| Desktop UI | `ui/` | Rust/egui native Windows app |

## Questions?

Open a discussion or issue — we're happy to help.
