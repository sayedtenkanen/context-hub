# Python Migration Plan

## Goals

- Provide a Python CLI with feature parity to the current Node.js `chub` CLI.
- Preserve command behavior, flags, and output formats (human + --json).
- Ship an MCP server in Python with matching tool surface.
- Keep bundled content support (registry + docs) for offline-first usage.

## Scope

- CLI commands: search, get, annotate, feedback, update, cache, build.
- Core libraries: registry merge/search, BM25 index, cache, config, frontmatter parsing, output formatting, annotations, telemetry + analytics, identity.
- MCP server: search, get, list, annotate, feedback tools + registry resource.
- Packaging: console entrypoints `pychub` and `pychub-mcp`.

## Source-of-Truth References

- CLI entry + command wiring: cli/src/index.js
- Commands: cli/src/commands/
- Core libs: cli/src/lib/
- MCP server: cli/src/mcp/
- CLI behavior: docs/cli-reference.md

## Python Package Layout (actual: src/pychub)

✅ **Completed:**

- pyproject.toml (uv + hatchling, Python 3.11+)
- src/pychub/**init**.py
- src/pychub/cli.py (typer scaffold with --version)
- src/pychub/commands/ (package dir)
- src/pychub/lib/ (package dir)
- src/pychub/mcp/server.py (stub entrypoint)
- **Phase 1 Core Libs:**
  - config.py (load ~/.chub/config.yaml, multi-source support) ✅
  - cache.py (fetch registries, bundle support, file caching) ✅
  - registry.py (merge sources, search, entry resolution) ✅
  - bm25.py (tokenize, build index, search) ✅
  - output.py (JSON mode, human formatting with Rich) ✅
  - annotations.py (read/write/clear/list local annotations) ✅
  - frontmatter.py (parse YAML frontmatter) ✅
  - normalize.py (language aliases) ✅
  - identity.py (machine ID, agent detection) ✅
- **Phase 2 Commands (partial):**
  - update.py (registry refresh, full bundle) ✅
  - cache.py (status, clear) ✅
  - search.py (fuzzy search, exact id, filters) ✅
  - annotate.py (read/write/clear/list) ✅
  - CLI wiring in cli.py ✅

🚧 **In Progress (Phase 2):**

- get.py (auto-detect doc vs skill, language/version handling, output modes)
- feedback.py (telemetry, labels, agent detection)
- build.py (discover DOC.md/SKILL.md, validate frontmatter, generate indexes)

## Immediate Next Sprint (Execution Order)

1. Implement `get.py` and register in `src/pychub/cli.py`.
2. Implement `telemetry.py` and `feedback.py` together (shared dependencies: client id + env/config gating).
3. Implement `build.py` with frontmatter validation + `registry.json` and `search-index.json` generation.
4. Run smoke checks:

- `pychub update`
- `pychub search stripe`
- `pychub annotate stripe/api "test"`

5. Add pytest coverage for `bm25.py`, `registry.py`, and `cache.py` first, then command-level tests.

⏳ **Pending:**

- Libs: telemetry.py, analytics.py (optional for Phase 2)
- MCP: tools.py, full server implementation

## Dependency Mapping (Node -> Python)

- commander -> typer (or click)
- chalk -> rich
- yaml -> PyYAML
- zod -> pydantic
- fetch -> httpx
- tar -> tarfile
- posthog-node -> posthog (python)

## Parity Checklist by Command

### search

- List all entries when query is omitted.
- Exact id match returns entry detail.
- Fuzzy search uses BM25 index when available, otherwise keyword fallback.
- Filters: tags, lang, limit.
- Supports --json output.

### get

- Auto-detect doc vs skill.
- Supports --lang, --version, --full, --file, -o/--output.
- Writes files to output dir or file.
- Includes annotation and additionalFiles in output (human + json).

### annotate

- List, read, write, and clear annotations.
- Persist annotations under ~/.chub/annotations.

### feedback

- Telemetry gated by config and env.
- Auto-detect doc vs skill when possible.
- Supports labels, lang, version, file, agent, model, status.

### update

- Refresh registry cache; supports --force and --full.
- Respect cache freshness logic.

### cache

- status and clear.
- Preserve config.yaml when clearing cache.

### build

- Validate DOC.md/SKILL.md frontmatter.
- Auto-discover entries, build registry.json and search-index.json.
- Copy content tree to output dir.

## Bundled Content Support

- Include built dist/ data in package.
- On startup, seed local cache from bundled registry.json if no cache exists.
- Allow remote refresh to override bundled content.

## Migration Phases

**Phase 0: Scaffold** ✅ COMPLETE

- pyproject.toml with uv
- Package structure: src/pychub
- CLI entrypoints: pychub, pychub-mcp
- Decisions: Python 3.11+, ship parallel to Node CLI

**Phase 1: Core libs parity** ✅ COMPLETE

- config.py (load ~/.chub/config.yaml, multi-source support) ✅
- cache.py (fetch registries, bundle support, file caching) ✅
- registry.py (merge sources, search, entry resolution) ✅
- bm25.py (tokenize, build index, search) ✅
- output.py (JSON mode, human formatting with Rich) ✅
- annotations.py (read/write/clear/list local annotations) ✅
- frontmatter.py (parse YAML frontmatter) ✅
- normalize.py (language aliases) ✅
- identity.py (machine ID, agent detection) ✅

**Phase 2: CLI commands parity** 🚧 IN PROGRESS

- ✅ update (refresh registry cache, --force, --full)
- ✅ cache (status, clear)
- ✅ search (fuzzy search, exact id, filters)
- ✅ annotate (list, read, write, clear)
- ⏳ get (fetch docs/skills, --lang, --version, --full, --file, -o)
- ⏳ feedback (send ratings with labels)
- ⏳ build (validate, build registry + search index)

**Definition of Done for Phase 2**

- All seven commands wired into `src/pychub/cli.py`.
- Human output + `--json` parity validated against existing Node behavior.
- Error handling parity for: missing IDs, ambiguous IDs, missing language, and invalid versions.

**Phase 3: MCP server parity** ⏳ PENDING

- tools.py, full server.py with SDK

**Phase 4: Packaging, bundled content, entrypoints** ⏳ PENDING

**Phase 5: Regression tests and performance checks** ⏳ PENDING

## Risks and Gaps

- Cross-platform path handling for cache and output.
- MCP SDK parity between JS and Python.
- Telemetry and analytics behavior matching.
- Large content bundle size in Python wheel.

## Decisions Made

- ✅ Python minimum version: **3.11+**
- ✅ Package name: **pychub** (entrypoints: pychub, pychub-mcp)
- ✅ Layout: **src/pychub** (uv-friendly)
- ✅ Ship: **Parallel** to Node CLI initially
- ⏳ Telemetry default: TBD (likely match Node: opt-out)
