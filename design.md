# VERIQ Design System & UI/UX Architecture
**Tagline: Code is generated. Proof is earned.**
**Design System Reference: [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md)**

VERIQ implements an executive-grade developer workbench adhering to the **design-system** specification and the **Impeccable** craft floor.

## System Tenets
1. **Consistency Over Creativity**: Every button, card, status badge, input, and modal conforms strictly to standardized atomic design tokens defined in `DESIGN_SYSTEM.md`.
2. **Zero Layout Overlap**: Grids and flex containers enforce strict bounds with `min-height: 0`, `overflow-y: auto`, and responsive breakpoints to guarantee that no card or timeline ever bleeds over into another container.
3. **Deterministic Visual Proof**: Clear visual separation between AI reasoning (Nebius cascade) and deterministic proof (Docker sandbox, AST checks, pytest executions).
4. **IDE-Grade Developer Ergonomics**: Gutter line numbers in diffs, 1-click copy for evidence hashes and patches, intuitive keyboard shortcuts (`G O`, `G N`, `G W`, `G L`, `G H`, `G B`, `G S`), and high-contrast WCAG AA accessible contrast.

## Mode Alignments
- **Operate Mode (Primary)**: The Active Run Workbench and Task Builder prioritize information density, rapid scanning, and precision telemetry without distraction.
- **Persuade Mode (Overview & Benchmarks)**: High-impact hero banner, verified claims counter, and interactive benchmarks demonstrating why the VERIQ cascade out-performs single-model baselines.
- **Read Mode (Ledger & Reports)**: Cryptographic evidence transparency with copyable SHA-256 digests and deep terminal stdout/stderr inspectability.
