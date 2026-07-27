# Torchlight Documentation

The documentation structure:

- [Architecture](architecture.md)
- [Memory System Deep Dive](memory-system.md)
- [Hardening Checklist](hardening-checklist.md)
- [Excellence Roadmap](excellence-roadmap.md)

## How To Use These Docs

Read [Architecture](architecture.md) to understand how the system is put together today.

Read [Hardening Checklist](hardening-checklist.md) when the goal is validation, stabilization, or closing correctness gaps.

Read [Excellence Roadmap](excellence-roadmap.md) when the goal is pushing Torchlight toward stronger local-agent behavior over time.

## Recommended Reading Order For A New Contributor

1. [Architecture](architecture.md)
2. [README.md](../../README.md)
3. [Hardening Checklist](hardening-checklist.md)
4. [Excellence Roadmap](excellence-roadmap.md)

## Coverage

These three docs are meant to cover:

- what Torchlight is and why it exists
- how the repo is organized
- how a request flows through the system
- where to start when changing a specific area
- what is currently risky
- what should be improved next

## Recent Runtime Progress

The current docs reflect several runtime improvements that are already implemented:

- deterministic execution-policy routing
- explicit working-set construction
- explicit provider and active-model truth
- failure-classified retry handling
- stronger stop and cancel control
- better visibility in Activity and Context surfaces
