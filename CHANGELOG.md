# Changelog

All notable changes to `tiny-cli-progress` are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-09-25

### Added

- **First public release.** ~250 LOC, zero dependencies, stdlib only.
- `progress(iterable, ...)` — wrap an iterable with a progress bar.
- `ProgressBar(total, ...)` — manual progress bar with `.update(n)`, `.set_description(desc)`, `.close()`. Context manager.
- `Spinner(message, ...)` — context manager that renders a Braille-dot spinner (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`). Auto-degrades to `<message>...` in non-TTY environments.
- `MultiBar(file, min_interval, force)` — concurrent named bars (e.g. parallel downloads). Each `mb.add(desc, total)` returns a `ProgressBar`.
- `is_tty()` — terminal capability detection.
- **`force=True`** flag — write progress output even when stdout isn't a TTY (useful for tests, log files, CI artifacts).
- **Auto-disable in non-TTY**: bars silently degrade so CI logs and redirected output stay clean.
- **GitHub Actions CI** — Python 3.9 → 3.13.
- **`llms.txt`** manifest for agent-native discovery.
- 28 tests covering bar mechanics (advance, clamp, total=0 rejection, idempotent close, disable, context manager), progress helper (yields all items, advance, custom total, exception cleanup), spinner (no crash, message on exit), multi-bar (concurrent updates, idempotent close), TTY detection, formatting (ETA, rate), performance (10k updates < 2s), and a real-world agent tool-call invocation pattern.
