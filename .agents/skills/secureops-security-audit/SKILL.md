---
name: secureops-security-audit
description: >
  Security engineer and audit skill for AI-powered ITSM codebases.
  Performs a structured threat-model-driven security audit covering OWASP Top 10,
  OWASP LLM Top 10, Python-specific vulnerabilities, agentic pipeline attack surfaces,
  secret management, database security, and frontend injection risks.
  Use when the user asks to audit a SecureOps-style codebase, find vulnerabilities,
  harden the security posture, or produce a security findings report.
---

# SecureOps Security Audit Skill

## Overview

This skill conducts a thorough, threat-model-driven security audit of the SecureOps
multi-agent ITSM codebase. It maps findings to standardised threat taxonomies,
assigns severity (Critical / High / Medium / Low / Info), and produces concrete
code-level remediations.

---

## Threat Model Scope

Audit every file against these threat categories, in order:

### 1. OWASP LLM Top 10 (2025)
- **LLM01 – Prompt Injection**: User input reaching LLM system prompts without sanitisation or role separation.
- **LLM02 – Sensitive Information Disclosure**: LLM returning data from other tenants, system config, or internal state.
- **LLM03 – Supply Chain**: Untrusted packages, pinned deps, model/embedding integrity.
- **LLM04 – Data & Model Poisoning**: Untrusted content injected into the knowledge base or ChromaDB.
- **LLM05 – Improper Output Handling**: LLM output rendered as HTML/markdown without sanitisation; `unsafe_allow_html=True` patterns.
- **LLM06 – Excessive Agency**: Agents granted permissions or tool access beyond the minimum required.
- **LLM07 – System Prompt Leakage**: System prompt retrievable through normal API responses.
- **LLM08 – Vector and Embedding Weaknesses**: ChromaDB query manipulation, cosine similarity abuse.
- **LLM09 – Misinformation**: Auto-resolved tickets generating and storing hallucinated knowledge articles.
- **LLM10 – Unbounded Consumption**: No rate limiting, token caps, or per-request quotas.

### 2. OWASP Top 10 (Classic Web/App)
- **A01 – Broken Access Control**: No authentication on Streamlit app, no multi-tenancy isolation.
- **A02 – Cryptographic Failures**: API keys, secrets, connection strings in source or environment.
- **A03 – Injection**: SQL injection via SQLAlchemy raw queries; ChromaDB query injection.
- **A05 – Security Misconfiguration**: Debug flags, verbose error messages exposed to UI.
- **A06 – Vulnerable Components**: Outdated packages with known CVEs.
- **A09 – Security Logging & Monitoring**: Missing audit events, PII in logs, log injection.

### 3. Python-Specific
- Hardcoded secrets in code.
- Use of `eval()`, `exec()`, `pickle`, or `subprocess` with untrusted input.
- `datetime.utcnow()` deprecation (naive datetimes leak timezone assumptions).
- Mutable default arguments.
- Exception swallowing (bare `except:` or `except Exception:` with no re-raise or alerting).
- Module-level side effects at import time (e.g. DB connections, API clients at top of file).

### 4. Agentic Pipeline
- Trust boundary violations: does any agent receive or forward unvalidated data from upstream?
- Fail-open paths: any exception handler that defaults to `approved` or `True`.
- Trace ID / session ID collision or predictability.
- Knowledge base poisoning via extraction agent: does resolution_text get stored without sanitisation?
- Confidence threshold tampering: is the threshold configurable via user input?

### 5. Infrastructure & Secrets
- `.env` file committed (check `.gitignore`).
- `GOOGLE_API_KEY` exposure through logs, error messages, or HTTP responses.
- SQLite file world-readable, no encryption.
- ChromaDB persistence path traversal.
- Streamlit running without authentication in a network-accessible context.

### 6. Frontend (Streamlit `app.py`)
- XSS via `unsafe_allow_html=True` with user-controlled content.
- User input inserted directly into HTML strings (`f"...{message}..."`) without escaping.
- No Content-Security-Policy header.
- No input length enforcement at the UI layer.

---

## Audit Execution Steps

When you execute this skill on a codebase:

1. **Read all source files** (not just the ones the user has open).
2. **Map each file to relevant threat categories** above.
3. **For each finding**:
   - Assign a severity: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or `INFO`.
   - State the exact file, line number(s), and the vulnerable code snippet.
   - Explain the exploit scenario (how an attacker would abuse this).
   - Provide a concrete code fix.
4. **Produce a findings report** as a markdown artifact with a summary table and per-finding sections.
5. **Apply all Critical and High fixes** directly to the source files.
6. **Apply Medium and Low fixes** and note any Low/Info items that require architectural decisions.

---

## Severity Definitions

| Severity | Definition |
|---|---|
| CRITICAL | Exploitable without authentication; direct RCE, data exfiltration, or complete security bypass |
| HIGH | Significant impact requiring specific conditions; XSS with sensitive data, auth bypass, prompt injection |
| MEDIUM | Requires additional attacker capability; information disclosure, missing rate limiting |
| LOW | Defence-in-depth improvement; logging gaps, minor misconfigurations |
| INFO | Best practice note; no immediate exploitability |

---

## Output Format

Produce a `security_audit_report.md` artifact with:
- Executive summary
- Findings summary table (ID, Severity, File, Title)
- Per-finding sections with: Description, Threat Category, Exploit Scenario, Vulnerable Code, Remediation Code
- Remediation status (Fixed / Requires Architectural Decision / Accepted Risk)
