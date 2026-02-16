# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities privately:

- **GitHub**: Use the repository's Security tab → "Report a vulnerability", or
- **Maintainer**: See the maintainer contact in `pyproject.toml` (no direct email in repo).

**Subject**: `[SECURITY] MDM Vulnerability Report`

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (typically 30-90 days)

### Disclosure Policy

- We will acknowledge receipt of your report within 48 hours
- We will provide regular updates on the status of the vulnerability
- We will notify you when the vulnerability is fixed
- We will credit you in the security advisory (if desired)

## Security Best Practices

### For Users

1. **Keep Updated**: Always use the latest version of MDM
2. **Review Traces**: Regularly audit decision traces for anomalies
3. **Domain Adapter Security**: Ensure your domain adapter layer follows security best practices
4. **Input Validation**: Validate all inputs before passing to MDM
5. **Access Control**: Restrict access to trace files and decision logs

### For Developers

1. **Dependency Updates**: Regularly update dependencies (`pip list --outdated`)
2. **Code Review**: All security-related changes require review
3. **Testing**: Security fixes must include tests
4. **Documentation**: Security changes must be documented in CHANGELOG.md

## Known Security Considerations

### 1. Trace Data Sensitivity

**Risk**: Traces may contain sensitive information from domain adapters.

**Mitigation**:
- Encrypt trace files at rest
- Implement access controls
- Follow GDPR/KVKK requirements for personal data

### 2. Deterministic Mode

**Risk**: Deterministic mode (`deterministic=True`) may expose internal state through replay.

**Mitigation**:
- Use deterministic mode only in trusted environments
- Review trace content before sharing
- Consider non-deterministic mode for production if acceptable

### 3. Input Validation

**Risk**: Invalid `raw_state` input may trigger unexpected behavior.

**Mitigation**:
- MDM includes fail-safe mechanisms
- Always validate inputs in domain adapter layer
- Monitor `human_escalation=True` events

### 4. Dependency Vulnerabilities

**Risk**: Third-party dependencies may have vulnerabilities.

**Mitigation**:
- Regularly update dependencies
- Monitor security advisories for dependencies
- Use `pip audit` or similar tools

## Security Contact

For security-related questions or to report vulnerabilities use the repository's Security tab or the maintainer contact listed in `pyproject.toml`. Do not put direct email addresses in the repo.

---

**Last Updated**: 2026-02-13
