# Architecture

NextSet is a modular Python application with one portable Windows entry point. Application code belongs to the `nextset` package; tests, reviewed knowledge, documentation and packaging tools have their own directories. There are no duplicate root modules or wildcard database compatibility shims.

```text
launcher.py              Stable entry point for START.cmd and PyInstaller
nextset/
  __main__.py            python -m nextset
  launcher.py            Setup and application lifecycle
  core/                  Exercise identities, shared constants, parsing and load arithmetic
  knowledge/             Reviewed catalogue access; no Telegram/model dependency
  coaching/              Profile, training state, blocks, feedback and background jobs
  ai/                    Evidence retrieval, Ollama protocol, extraction, setup and evaluation
  storage/               Canonical SQLite implementation and consistent backups
  telegram/              Telegram handlers, guided UI, method browser and update routing
  visuals/               Actual-progress charts and planned training calendars
  platform/              Portable paths and Windows HTTPS compatibility
knowledge/               Reviewed JSON content, shipped as application resources
tests/                   Unit, integration, routing, packaging and boundary checks
scripts/                 Release scanner and Windows package builder
docs/                    English usage, architecture and evidence documentation
```

The Telegram runtime composes the application and enforces pairing and private-chat access. Presentation handlers translate messages and button actions into coaching or diary operations. Coaching coordinates validation, stored state and AI proposals. The model proposes structured data; application guards validate it before storage. A plan is distinct from actual diary records and never becomes completed merely by approval.

Shared exercise identities and arithmetic have no Telegram or model dependency. `knowledge.catalog` reads reviewed method metadata without loading the bot or an inference backend. Only the selected compact reference enters the model context. Displaying method cards and saved plans requires no inference.

All database callers import `nextset.storage.database`, giving one canonical module and connection configuration. Portable paths are resolved centrally in `platform.paths`; changing the working directory cannot redirect knowledge resources. Existing databases retain their schema and settings, so this refactor requires no data migration. Runtime files remain in `data/`; they never enter a release or Git history.

Telegram updates remain ordered for diary consistency. Long coaching requests run as application-managed asynchronous tasks with one inference slot. They capture proposed state instead of writing it immediately. Completion checks current profile, training state, diary, recent measurements and date before committing. Cancellation discards results; the inference slot remains occupied until the finite HTTP request returns. Request status and saved answers survive restart; an unfinished job becomes interrupted. Telegram delivery failures cannot roll back or mislabel a successfully saved answer.

This is a pragmatic modular application, not a microservice system. Coaching currently contains a command adapter and some Telegram prompt helpers; the AI coaching service coordinates block validation as well as backend calls. Keep these integration points explicit. Extract smaller services when new behavior needs them; avoid introducing a generic plugin framework or a second state model prematurely.

## Extending it

- **Method:** add a reviewed entry to `knowledge/programs.json`; preserve old IDs. See [METHODS.md](METHODS.md).
- **Exercise:** add its identity/movement to `core/exercises.py`; review schemas, substitution constraints and tests. An exercise ID is not a workout prescription.
- **Research source:** add a bilingual reviewed evidence card with population, limitations and primary URL. Chat messages cannot modify evidence.
- **Telegram action:** add presentation routing in `telegram/`, reuse coaching/storage operations, and test the conversation path. Do not run long inference directly in a serial handler.
- **Training rule:** put shared validation or arithmetic in `core/`; state transitions and approvals belong in `coaching/`. Test actual behavior, including stale data and failure cases.
- **Persistence:** change the canonical storage module and add a backward-compatible schema migration if required. Test existing database behavior and backups.
- **Visual:** add a renderer in `visuals/`; distinguish planned dates from measured outcomes and test/export with synthetic data.

## Validation and packaging

From the repository root, run `python -m unittest discover -s tests -p "test_*.py" -v`, `python launcher.py --check` and `python scripts/check_release.py`. Tests do not require Ollama or live Telegram access. Boundary tests reject old ambiguous imports and check that core/catalogue access remains independent of Telegram. Packaging builds from the thin root launcher and bundles `knowledge/` and Windows HTTPS resources. Both `python launcher.py` and `python -m nextset` use the same implementation.
