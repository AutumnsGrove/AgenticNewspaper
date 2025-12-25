# GroveEngine Reference Patterns

> Source: https://github.com/AutumnsGrove/GroveEngine
> Purpose: Core UI engine and multi-tenant blog framework for Grove ecosystem

---

## What to Clone For

When you need to reference GroveEngine patterns:

```bash
git clone https://github.com/AutumnsGrove/GroveEngine /tmp/groveengine-ref
```

---

## Key Patterns for Newspaper Project

### 1. Markdown Rendering Components

**Location**: `packages/engine/src/lib/components/`

The engine has markdown parsing and rendering components that could be adapted for newspaper digest display:
- ContentWithGutter - sidebar annotation system
- MarkdownEditor - full-featured editor with live preview

**Useful for**: Rendering the generated newspaper digests in Svelte

### 2. Multi-Tenant Architecture

**Location**: `docs/multi-tenant-architecture.md`

Pattern: Single deployment serving all users via subdomain routing
- Request flow: `*.grove.place` → extract subdomain → D1 tenant lookup
- Data isolation: All queries scoped by `tenant_id`

**Useful for**: Per-user newspaper customization and data isolation

### 3. Theming System (Foliage)

**Location**: `packages/engine/src/lib/ui/`

Built on Tailwind CSS presets with design tokens for colors, spacing, typography.

**Useful for**: Newspaper theme customization (light/dark, typography choices)

### 4. Component Hierarchy Pattern

```
Lattice (Business Logic) → GroveUI (Generic Components) → Site-Specific Code
```

**Useful for**: Separating newspaper logic from UI components

### 5. Authentication (Heartwood Integration)

**Location**: `docs/groveauth-handoff.md`, `packages/engine/src/lib/auth/`

- OAuth 2.0 with PKCE flow
- JWT token validation
- Session management on `.grove.place` domain

**Useful for**: User authentication for the newspaper SaaS

---

## Naming Conventions to Follow

| Element | Convention | Example |
|---------|------------|---------|
| Directories | CamelCase | `VideoProcessor`, `DataAnalysis` |
| Date paths | kebab-case + ISO | `logs-2025-01-15` |
| Functions | camelCase | `calculateTotalPrice()` |
| Types/Interfaces | PascalCase | `ArticleMetadata` |
| Constants | SCREAMING_SNAKE | `MAX_ARTICLES` |
| Products | Single evocative word | Ivy, Amber, Clearing |

---

## Files to Read First

1. `/docs/grove-naming.md` - Ecosystem naming philosophy
2. `/docs/multi-tenant-architecture.md` - Architecture patterns
3. `/docs/belongs-in-engine.md` - What goes where
4. `/packages/engine/src/lib/components/` - UI component examples

---

## Code Style Highlights

- Svelte 5 with runes (`$state`, `$derived`, `$effect`)
- TypeScript required
- Tailwind CSS (utility-first)
- Conventional commits (`feat:`, `fix:`, `docs:`)
- No strict linting enforced; write readable code

---

## Cleanup After Reference

```bash
rm -rf /tmp/groveengine-ref
```
