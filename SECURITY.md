# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in drift, **please do not open a public issue.**

Instead, report it privately:

1. **Email:** Send a detailed description to the maintainer via the contact listed on the [GitHub profile](https://github.com/sauremilk).
2. **GitHub Security Advisory:** Use the [private vulnerability reporting](https://github.com/sauremilk/drift/security/advisories/new) feature.

Please include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce or a proof-of-concept.
- The drift version affected.

You will receive an acknowledgment within **72 hours** and a resolution timeline within **7 days**.

## Scope

drift is a static analysis tool that:

- **Parses Python and TypeScript source code** using AST modules and tree-sitter.
- **Invokes `git log`** via `subprocess` to read commit history.
- **Reads file system contents** of the target repository.

### Known Attack Surface

| Vector | Description | Mitigation |
| --- | --- | --- |
| Git history parsing | drift calls `git log` via `subprocess` on the target repo. A crafted `.git` directory could theoretically influence output. | drift passes only hardcoded `git log` format strings — no user-controlled arguments are interpolated into shell commands. |
| Arbitrary file read | drift reads all `.py` and `.ts` files in the target directory tree. | No file contents are executed. Parsing is done via Python `ast.parse()` which does not execute code. |
| CI environment | When run in CI (e.g., GitHub Actions), drift has access to the runner's environment. | drift does not read environment variables, secrets, or network resources beyond the local repository. |

## Disclosure Policy

We follow [coordinated disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure). Vulnerabilities will be patched before public disclosure. Credit will be given to reporters unless they prefer anonymity.
