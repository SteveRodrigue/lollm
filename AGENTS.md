# Repository Contribution Rules

- Never add private information to Git.
- Do not commit personal usernames, home-directory paths, machine-specific absolute paths, credentials, tokens, private keys, or local environment files.
- Keep local model files, runtimes, caches, logs, reports, and virtual environments ignored.
- Always use the repository `.venv` interpreter for Python commands, tests, linters, and project tools; shell activation is optional, but do not use the system Python when the project environment is available.
- Use repository-relative paths, documented placeholders, or environment variables for machine-specific configuration.
- Before committing, search the staged files for personal paths and secrets.