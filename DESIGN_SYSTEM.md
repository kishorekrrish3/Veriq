# VERIQ Design System Specification (v5.0)
**Tagline: Code is generated. Proof is earned.**
**Mission: Evidence-Driven Autonomous Engineering Agent**

---

## 1. Design System Summary & Audit

- **System Name**: VERIQ Obsidian & Electric Cyan Design System
- **Aesthetic**: Deep Space Obsidian, Precision Hairlines, High-Vibrancy Deterministic Indicators, IDE-Grade Developer Ergonomics
- **Target Modes**: 
  - **Operate**: Maximum scanability, high information density without clutter, zero-bleed layouts, instant keyboard shortcuts.
  - **Persuade**: Executive proof metrics, baseline vs. cascade comparisons, deterministic evidence receipts.
  - **Read**: Audit-grade cryptographic verification ledger, traceable stdout/stderr inspectability.

---

## 2. Design Tokens

### 2.1 Color Tokens

```css
:root {
  /* Canvas & Surface Scale */
  --canvas-deep: #05070B;            /* Deepest void backdrop */
  --canvas-base: #080C14;            /* App content canvas */
  --surface-sidebar: #0B101A;        /* Navigation drawer & sidebar */
  --surface-card: #0F1624;           /* Primary interactive cards & containers */
  --surface-card-hover: #151E30;     /* Hover surface for interactive elements */
  --surface-floating: #192338;       /* Popovers, dropdowns, and modals */
  --surface-terminal: #04060A;       /* Code blocks, diff viewer, terminal consoles */

  /* Hairline Borders */
  --border-hairline: rgba(255, 255, 255, 0.07);
  --border-subtle: rgba(255, 255, 255, 0.12);
  --border-strong: rgba(255, 255, 255, 0.22);
  --border-accent: rgba(0, 229, 255, 0.45);
  --border-accent-glow: 0 0 16px rgba(0, 229, 255, 0.35);

  /* Typography Colors (WCAG AA 4.5:1+ Compliant) */
  --text-primary: #F8FAFC;          /* Highest contrast headers and values */
  --text-secondary: #CBD5E1;        /* Standard body copy and descriptions */
  --text-muted: #94A3B8;            /* Meta items, breadcrumbs, hints */
  --text-dim: #64748B;              /* Disabled and placeholder text */

  /* Brand & Acceleration Accents */
  --brand-cyan: #00E5FF;             /* Primary electric cyan brand accent */
  --brand-cyan-hover: #38BDF8;
  --brand-cyan-dim: rgba(0, 229, 255, 0.10);
  --brand-violet: #8B5CF6;           /* Nemotron routing & AI orchestration */
  --brand-violet-dim: rgba(139, 92, 246, 0.12);

  /* Deterministic Status Tokens */
  --status-verified: #10B981;        /* Proven, tests pass, syntax valid */
  --status-verified-text: #34D399;
  --status-verified-bg: rgba(16, 185, 129, 0.12);
  --status-verified-border: rgba(16, 185, 129, 0.35);

  --status-supported: #38BDF8;       /* Research grounded, context supported */
  --status-supported-text: #7DD3FC;
  --status-supported-bg: rgba(56, 189, 248, 0.12);
  --status-supported-border: rgba(56, 189, 248, 0.35);

  --status-failed: #F43F5E;          /* Test failure, assertion error */
  --status-failed-text: #FB7185;
  --status-failed-bg: rgba(244, 63, 94, 0.14);
  --status-failed-border: rgba(244, 63, 94, 0.40);

  --status-unresolved: #F59E0B;      /* Non-deterministic, needs human review */
  --status-unresolved-text: #FBBF24;
  --status-unresolved-bg: rgba(245, 158, 11, 0.14);
  --status-unresolved-border: rgba(245, 158, 11, 0.40);

  --status-not-run: #64748B;         /* Pending execution in pipeline */
  --status-not-run-text: #94A3B8;
  --status-not-run-bg: rgba(100, 116, 139, 0.12);
  --status-not-run-border: rgba(100, 116, 139, 0.25);
}
```

### 2.2 Typography Scale

