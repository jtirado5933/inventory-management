# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Factory Inventory Management System Demo with GitHub integration - Full-stack application with Vue 3 frontend, Python FastAPI backend, and in-memory mock data (no database).

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

## Critical Tool Usage Rules

### Subagents
Use the Task tool with these specialized subagents for appropriate tasks:

- **vue-expert**: Use for Vue 3 frontend features, UI components, styling, and client-side functionality
  - Examples: Creating components, fixing reactivity issues, performance optimization, complex state management
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: Use after writing significant code to review quality and best practices
- **Explore**: Use for understanding codebase structure, searching for patterns, or answering questions about how components work
- **general-purpose**: Use for complex multi-step tasks or when other agents don't fit

### Skills
- **backend-api-test** skill: Use when writing or modifying tests in `tests/backend` directory with pytest and FastAPI TestClient

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: Local branches only - use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing
  - Test against: `http://localhost:3000` (frontend), `http://localhost:8001` (API)

## Stack
- **Frontend**: Vue 3 + Composition API + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: JSON files in `server/data/` loaded via `server/mock_data.py`

## Quick Start

```bash
# Backend
cd server
uv run python main.py

# Frontend
cd client
npm install && npm run dev
```

## Commands

```bash
./scripts/start.sh | ./scripts/stop.sh        # Both servers (also /start, /stop skills)
cd client && npm run build                    # Production build (no lint/test tooling in client)

# Backend tests - run from server/ (that's where the uv env with pytest lives)
cd server && uv run pytest ../tests/backend -c ../tests/pytest.ini -q
cd server && uv run pytest ../tests/backend/test_inventory.py::TestInventoryEndpoints::test_get_all_inventory -c ../tests/pytest.ini
```

`cd tests && uv run pytest` (as written in `tests/README.md` and `server/CLAUDE.md`) fails with "pytest not found" because `tests/` has no pyproject. There are no frontend tests or linters; the `/test` command's lint/type steps have nothing to run.

## Architecture

- **Backend** is two files: `server/mock_data.py` loads every `server/data/*.json` into module-level lists at import time; `server/main.py` holds all Pydantic models, the shared `filter_by_month`/`apply_filters` helpers, and every route. Data is never persisted, so restart to reload JSON. `server/generate_data.py` regenerates the JSON.
- `month` filter accepts `2025-01` style or quarters (`Q1-2025`, mapped via `QUARTER_MAP`) and matches against `order_date`, so it only applies to orders/dashboard.
- **Frontend** uses `vue-router` (routes defined in `client/src/main.js`; there is no `router/` dir) with options-style `setup()` components in `views/` (one per route) and `components/` (modals, FilterBar).
- **Filters are a singleton**: `composables/useFilters.js` holds module-level refs shared by every view; `getCurrentFilters()` maps Time Period to the API's `month` param. `client/src/api.js` skips params equal to `'all'`, and the base URL `http://localhost:8001/api` is hardcoded there.
- **i18n**: `composables/useI18n.js` with `locales/en.js` and `ja.js` (locale persisted in localStorage, falls back to English). Currency follows locale (en -> USD, ja -> JPY, see `utils/currency.js`). New UI strings need keys in both locale files.
- `composables/useAuth.js` is a mock user (language-aware); there is no real auth.
- `client/CLAUDE.md` and `server/CLAUDE.md` are generic Vue/FastAPI best-practice guides, not repo-specific; trust the code over them (e.g. their suggested module layouts do not exist).

## Key Patterns

**Filter System**: 4 filters (Time Period, Warehouse, Category, Order Status) apply to all data via query params
**Data Flow**: Vue filters → `client/src/api.js` → FastAPI → In-memory filtering → Pydantic validation → Computed properties
**Reactivity**: Raw data in refs (`allOrders`, `inventoryItems`), derived data in computed properties

## API Endpoints
- `GET /api/inventory` - Filters: warehouse, category
- `GET /api/orders` - Filters: warehouse, category, status, month
- `GET /api/dashboard/summary` - All filters
- `GET /api/demand`, `/api/backlog` - No filters
- `GET /api/spending/*` - Summary, monthly, categories, transactions

## Common Issues
1. Use unique keys in v-for (not `index`) - use `sku`, `month`, etc.
2. Validate dates before `.getMonth()` calls
3. Update Pydantic models when changing JSON data structure
4. Inventory filters don't support month (no time dimension)
5. Revenue goals: $800K/month single, $9.6M YTD all months

## File Locations
- Views: `client/src/views/*.vue`
- API Client: `client/src/api.js`
- Backend: `server/main.py`, `server/mock_data.py`
- Data: `server/data/*.json`
- Styles: `client/src/App.vue`

## Design System
- Colors: Slate/gray (#0f172a, #64748b, #e2e8f0)
- Status: green/blue/yellow/red
- Charts: Custom SVG, CSS Grid for layouts
- No emojis in UI
