---
name: "Community Study: Self-Analysis"
about: "Run drift on your own repo and share what you found"
title: "[Study] Self-Analysis: "
labels: ["community-study", "self-analysis"]
assignees: []
---

## Study: Self-Analysis Challenge (S5 / S13)

Thank you for participating! This takes about 15–30 minutes.

### Setup

**Drift version:** <!-- e.g. 1.2.0 -->

**Your repo (optional):** <!-- URL or short description. You may keep this private. -->

**How long have you worked on this repo?** <!-- e.g. 6 months, 2 years -->

**Framework / language:** <!-- e.g. Django / Python, Express / TypeScript -->

### Step 1 — Run drift

```bash
drift analyze --repo . --format rich
```

**Total findings reported:** <!-- number -->

### Step 2 — Rate each finding

Copy this table and add one row per finding. Add more rows as needed.

| # | Signal | Severity | Was I aware of this? | Is this a real problem? | Will I fix it? | Surprise (1–5) |
|---|--------|----------|:--------------------:|:-----------------------:|:--------------:|:--------------:|
| 1 | <!-- e.g. PFS --> | <!-- e.g. HIGH --> | yes / no | yes / no / unsure | yes / no | <!-- 1–5 --> |
| 2 | | | | | | |
| 3 | | | | | | |

**Surprise scale:**
1 = "Knew this exactly" · 2 = "Vaguely aware" · 3 = "Had a diffuse feeling" · 4 = "Had no idea" · 5 = "Would have expected the opposite"

### Step 3 — Most surprising finding

**Which finding surprised you most?**

<!-- Paste the finding's reason text and explain why it surprised you. -->

### Step 4 — Actionability (optional, for S13)

For up to 10 findings, rate drift's `next_action` text:

| # | Signal | Understandable (1–5) | Actionable (1–5) | Prioritizable (1–5) |
|---|--------|:--------------------:|:-----------------:|:-------------------:|
| 1 | | | | |
| 2 | | | | |

**Actionability scale:**
1 = "Don't understand / can't act" · 3 = "Somewhat clear" · 5 = "Immediately clear and actionable"

### Step 5 — 30-day follow-up (we'll ask later)

We will follow up after 30 days to check which findings were actually fixed.
No action needed now.

---

**Privacy:** You do not need to share your repo URL or any proprietary code.
Finding descriptions and ratings are sufficient.
