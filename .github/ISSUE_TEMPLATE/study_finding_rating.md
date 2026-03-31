---
name: "Community Study: Finding Rating"
about: "Rate drift findings for inter-rater validation"
title: "[Study] Finding Rating: "
labels: ["community-study", "finding-rating"]
assignees: []
---

## Study: Finding Rating (S7 / S8)

Thank you for participating! This takes about 30 minutes.

### Your background

**Years of software development experience:** <!-- e.g. 5 -->

**Primary language / framework:** <!-- e.g. Python / Django -->

**Have you used drift before?** yes / no

### Rating instructions

You will rate a set of findings. For each finding, you receive:
- The signal name and severity
- The `reason` text from drift
- 20 lines of source code context (±10 lines around the finding location)

**Do not look up the repository or read other reviewers' ratings.**

### Ratings

Copy this table and fill one row per finding.

| Finding ID | Signal | Rating | Category (if PFS) | Comment |
|:----------:|--------|:------:|:------------------:|---------|
| <!-- e.g. F-001 --> | <!-- e.g. PFS --> | TP / FP / Unclear | A / B / C / D / n/a | <!-- optional --> |
| | | | | |
| | | | | |

**Rating definitions:**
- **TP (True Positive):** This finding describes a real, unintentionally created architectural problem.
- **FP (False Positive):** This finding does not describe a real problem — either factually incorrect or architecturally intentional.
- **Unclear:** Cannot determine from the given context.

**Category definitions (only for PFS findings, study S8):**
- **A — Unintentional incoherence:** Pattern fragmentation without architectural justification.
- **B — Intentional variance:** Deliberate polymorphism, interface segregation, adapter/strategy pattern.
- **C — Migration transit:** Old and new pattern coexist during a planned transition.
- **D — Framework-imposed variance:** Different patterns required by the framework (e.g. class-based vs. function-based views).

### Calibration check

Before rating the study findings, please rate these 5 calibration findings
(provided separately). Your calibration ratings will not be included in the
study results but help ensure consistent understanding of the rating criteria.

**Calibration findings rated:** yes / no

---

**Privacy:** Finding contexts are from public open-source repositories only.
