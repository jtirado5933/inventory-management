# Sidebar Pattern

## Layout skeleton

```vue
<div class="app-shell" :class="{ 'sidebar-open': sidebarOpen }">
  <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />
  <div class="app-content">
    <div class="app-topbar">
      <button class="menu-toggle" aria-label="Open navigation" @click="sidebarOpen = true">...</button>
      <!-- toolbar / filter strip moves here -->
    </div>
    <main class="main-content"><router-view /></main>
  </div>
</div>
```

```css
.app-shell { display: flex; min-height: 100vh; background: var(--color-bg); }
.app-content { flex: 1; min-width: 0; display: flex; flex-direction: column; margin-left: var(--sidebar-width); }
.app-topbar { position: sticky; top: 0; z-index: 50; background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.main-content { flex: 1; padding: var(--space-5) var(--space-6); max-width: 1600px; width: 100%; margin: 0 auto; }
.menu-toggle { display: none; }

@media (max-width: 900px) {
  .app-content { margin-left: 0; }
  .menu-toggle { display: inline-flex; }
  .main-content { padding: var(--space-4); }
}
```

`min-width: 0` on `.app-content` prevents wide tables from stretching the page.

## Sidebar rules
- `position: fixed; inset: 0 auto 0 0; width: var(--sidebar-width)`; flex column: brand, nav (flex 1, scrolls), footer.
- Nav item: `display: flex; gap: var(--space-3); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md)`. Active uses `router-link-exact-active` or `aria-current="page"` styling: stronger background plus full-contrast text. Use exact matching for `/`, otherwise it is active on every route.
- Group labels (optional): `--text-xs`, uppercase, `--color-text-subtle`.
- Footer holds the language switcher and profile menu. Child dropdowns that open downward must open upward or sideways here; check them.

## Mobile drawer (<= 900px)
- Sidebar gets `transform: translateX(-100%)`; `.open` removes it. Transition 0.2s.
- Backdrop `rgba(15,23,42,0.5)`, click closes.
- Close on Escape and on route change (`watch(() => route.path, close)`).
- Hamburger button needs `aria-label` and `aria-expanded`.

## Collapsed state (optional)
- Toggle width between `--sidebar-width` and `--sidebar-width-collapsed`; hide labels, keep icons, add `title` tooltips.
- Persist in `localStorage` inside try/catch; also update `.app-content` margin.

## A11y
- `<nav aria-label="Main">`, `aria-current="page"` on active link, visible `:focus-visible` outline, keyboard-reachable drawer, focus returns to the hamburger on close.
