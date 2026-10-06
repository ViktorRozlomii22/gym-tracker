# Build and release

## Layout

- `launcher.py`: first-run setup and portable app entry point.
- `runtime.py`: Telegram routing, pairing and polling.
- `handlers_*.py`: adapted upstream conversation and export modules.
- `database_sqlite.py`: local storage implementing the NextSet database interface.
- `diary.py`: history, quick entries, graphs and reminders.
- `local_ai.py`: optional validated localhost Ollama extraction.
- `paths.py`: separates persistent `data/` from bundled resources.
- `tests`: `test_nextset.py` and `test_packaging.py`.

## Test

Use Python 3.12 on Windows:

```powershell
python -m pip install -r requirements.lock
python -m unittest discover -p "test_*.py" -v
python launcher.py --check
python scripts/check_release.py
```

Tests use temporary databases and fake Telegram messages. They do not need a real token or send messages to people. Optional AI extraction is mocked; the real model must be separately installed and validated for your machine and inputs.

## Build the portable app

```powershell
python -m pip install -r requirements.lock -r requirements-build.txt
python scripts/build_windows.py
```

This creates `release/NextSet-UA-Windows.zip` and its SHA-256 file. The ZIP contains the executable, English quick-start guide, stop script, app license and third-party notices. No `data/`, credentials, logs or personal records are included. PyInstaller bundles Python and libraries; a target computer does not need Python. Builds are unsigned Windows x64 executables.

## GitHub releases

The CI workflow tests each push and pull request on Windows. Pushing a version tag such as `v1.0.0` runs the release workflow, builds and smoke-tests the executable, and uploads the ZIP/checksum to a GitHub Release. The workflow uses the repository's built-in `GITHUB_TOKEN`; no personal token belongs in the source tree.

The initial publication is split into commits for core application, portable launcher, and documentation/build checks. No co-author trailers are added.

## Dependencies and attribution

`requirements.txt` lists direct runtime dependencies; `requirements.lock` pins the tested resolved versions. `requirements-build.txt` pins build tools. Update and test these deliberately. Keep `LICENSE` in distributions. The build script collects available dependency license files and the Python license into the Windows archive.
