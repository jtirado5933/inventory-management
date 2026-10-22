# Restyle Checklist

Apply to shared/global classes. Names below are typical; map to whatever the project uses.

| Element | Treatment |
|---|---|
| Page header (`.page-header`) | `h2` at `--text-2xl`, weight 700, letter-spacing -0.025em; subtitle `--color-text-muted`; `margin-bottom: var(--space-5)` |
| Card (`.card`) | surface bg, `1px solid var(--color-border)`, `--radius-lg`, `--shadow-sm`, padding `--space-5`; header with bottom border and `--space-4` gap |
| Stat card | same as card; label `--text-xs` uppercase muted; value `--text-xl`+ weight 700; hover raises to `--shadow-md` and `--color-border-strong` |
| Grid gaps | `--space-4` or `--space-5`, never mixed within one page |
| Table | `thead` bg `--color-bg`; `th` `--text-xs` uppercase muted; cell padding `--space-3 var(--space-4)`; row hover `--color-bg`; wrapper `overflow-x: auto` |
| Badge | `--radius-sm`, `--text-xs`, weight 600; soft bg + dark text from status tokens |
| Button | primary: `--color-primary` bg, white text; secondary: surface bg + border; height ~36px; `--radius-md`; hover darkens; disabled 0.5 opacity |
| Input / select | height ~36px, `--radius-md`, border `--color-border`; focus: border `--color-primary` + `0 0 0 3px` primary at 15% alpha |
| Modal | overlay `rgba(15,23,42,0.5)`; panel `--radius-lg`, `--shadow-lg`, padding `--space-5`; z-index above sidebar (sidebar 100, topbar 50, modal 1000) |
| Loading / error | centered muted text; error uses `--color-danger-soft` bg with `--radius-md` |
| Focus | global `:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }` |

## Sweep commands
- Hardcoded colors: grep `#[0-9a-fA-F]{3,6}` in `src/**/*.vue` and `App.vue`; convert shared ones to tokens, leave data-viz colors alone.
- Top-bar coupling: grep `top: *[0-9]+px`, `100vh`, `position: sticky`.
- Off-scale spacing: grep odd values like `0.313rem`, `0.625rem`; snap to the scale when in shared styles.

## Keep
- Status color semantics (green/blue/yellow/red).
- Chart SVG internals and any project-specific design-system rules.
