# Contributing to MDM

Thank you for your interest in contributing to MDM!

## Contributor License Agreement (CLA)

**MDM does not require a CLA (Contributor License Agreement).**

By contributing code, documentation, or other materials to this project, you agree that your contributions will be licensed under the same license as the project (Apache-2.0).

## Developer Certificate of Origin (DCO)

While not strictly required, contributors are encouraged to include a "Signed-off-by" line in their commit messages:

```
Signed-off-by: Your Name <your.email@example.com>
```

This certifies that you have the right to submit the work under the project's license. You can add this automatically with:

```bash
git commit -s -m "Your commit message"
```

## Commercial Support

**Commercial support and consulting services are available** for organizations requiring:

- Custom domain adapters
- Integration assistance
- Extended support and maintenance
- Training and workshops
- Custom feature development

For commercial inquiries, see the maintainer in `pyproject.toml` or open a GitHub Discussion.

**Support Scope:**
- **Community Support**: Best-effort via GitHub Issues (no SLA)
- **Commercial Support**: Defined SLA and response times (contact for details)
- **Security Issues**: See [SECURITY.md](../SECURITY.md) for reporting process

---

## Code of Conduct

- Be respectful and professional
- Focus on constructive feedback
- Respect intellectual property and attribution

---

## How to Contribute

### Reporting Issues

- **Bug Reports**: Use GitHub Issues with clear reproduction steps
- **Security Issues**: See SECURITY.md for private reporting
- **Feature Requests**: Open an issue with clear use case description

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Update documentation if needed
6. Commit with clear messages (`git commit -m 'Add amazing feature'`)
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Setup

```bash
# Clone repository
git clone https://github.com/MeetlyTR/mdm-engine.git
cd mdm-engine

# Install in editable mode
pip install -e ".[dev]"

# Run tests
python run_all_tests.py
```

---

## Contribution Guidelines

### Code Style

- Follow PEP 8 (Python style guide)
- Use type hints where applicable
- Keep functions focused and under 100 lines
- Add docstrings for public APIs

### Testing

- All new features should include tests
- Run `python run_all_tests.py` before submitting PR
- Maintain or improve test coverage

### Documentation

- Update README.md for user-facing changes
- Update CHANGELOG.md for notable changes
- Add docstrings for new functions/classes

### Public API Changes

**Breaking changes** to public API require:
- Major version bump (1.0 → 2.0)
- Migration guide in CHANGELOG.md
- Deprecation warnings for at least one minor version

**Public API** (stable):
- `mdm_engine.decide()`
- `mdm_engine.replay_trace()`
- `mdm_engine.moral_decision_engine()`
- `mdm_engine.get_config()`, `mdm_engine.list_profiles()`
- CLI commands (`mdm dashboard`, etc.)

---

## Areas for Contribution

### High Priority

- Additional config profiles for specific domains
- Performance optimizations
- Extended test coverage
- Documentation improvements

### Medium Priority

- Additional visualization plots
- Example adapters for common domains
- CI/CD improvements
- Internationalization (i18n) expansion

### Low Priority

- Additional example scripts
- Documentation translations
- Code style improvements

---

## Questions?

- **General Questions**: Open a GitHub Discussion
- **Security**: See SECURITY.md
- **Contact**: See repository maintainer (pyproject.toml) or open an issue.

---

**Thank you for contributing to MDM!**
