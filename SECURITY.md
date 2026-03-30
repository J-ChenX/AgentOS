# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub Issues.**

To report a vulnerability, choose one of the following:

1. **GitHub Private Vulnerability Reporting** (preferred): Go to the repository's
   **Security** tab → **Advisories** → **Report a vulnerability**.
2. **Email**: Contact the maintainers directly (see repository profile for contact).

We will acknowledge your report within **72 hours** and aim to provide a fix
timeline within **7 days** for confirmed High/Critical vulnerabilities.

## Scope

This policy covers the `agentos` Python package (`src/agentos/`).

The following are **out of scope**:
- Example projects (`examples/`)
- Documentation files
- Development tooling configuration

## Known Security Considerations

The following behaviors are by design and documented:

- **`system_shell` builtin skill**: Executes shell commands on behalf of the LLM.
  The `BLOCKED_PATTERNS` blocklist is best-effort and explicitly **not** a security
  boundary. Do not expose AgentOS to untrusted user input in production without
  additional access controls.

- **`FileScope`**: Restricts file access to the declared project directory, but
  does not prevent all file operations performed via shell commands. It is a
  convenience guardrail, not a sandbox.

- **LLM prompt injection**: As with all LLM-based agents, prompt injection attacks
  via untrusted tool results are an inherent risk. Validate inputs at system
  boundaries when deploying in sensitive environments.
