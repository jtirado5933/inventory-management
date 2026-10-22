# Checks

Each check: what to look for, why it matters, the fix. "Scan" notes say whether `scan_vue.py` already surfaces it; read the code either way.

## Contents
- Correctness
- Structure and reuse
- Reactivity and performance
- Fetching and filters
- Repo conventions

## Correctness (outranks everything else)

**Unregistered or missing component** (scan)
- Look for a tag in the template that is not imported, registered, or global, or an import path that does not exist.
- Why: Vue renders an unknown element and logs a warning; buttons that open it do nothing.
- Fix: create the component or remove the usage and its dead state.

**Dead bindings and dead CSS** (scan)
- Look for values returned from `setup()` that the template never reads, and CSS classes with no matching markup. Large dead blocks make a file look oversized and hide its real structure.
- Fix: delete. Check dynamically built class names (`'badge-' + status`) before deleting.

**Wrong or stale values**
- Hand-copied constants that disagree with the geometry they describe (SVG circumference vs radius), an error ref that is never reset after a successful reload, static demo numbers presented as live KPIs, dates used without validity checks.

**Composable called inside a function** (scan)
- `useX()` inside a handler or helper runs per call and may fall outside setup context. Call once at setup top level.

## Structure and reuse

**Oversized component**
- Look at the template: more than about 250 lines, or several unrelated sections. If the file is mostly `<style>`, the problem is CSS (dead or duplicated), not component split; the scan says so. The root CLAUDE.md and the code win over the generic ">100 lines" advice in `client/CLAUDE.md`.
- Fix: extract section components with explicit props/emits; extract chart SVG into its own component.

**Duplicated markup** (scan: template runs)
- Same card, table, badge or modal shell in several files. Fix: a shared component with slots. Confirm the copies are equivalent first.

**Duplicated CSS and CSS drift** (scan)
- Identical scoped rules copied across components are usually the largest duplication in a codebase like this one. Drift (same selector, different `z-index`, shadow, spacing, transition timing) is a visible inconsistency and can be a stacking bug.
- Fix: one shared component owns the shell styles, or move shared rules to the global stylesheet.

**Duplicated logic** (scan: identical bodies and same-name-different-body)
- Same formatting, filtering or aggregation in several files; repeated fetch + loading + error handling. Look for an existing util first (`utils/currency.js`, `useI18n`) before proposing a new one. Near-identical copies with different bodies are drift: one of them is usually wrong (a `formatDate` hardcoded to `en-US` beside locale-aware copies).
- Note `useFilters` is a deliberate module-level singleton; do not suggest per-component copies.

**Prop drilling and event chains**
- A prop passed through components that do not use it, or an emit re-emitted unchanged. Fix: a composable, or `provide/inject`.

**Component API**
- Parents mutating a prop object, `v-model` handled by hand, modals that fetch data the parent already has.

## Reactivity and performance

**Missing or index `v-for` keys** (scan)
- Wrong DOM reuse and stale row state. Use a stable id (`sku`, `month`, `id`).

**Helpers called many times per render** (scan)
- A method called dozens of times in the template that rebuilds a lookup table or parses dates on each call. Fix: a computed map keyed by value, rebuilt only when its inputs change.

**Heavy work in templates and O(n*m) computeds**
- `.filter/.map/.reduce/.sort` in the template; `find()` inside a loop over orders in a computed. Fix: computed, or a `Map` index built once.

**Watchers that should be computed; computed that should not be**
- `watch` that only derives a value into another ref; a computed that just returns a ref or is never read (scan flags empty watchers and unused returns).

**Deep reactivity on large data**
- Large API arrays in `ref` that are only replaced, never mutated, and `deep: true` watchers. Fix: `shallowRef`, or watch a specific key. Do not recommend it when code mutates items in place.

**In-place `sort`/`reverse` on reactive state** (scan prints the receiver)
- Mutates the source and can retrigger itself. Copy first. A fresh array (`Object.values(x)`, `[...a]`) is safe.

**Children that do not depend on the changed state still re-render**
- Charts or tables inside a big template re-render on every filter change. Fix: extract them and pass props so Vue skips them when props are unchanged.

**`v-if` vs `v-show`; large lists; eager loading**
- `v-show` for frequently toggled content, `v-if` for rarely shown content such as modals. Pagination or windowing for lists the API can grow. `() => import()` for routes and `defineAsyncComponent` for rarely opened modals, ranked low at small sizes.

**CSS cost**
- `transition: all` animating layout properties; long width transitions that read as lag.

**Lifecycle leaks** (scan)
- Listeners, intervals or observers without `onUnmounted` cleanup.

## Fetching and filters

Use the scan's fetch map as the starting point.

**Filter coverage**
- Which of the shared filters does this view read, and does its endpoint support them (CLAUDE.md lists which)? A control that does nothing reads as "slow" or broken. Fix: pass `getCurrentFilters()` to the call and refetch, or hide the filters on that route.

**Refetch vs client-side filtering**
- Decide which side filters. Refetching data an endpoint does not filter (backlog, inventory by month) is waste; filtering a full list client-side that the API could filter is the opposite.

**Loading-flag remount** (scan)
- A `v-if="loading"` around the whole view, toggled on every refetch, destroys and rebuilds the DOM. Fix: show loading only on first load or as an overlay, and refetch only what changed.

**Races and stale state**
- Two quick filter changes can resolve out of order. Fix: a request counter or cancellation, and debounce if needed. Reset error state at the start of each load.

**Repeated fetching**
- Several components calling the same endpoint on mount. Fix: fetch once in a composable.

## Repo conventions

**Hardcoded strings** (scan)
- This repo needs i18n keys in both `en.js` and `ja.js`. Strings typed into templates of files that already use i18n are drift. A modal that is partly translated is the usual shape.

**Currency and dates**
- Currency follows locale via `utils/currency.js`; swapping only the symbol without converting the amount is a bug. Dates should respect the current locale.
