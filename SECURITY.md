# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in localfs, please report it privately by emailing **rkriad585@example.com**.

Please do NOT open a public issue for security vulnerabilities.

We will acknowledge receipt within 48 hours and provide a timeline for a fix. Once the fix is released, we will publish a security advisory.

## Scope

- Authentication bypass
- Path traversal
- Remote code execution
- Data exposure

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x     | Yes       |

## Best Practices

- Always enable `WEBSITE_ACCESS_KEY_REQUIRED = True` in `config.py` for public-facing instances.
- Keep the application behind a reverse proxy (nginx, Caddy) for production use.
- Run with a non-root user inside Docker.
- Regularly update dependencies with `pip install --upgrade -r requirements.txt`.