- **Display Header**: `font-size: 32px`, `font-weight: 800`, `line-height: 1.15`, `letter-spacing: -0.03em`
- **Section Title**: `font-size: 22px`, `font-weight: 700`, `line-height: 1.25`, `letter-spacing: -0.02em`
- **Card Title**: `font-size: 16px`, `font-weight: 600`, `line-height: 1.35`, `letter-spacing: -0.01em`
- **Body Large**: `font-size: 14.5px`, `font-weight: 400`, `line-height: 1.55`
- **Body Small**: `font-size: 13px`, `font-weight: 400`, `line-height: 1.5`
- **Code & Mono**: `font-family: 'JetBrains Mono', monospace`, `font-size: 12.5px`, `line-height: 1.6`
- **Micro Tag**: `font-size: 11px`, `font-weight: 600`, `text-transform: uppercase`, `letter-spacing: 0.05em`

### 2.3 Spacing Scale & Border Radii

- **Spacing**: `4px`, `8px`, `12px`, `16px`, `20px`, `24px`, `32px`, `48px`
- **Radius**:
  - `radius-xs`: `4px` (micro badges, code tags)
  - `radius-sm`: `6px` (buttons, inputs, status pills)
  - `radius-md`: `10px` (cards, timeline containers, diff boxes)
  - `radius-lg`: `16px` (modal surfaces, hero banner)
  - `radius-pill`: `9999px` (capsule tags)

### 2.4 Shadows & Elevation

- `shadow-sm`: `0 2px 4px rgba(0, 0, 0, 0.4)`
- `shadow-md`: `0 6px 20px -2px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.06)`
- `shadow-lg`: `0 16px 40px -4px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.1)`
- `shadow-cyan-glow`: `0 0 24px -2px rgba(0, 229, 255, 0.28)`

---

## 3. Core Components

### 3.1 Button (`.btn`)
- **Variants**:
  - `.btn-primary`: Electric cyan background, `#05070B` bold text, soft cyan drop shadow.
  - `.btn-outline`: Transparent surface, `border: 1px solid var(--border-subtle)`, hover `border-color: var(--brand-cyan)`.
  - `.btn-ghost`: Borderless, background highlight on hover.
  - `.btn-danger`: Border and background in rose tint.
- **Sizes**: `.btn-sm` (32px height), `.btn-md` (40px height), `.btn-lg` (48px height).
- **States**: `default`, `:hover` (lift & glow), `:active` (scale 0.98), `:focus-visible` (electric cyan 2px outline), `:disabled` (opacity 0.45).

### 3.2 Status Badge (`.status-badge`)
- Capsule shape with pulsating status dot.
- Explicit semantic variants: `.status-verified`, `.status-supported`, `.status-failed`, `.status-unresolved`, `.status-not-run`.

### 3.3 Diff Viewer (`.diff-viewer`)
- Terminal background (`#04060A`) with sticky header containing file name, additions `+`, deletions `-`, and copy patch action.
- Line number gutter (`.diff-gutter`) displaying relative source line numbers.
- `.diff-line-add`: Green highlight (`rgba(16, 185, 129, 0.12)`) and emerald border.
- `.diff-line-del`: Red highlight (`rgba(244, 63, 94, 0.12)`) and rose border.
- `.diff-line-hunk`: Cyan highlight (`rgba(0, 229, 255, 0.08)`) and cyan line.

### 3.4 Verification Claim Card (`.claim-card`)
- Expandable accordion card.
- Header: Claim ID (e.g., `CLAIM-001`), descriptive title, check type tag, and deterministic status pill.
- Expanded Content: Explicit limitations, execution evidence records, command string, exit code, execution duration, and formatted stdout/stderr console box with copyable SHA-256 evidence hash.

### 3.5 Timeline Stream (`.timeline-stream`)
- Continuous vertical progress rail connecting chronological pipeline events.
- Pulsating status node for live events.
- Monospace timestamp + event type badge (`MODEL_SELECTED`, `PATCH_GENERATED`, `TESTS_EXECUTED`, etc.).

---

## 4. Anti-Patterns & Quality Floor

- ❌ **No Overlapping Grids**: Never set fixed parent grid heights while child card contents can grow arbitrarily. Always use `min-height: 0`, `overflow-y: auto`, and flex containment.
- ❌ **No Raw Hex Values in Components**: All color values must reference `:root` tokens.
- ❌ **No Emoji Icons**: All icons must be scalable, clean SVGs.
- ❌ **No Broken Focus Outlines**: All interactive elements must maintain high-contrast `:focus-visible` outlines.
- ❌ **No Layout Shifts**: Reserve fixed metric card heights and skeleton states.
