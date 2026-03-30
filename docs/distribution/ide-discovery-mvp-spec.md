# IDE Discovery MVP Spec (VS Code and Cursor)

This is a product-spec artifact for a lightweight adoption driver without building a full extension in week one.

## Goal

Expose drift findings inside the IDE workflow so users can discover value without switching to a full CLI context.

## Scope

- In scope:
  - Quick setup guide for MCP usage in VS Code and Cursor
  - Minimal findings panel concept based on existing JSON output
  - One-click command flow for `drift scan` and `drift diff --staged-only`
- Out of scope (MVP):
  - Marketplace-ready full VS Code extension package
  - Custom language server or persistent background daemon
  - Multi-repo enterprise dashboard

## Existing Building Blocks

- MCP server support already exists in drift.
- VS Code MCP config example already exists.
- CLI commands already return deterministic actionable output.

## User Flow (MVP)

1. User installs `drift-analyzer[mcp]`.
2. User enables MCP server (`drift mcp --serve`) via IDE config.
3. User runs quick commands from command palette or task shortcuts.
4. IDE renders concise findings list with file, severity, and next action.
5. User opens file location, applies fix, re-runs diff check.

## MVP UX Contract

Each finding row should display:

- Signal label
- Severity
- File path
- One-line reason
- One concrete next action

This keeps outputs actionable and aligned with drift policy requirements.

## Proposed Minimal Data Contract

Use compact JSON output as source for UI rendering:

- `score`
- `severity`
- `findings_compact[]`
  - `rule_id`
  - `title`
  - `file`
  - `start_line`
  - `end_line`
  - `next_action` (derived when needed)

## Implementation Backlog (Post-MVP)

1. Add an IDE-focused quickstart page with screenshots or GIF.
2. Provide sample tasks for scan and staged diff checks.
3. Add optional command wrappers for concise output mode.
4. Validate perceived usefulness with 5 external users.

## Success Criteria

- Setup to first finding under 5 minutes.
- User can navigate from finding to file location in one click.
- At least one fix validated in same session with staged diff re-check.

## Risks and Mitigation

- Risk: too much output noise in IDE panel.
  - Mitigation: default to compact findings and max findings cap.
- Risk: users confuse drift with bug/security scanners.
  - Mitigation: explicit wording in setup docs: coherence analysis, not bug detection.
- Risk: setup friction around MCP config.
  - Mitigation: copy-paste config blocks and one troubleshooting section.

## Hand-off

This spec is ready to convert into implementation tickets for:

- Docs: quick setup page
- UX: panel wireframe
- Engineering: task integration and compact findings adapter
