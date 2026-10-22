# Design Tokens

Paste into the global stylesheet (e.g. the unscoped `<style>` in `App.vue`). Defaults are slate + blue; remap to the project's documented palette if there is one.

```css
:root {
  /* Spacing scale (4px base) */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;
  --space-7: 3rem;

  /* Color: neutrals */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-border-strong: #cbd5e1;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-text-subtle: #94a3b8;

  /* Color: brand + status */
  --color-primary: #2563eb;
  --color-primary-soft: #eff6ff;
  --color-success: #059669;
  --color-success-soft: #d1fae5;
  --color-warning: #d97706;
  --color-warning-soft: #fed7aa;
  --color-danger: #dc2626;
  --color-danger-soft: #fecaca;

  /* Sidebar */
  --sidebar-width: 240px;
  --sidebar-width-collapsed: 72px;
  --sidebar-bg: #0f172a;
  --sidebar-text: #94a3b8;
  --sidebar-text-active: #ffffff;
  --sidebar-item-hover: rgba(255, 255, 255, 0.06);
  --sidebar-item-active: rgba(255, 255, 255, 0.12);

  /* Shape */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* Elevation */
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);
  --shadow-lg: 0 12px 32px rgba(15, 23, 42, 0.16);

  /* Type */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 0.938rem;
  --text-lg: 1.125rem;
  --text-xl: 1.5rem;
  --text-2xl: 1.875rem;

  /* Motion */
  --transition: 0.15s ease;
}
```

Light sidebar variant: set `--sidebar-bg: #ffffff`, `--sidebar-text: #64748b`, `--sidebar-text-active: var(--color-primary)`, hover `#f1f5f9`, active `var(--color-primary-soft)`, and add a right border.

Rules:
- Padding/margin/gap use `--space-*` only.
- Cards use `--radius-lg` + `--shadow-sm`; buttons and inputs `--radius-md`; badges `--radius-sm`.
- Contrast: body text on surface must be at least 4.5:1.
