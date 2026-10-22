---
name: vue-saas-redesign
description: Redesign a Vue 3 (vue-router) application's UI into a modern SaaS-style interface with a vertical left sidebar instead of a top nav bar, design tokens, and spacing from a fixed scale. Use when asked to redesign the UI, replace the top nav with a sidebar, or give the app a SaaS dashboard look. Do not use for apps that already have a sidebar, non-Vue frontends, or backend-only or API-only work.
---

# Vue 3 SaaS Redesign

Convert a top-nav Vue 3 app to a sidebar layout. Change only the app shell, global tokens, and shared classes. Limit per-view scoped styles to light touch-ups.

## When not to use
- The app already uses a sidebar layout.
- The frontend is not Vue 3 with vue-router.
- The task is API, state, or data work with no UI change.

References (read as needed):
- `references/design-tokens.md` - `:root` variables to paste into the global stylesheet
- `references/sidebar-pattern.md` - layout, active state, collapse, mobile drawer, a11y
- `references/restyle-checklist.md` - mapping for cards, tables, badges, buttons, inputs, modals
- `assets/AppSidebar.vue.template` - starting point for the sidebar component

## Workflow

### 1. Discover (read-only)
- Find `main.js` / router config, root `App.vue`, and the top nav (`<header>` or `<nav>` containing `router-link`s).
- List every item living in the top bar (logo, links, language switcher, profile menu, search) and any toolbar/filter strip below it. Each must survive the move.
- Find the global style block and shared classes (`.card`, `.badge`, `table`, `.page-header`, `.stat-card`).
- Read the project CLAUDE.md for constraints: palette, "no emojis", i18n rules, mandatory subagents. These override this skill's defaults.

### 2. Tokens
- Add the variables from `references/design-tokens.md` to the global `:root`. If the project documents a palette, map its colors onto the token names instead of using the defaults.
- Replace hardcoded hex, px padding, radii, and shadows in shared classes with `var(--...)`.

### 3. Sidebar shell
- Create `components/AppSidebar.vue` from `assets/AppSidebar.vue.template`: brand at top, nav links, footer slot for language switcher and profile menu.
- Apply the two-column layout and sidebar width from `references/sidebar-pattern.md`. Move the toolbar/filter strip into the content column as a sticky bar.
- Keep every existing route, i18n key (`t('nav.*')`), prop, and emitted event. Relocate, do not rewrite behavior. Any hardcoded nav label should get an i18n key in every locale file.
- Icons: inline SVG or none. No emojis unless the project allows them.

### 4. Responsive and a11y
- Apply the mobile drawer, a11y, and optional collapsed-state rules from `references/sidebar-pattern.md`.

### 5. Restyle shared classes
Follow `references/restyle-checklist.md`. Rules: spacing only from the scale, one radius per component tier, one shadow level for cards, borders over heavy shadows, status colors keep their meaning.

### 6. Light per-view pass
- Grep views for layout coupled to the old top bar: sticky `top:` offsets (e.g. 70px), `100vh` heights, `max-width` wrappers, hardcoded outer padding.
- Fix only what breaks or visibly clashes. Do not restyle scoped styles wholesale.

### 7. Delegation
If the project's CLAUDE.md says `.vue` files must be created or significantly modified by a specific subagent (this repo: `vue-expert`), delegate steps 3-6 to it with the references paths in the prompt.

### 8. Verify
- Run the production build (`npm run build`).
- Start the app and screenshot at ~1440px and ~390px (Playwright MCP if available).
- Click every nav item: route changes, active state correct, no console errors.
- If the app has multiple locales, switch locale and check long labels do not overflow the sidebar.
- Confirm the diff contains no credentials, internal hostnames, or registry URLs.

## Do not
- Change API calls, state composables, or routing.
- Add UI libraries or new dependencies.
- Leave the old top nav markup or its dead CSS behind.
