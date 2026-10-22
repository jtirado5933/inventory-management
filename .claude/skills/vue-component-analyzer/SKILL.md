---
name: vue-component-analyzer
description: Analyze Vue 3 component structure and report prioritized performance, correctness and code-reuse findings (oversized components, duplicated markup, CSS or logic, unregistered components, dead bindings and CSS, missing v-for keys, heavy computed/watch use, refetch and filter-handling problems). Report only, never edits code. Use when asked to review, audit, profile or optimize Vue components or a view, find duplication or refactoring candidates, or diagnose why a view feels slow, even if the user does not say "analyze". Do not use for backend/API work, non-Vue frontends, or applying a redesign.
---

# Vue Component Analyzer

Read a Vue 3 codebase and produce a prioritized report of structural, correctness and performance problems with concrete fixes. This skill only reports. Edits are a separate step the user must ask for, and in this repo `.vue` changes go to `vue-expert` (see CLAUDE.md).

References (read as needed):
- `references/checks.md` - what to look for, why it matters, and the fix for each check
- `scripts/scan_vue.py` - deterministic scan; run it first so findings start from facts

## Workflow

### 1. Scope
Decide the scope from the request and keep to it. Reading beyond it is only for confirming a finding.
- **Whole app** ("audit the components"): every `.vue` under `client/src/`.
- **One file or view**: report on that file. Read what it imports only to confirm duplication, prop contracts, or a fetch path, and do not audit those files.
- **Folder or pattern** (`*Modal.vue`, `components/`): those files, plus whatever outside them is needed to confirm duplication.
- **A question** ("why is X slow when I change filters?"): use diagnostic mode below.

Read the root CLAUDE.md for conventions that change what counts as a problem (this repo: options-style `setup()`, singleton `useFilters`, custom SVG charts, i18n keys in both locales). Where the root CLAUDE.md and the code disagree with `client/CLAUDE.md` or `server/CLAUDE.md`, the root file and the code win; those two are generic best-practice guides.

### 2. Scan
Run from the repo root. The scope goes first; `--compare` adds files used only for cross-file duplication checks, so a narrow scope still sees the rest of the app.

```bash
# whole app
python .claude/skills/vue-component-analyzer/scripts/scan_vue.py client/src
# one file, compared against the app
python .claude/skills/vue-component-analyzer/scripts/scan_vue.py client/src/views/Dashboard.vue --compare client/src
# a pattern (quote it so the script expands it)
python .claude/skills/vue-component-analyzer/scripts/scan_vue.py "client/src/components/*Modal.vue"
```

It reports, with line numbers: unregistered components and unresolved imports, bindings returned from `setup()` that the template never uses, CSS classes nothing references, `v-for` key problems, empty watchers, composables called inside functions, a fetch map (what runs on mount and on each watcher, and which shared filters a view reads), helpers called many times per render, hardcoded strings in i18n files, and duplicated template runs, CSS rules, CSS drift and function bodies across files.

Treat every line as a lead. The scan is regex-based: dynamically built class names, `<component :is>` and unusual formatting cause false positives. Read the code at each reported line before it goes in the report.

### 3. Read and judge
Read the files the scan points at, then work through `references/checks.md` for the areas the request is about. Do not cover areas the request does not ask for. A reuse-only request does not need a performance pass.

Verify before reporting:
- Duplicates: the scan prints identical and drifted copies. Open one drifted pair to confirm the difference is real and unintended.
- Cost: check data size in `server/data/*.json` before calling something expensive. Mock data is small, so for an optimization audit rank by what scales and say so. When the user asks why something is slow today and nothing measurable is, say that plainly and look for perceived slowness (controls that do nothing, remounts, transitions).
- Bugs you find outside the checks (wrong constants, stale state, missing files) belong in the report. Correctness outranks performance and reuse.

#### Diagnostic mode
For "why is X slow" or "why does Y not update" questions, answer the question before auditing:
1. Name the user action and what it mutates (for filters: which shared refs).
2. List every `watch`, `computed` and `onMounted` that reads it. The scan's fetch map gives the fetch triggers.
3. List the API calls those trigger, and whether the endpoint even supports the filter (CLAUDE.md lists which do).
4. List the template regions that re-render, and whether a loading flag unmounts the whole view.
If the premise is wrong (no fetch happens, the control is ignored), say so first. It is usually the finding.

### 4. Report
Cite `file:line` for every finding. Use this structure and drop any section that has nothing to say:

```
# Vue component analysis: <scope>
Files read: <list or count>

## Answer            (diagnostic questions only: the direct answer and causal chain)

## Summary
<3-5 lines: overall health, the one or two changes to do first>

## Findings
### [High|Medium|Low] <short title>
- Where: path:line (and other occurrences)
- Problem: what is wrong and why it matters
- Fix: the specific change (name the component/composable to extract, the API to use)
- Effort: S (under an hour, one file) / M (a few files or a new shared component) / L (cross-cutting or needs a decision)

## Reuse candidates   (cross-file patterns only; omit for a single-file audit)
<table: duplicated pattern | files:lines | proposed shared component or composable>

## Not worth changing
<rejected scan leads and suspicious-looking code that is fine, each with a reason>

## Not measured       (when render cost was inferred from code, not profiled; say what to measure)
```

Ranking:
- **High**: bugs and correctness (unregistered component, wrong constants, ignored filters, stale state), index or missing `v-for` keys, work that scales badly, and duplication that has already drifted.
- **Medium**: clear maintainability or reuse wins, duplication that is identical but not yet drifted.
- **Low**: polish.

If you noticed something outside the requested areas, put it in one line under Summary ("Also noticed: ...") rather than a full finding.

## Do not
- Edit files, install tools, or add dependencies.
- Recommend a rewrite to a different style (e.g. `<script setup>`) unless it directly enables a finding.
- Pad the report with generic best practices that nothing in this codebase violates.
