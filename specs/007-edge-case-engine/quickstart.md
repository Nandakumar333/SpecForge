# Quickstart: Edge Case Analysis Engine

**Feature**: 007-edge-case-engine

## Prerequisites

- SpecForge installed (`uv tool install specforge`)
- Project initialized (`specforge init`)
- Architecture decomposed (`specforge decompose`) — manifest.json with services and communication map

## Quick Test

```bash
# Generate edge cases for a specific service
specforge edge-cases ledger-service

# Or use a feature number
specforge edge-cases 002
```

## Expected Output

For a microservice manifest with ledger-service depending on identity-service:

```
Analyzing edge cases for ledger-service...
Architecture: microservice (1 dependency, 1 event)
Generated 11 edge cases (2 critical, 4 high, 3 medium, 2 low)
Written to: .specforge/features/ledger-service/edge-cases.md
```

## Verify Output

```bash
# Check the generated file
cat .specforge/features/ledger-service/edge-cases.md

# Verify YAML frontmatter is parseable
python -c "
import re, yaml
text = open('.specforge/features/ledger-service/edge-cases.md').read()
blocks = re.findall(r'\`\`\`yaml\n(.*?)\n\`\`\`', text, re.DOTALL)
for b in blocks:
    data = yaml.safe_load(b)
    print(f'{data[\"id\"]}: {data[\"category\"]} ({data[\"severity\"]})')
"
```

## Architecture Modes

| Architecture | Categories Generated | Inter-Service Cases |
|-------------|---------------------|-------------------|
| microservice | Standard + Microservice | Yes — derived from communication[] |
| monolithic | Standard only | No |
| modular-monolith | Standard + Interface Contract | No |

## Integration with Pipeline

Edge cases are automatically generated as Phase 3b when running:

```bash
specforge specify ledger-service
```

Phase 3b runs in parallel with Phase 3a (data model).
