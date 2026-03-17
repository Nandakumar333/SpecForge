# CLI Contract: specforge clarify

## Command Signature

```
specforge clarify <target> [--report]
```

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| target | string | yes | Service slug (e.g., "ledger-service") or feature number (e.g., "002") |

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| --report | flag | false | Generate report file instead of interactive mode |

## Inputs

| Source | Required | Path |
|--------|----------|------|
| manifest.json | yes | `.specforge/manifest.json` |
| spec.md | yes | `.specforge/features/<slug>/spec.md` |

## Outputs

### Interactive Mode (default)

| Artifact | Path | Action |
|----------|------|--------|
| spec.md | `.specforge/features/<slug>/spec.md` | Appended with Clarifications section |

### Report Mode (--report)

| Artifact | Path | Action |
|----------|------|--------|
| clarifications-report.md | `.specforge/features/<slug>/clarifications-report.md` | Created/overwritten |
| spec.md | `.specforge/features/<slug>/spec.md` | NOT modified |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (questions answered or no ambiguities found) |
| 1 | Error (missing manifest, missing spec, service not found) |

## Behavior

1. Resolves target to service slug via manifest.json
2. Validates spec.md exists
3. Checks `.pipeline-lock` — refuses if locked
4. Scans spec.md for ambiguity patterns
5. Analyzes service boundaries via manifest
6. Checks for architecture remap → adds remap-specific questions
7. Generates ranked clarification questions
8. Interactive: presents questions with Rich prompts; records answers
9. Report: renders template to file
10. Displays summary of questions asked/answered/skipped

## Terminal Output Examples

```
$ specforge clarify ledger-service

Scanning ledger-service spec for ambiguities...
Found 4 ambiguities (2 domain, 1 service-boundary, 1 technical)

Q1 [service-boundary] (1/4)
Context: "Categories are used by both transactions and budgets"
Should category management live in ledger-service or planning-service?

  A) ledger-service — categories are primarily a transaction concern
  B) planning-service — categories are primarily a budgeting concern
  C) Shared library — extract to a shared package used by both
  D) Custom answer

Your choice: A

...

Clarification complete: 3 answered, 1 skipped
Updated: .specforge/features/ledger-service/spec.md
```

```
$ specforge clarify ledger-service --report

Scanning ledger-service spec for ambiguities...
Found 4 ambiguities (2 domain, 1 service-boundary, 1 technical)
Report written to: .specforge/features/ledger-service/clarifications-report.md
```

```
$ specforge clarify ledger-service

Scanning ledger-service spec for ambiguities...
No ambiguities detected.
```
