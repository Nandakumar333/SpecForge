# CLI Contract: specforge research

## Command Signature

```
specforge research <target>
```

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| target | string | yes | Service slug (e.g., "ledger-service") or feature number (e.g., "002") |

## Inputs

| Source | Required | Path |
|--------|----------|------|
| manifest.json | yes | `.specforge/manifest.json` |
| spec.md | yes | `.specforge/features/<slug>/spec.md` |
| plan.md | no | `.specforge/features/<slug>/plan.md` |
| research.md | no | `.specforge/features/<slug>/research.md` (for merge on re-run) |

## Outputs

| Artifact | Path | Action |
|----------|------|--------|
| research.md | `.specforge/features/<slug>/research.md` | Created or merged with existing |
| .pipeline-state.json | `.specforge/features/<slug>/.pipeline-state.json` | Research phase marked "complete" |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (research.md generated) |
| 1 | Error (missing manifest, missing spec, service not found) |

## Behavior

1. Resolves target to service slug via manifest.json
2. Validates spec.md exists
3. Checks `.pipeline-lock` — refuses if locked
4. Loads spec.md text (required) and plan.md text (optional)
5. Extracts NEEDS CLARIFICATION markers and tech references
6. Gets architecture-specific research topics from adapter
7. Optionally loads PromptContextBuilder for tech-stack-specific topics
8. Generates ResearchFinding objects with status
9. If existing research.md: merges findings (preserves RESOLVED, re-evaluates BLOCKED)
10. Renders research.md.j2 template
11. Writes research.md atomically
12. Updates .pipeline-state.json research phase to "complete"
13. Displays summary with status counts

## Terminal Output Examples

```
$ specforge research ledger-service

Researching technical unknowns for ledger-service...

Scanning spec.md... found 3 unknowns
Scanning plan.md... found 2 unknowns
Adding microservice-specific topics... 4 topics

Research complete: 9 findings
  RESOLVED:    5
  UNVERIFIED:  2
  BLOCKED:     1
  CONFLICTING: 1

Written to: .specforge/features/ledger-service/research.md
Pipeline state updated: research → complete
```

```
$ specforge research ledger-service  # re-run after spec update

Researching technical unknowns for ledger-service...

Merging with existing research.md (5 RESOLVED preserved)
Found 2 new unknowns

Research complete: 11 findings
  RESOLVED:    7
  UNVERIFIED:  2
  BLOCKED:     1
  CONFLICTING: 1

Written to: .specforge/features/ledger-service/research.md
```

## Research Finding Format (in research.md)

```markdown
### R-001: gRPC for Auth Validation

**Status**: RESOLVED
**Source**: embedded-knowledge
**Triggered by**: "gRPC for auth validation" (spec.md, line 42)

gRPC is well-suited for synchronous inter-service authentication.
Library: grpc (Python) / Grpc.AspNetCore (.NET).
Proto files should be co-located in a shared contracts/ directory.

---

### R-007: Database Choice for Ledger

**Status**: CONFLICTING
**Source**: spec-reference
**Triggered by**: "[NEEDS CLARIFICATION: database choice]" (spec.md, line 78)

**Alternative A**: PostgreSQL — best for ACID transactions, mature ecosystem
**Alternative B**: CockroachDB — distributed SQL, built-in horizontal scaling
**Alternative C**: MongoDB — flexible schema, good for event sourcing patterns

Recommendation: Requires human decision based on scale and consistency requirements.
```
