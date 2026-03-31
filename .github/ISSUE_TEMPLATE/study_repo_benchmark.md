---
name: "Community Study: Repo Benchmark"
about: "Analyze a repository for a community study"
title: "[Study] Repo Benchmark: "
labels: ["community-study", "benchmark"]
assignees: []
---

## Study: Repo Benchmark

Thank you for participating! Time required depends on the study (1–3 hours).

### Which study are you contributing to?

<!-- Check one: -->

- [ ] **S1 — Security-Erosion:** MAZ findings in AI-attributed vs. manual endpoints
- [ ] **S3 — Auth-Coverage × Score:** Authorization coverage correlation with drift score
- [ ] **S4 — Score after contributor change:** Score delta around team transitions
- [ ] **S6 — DIA as Day-2 indicator:** Documentation drift vs. maintenance stagnation
- [ ] **S9 — Framework erosion profiles:** Signal dominance by framework
- [ ] **S11 — Score-Debt correlation:** Drift score vs. tech-debt issue count
- [ ] **S12 — DCA in AI-heavy repos:** Dead code accumulation comparison

### Repository information

**Repo URL:** <!-- public GitHub URL -->

**Framework:** <!-- e.g. Django, Flask, FastAPI, Express, NestJS -->

**Language:** Python / TypeScript / JavaScript

**Approximate LOC:** <!-- e.g. 25,000 -->

**Active contributors (last 12 months):** <!-- number -->

### Drift analysis

**Drift version used:** <!-- e.g. 1.2.0 -->

**Command run:**

```bash
drift analyze --repo <path> --format json --since 90
```

**Composite drift score:** <!-- e.g. 0.442 -->

**Please attach the JSON output** as a file or paste it in a code block below.

<details>
<summary>JSON output (click to expand)</summary>

```json

```
</details>

### Study-specific measurements

<!-- Fill in the section matching your study. Delete the others. -->

#### S1 — Security-Erosion

| Metric | Value |
|--------|-------|
| Total endpoints | |
| AI-attributed endpoints | |
| Manual endpoints | |
| MAZ findings (AI endpoints) | |
| MAZ findings (manual endpoints) | |
| HSC findings total | |
| Attribution method used | <!-- commit message / .github config / other --> |

#### S3 — Auth-Coverage × Score

| Metric | Value |
|--------|-------|
| Total endpoints | |
| Endpoints with auth mechanism | |
| Auth-coverage rate | <!-- endpoints_with_auth / total --> |
| MAZ findings | |

#### S4 — Score after contributor change

| Checkpoint | Commit hash | Date | Composite score |
|:----------:|-------------|------|:---------------:|
| t−30 | | | |
| t−15 | | | |
| t₀ (transition) | | | |
| t+15 | | | |
| t+30 | | | |
| t+60 | | | |
| t+90 | | | |

**Transition description:** <!-- Who left? Who joined? Was there a major release nearby? -->

#### S6 — DIA as Day-2 indicator

| Metric | Value |
|--------|-------|
| DIA signal score | |
| Days since last docs commit | |
| Total LOC | |
| Docs-to-code commit ratio (last 6 months) | |

#### S9 — Framework erosion profiles

| Signal | Raw score | % of composite |
|--------|:---------:|:--------------:|
| PFS | | |
| AVS | | |
| MDS | | |
| EDS | | |
| TVS | | |
| SMS | | |
| DIA | | |
| COD | | |
| CCC | | |

#### S11 — Score-Debt correlation

| Metric | Value |
|--------|-------|
| Composite drift score | |
| Total LOC | |
| Tech-debt issues (labels: tech-debt, refactoring, cleanup, etc.) | |
| Tech-debt issues per 10k LOC | |

#### S12 — DCA in AI-heavy repos

| Metric | Value |
|--------|-------|
| DCA findings | |
| Total LOC (kLOC) | |
| DCA findings per kLOC | |
| Estimated AI-attributed commit % | |
| Matched pair repo (if applicable) | |

---

**Privacy:** Only public repositories should be analyzed for community studies.
