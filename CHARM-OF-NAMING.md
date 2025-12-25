# The Charm of Naming

> A philosophy document for the AgenticNewspaper project

---

## Why Multiple Spec Versions?

In this project, we keep multiple versions of specification documents rather than updating a single file. This is intentional.

### The Pattern

```
docs/
├── intelligent-news-aggregator-spec-orig.md   # v1 - Original brain dump
├── intelligent-news-aggregator-spec-v2.md     # v2 - Refined after architecture decisions
├── v3-spec-hybrid-architecture.md             # v3 - Cloudflare + Python hybrid
└── ...future versions
```

### Why Not Just Update One File?

1. **Archaeology**: Each spec captures a moment in time—the thinking, constraints, and context that led to decisions. Future readers (including future-you) can trace the evolution of ideas.

2. **Charm**: There's something satisfying about seeing `v1`, `v2`, `v3` lined up. It tells a story. It has personality.

3. **Safety**: Bold pivots feel less scary when the old spec still exists. You're not destroying; you're building on top.

4. **Clarity**: When specs diverge significantly (like Python-only → Cloudflare hybrid), a new file makes the break clean. No awkward strikethroughs or "DEPRECATED" headers cluttering the document.

5. **Reference**: Sometimes you need to remember "why did we stop doing X?" The old spec has the answer.

---

## When to Create a New Version

Create a new spec version when:

- The **architecture fundamentally changes** (new stack, new patterns)
- The **scope significantly expands or contracts**
- You're returning to a project after a long hiatus with fresh perspective
- The existing spec would require more than 40% rewriting

Don't create a new version for:

- Minor clarifications or typo fixes
- Adding detail to existing sections
- Bug fixes or small feature additions

---

## Naming Convention

```
{feature-or-project}-spec-{version-or-qualifier}.md
```

Examples:
- `news-aggregator-spec-v2.md`
- `news-aggregator-spec-cloudflare.md`
- `export-system-spec-streaming.md`

The qualifier can be a version number (`v1`, `v2`) or a descriptive word (`streaming`, `hybrid`, `minimal`).

---

## The Moment This Document Captures

**Date**: December 25, 2025

After months away from this project, we returned to find:
- Two existing specs (original + v2)
- A half-implemented Python agent system with mocks
- A desire to pivot toward Cloudflare Workers + Svelte

Rather than gut the existing specs, we're creating v3 to capture this new direction. The old specs remain as artifacts of the original vision—useful for understanding decisions, extracting still-valid ideas, and appreciating how far the thinking has come.

This document exists because someone asked: "why the hell are there 2 specs??" and the answer was charming enough to preserve.

---

## Related Philosophy

See also:
- Grove ecosystem naming conventions (`grove-naming.md` in GroveEngine)
- The principle of "edit existing files, don't create new ones" (AGENT.md) — specs are an exception
- Commit message archaeology (conventional commits preserve intent)

---

*This file itself is an artifact. It captures a moment of reflection on how we work.*
