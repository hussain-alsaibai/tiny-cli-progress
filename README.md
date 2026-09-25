# tiny-cli-progress

> Zero-dependency progress bars and spinners for Python CLIs.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-28%20passing-success.svg)](#testing)

~250 LOC. ANSI escape codes. **Stdlib only.** Like `tqdm`, but in one file
and zero deps. Auto-detects non-TTY (CI logs, file output) and silences
the bar — or force-enable with `force=True`.

```python
from tiny_cli_progress import progress, Spinner

for item in progress(items, desc="Processing"):
    process(item)

with Spinner("Connecting..."):
    connect()
```

## Install

```bash
pip install tiny-cli-progress
```

## Quick start

### Wrap an iterable

```python
from tiny_cli_progress import progress

for x in progress(range(1000), desc="Loading"):
    do_something(x)
```

Output:
```
Loading: ██████████░░░░░░░░░░░░░░░░░░ 423/1000 [ 42.3%] 4.2k/s eta 01:09
```

### Manual bar

```python
from tiny_cli_progress import ProgressBar

bar = ProgressBar(total=1000, desc="Downloading", unit="B")
for chunk in stream:
    bar.update(len(chunk))
bar.close()
```

### Spinner for indeterminate work

```python
from tiny_cli_progress import Spinner

with Spinner("Waiting for response..."):
    response = await slow_api_call()
```

### Multiple bars in parallel

```python
from tiny_cli_progress import MultiBar

with MultiBar() as mb:
    bar1 = mb.add("file-1.bin", total=1000)
    bar2 = mb.add("file-2.bin", total=500)
    # ... update each from a thread ...
```

## API

### `progress(iterable, total=None, *, desc='', unit='it', disable=False, file=sys.stdout, min_interval=0.05, width=30, colour='green', force=False)`

Wrap an iterable. Yields each item after advancing the bar.

- `force=True` — write progress output even when stdout isn't a TTY (tests, log files).

### `ProgressBar(total, *, desc='', unit='it', width=30, file=sys.stdout, min_interval=0.05, colour='green', disable=False, force=False)`

Manual progress bar.

- `update(n=1)` — advance.
- `set_description(desc)` — change the prefix.
- `close()` — finalize (also writes newline).
- Context manager (`with ProgressBar(...) as bar:`).
- `force=True` — write to non-TTY streams.

### `Spinner(message='', *, file=sys.stdout, interval=0.08)`

Context manager that shows a Braille-dot spinner (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`).

- In non-TTY: just writes `<message>...` and exits (so CI logs read correctly).
- `message=""` is a no-op.

### `MultiBar(file=sys.stdout, min_interval=0.05, force=False)`

Concurrent named bars (e.g. parallel downloads). Each `mb.add(desc, total)` returns a `ProgressBar`. `mb.close()` finalizes all bars.

### `is_tty()`

Returns `True` if stdout is a terminal.

## Behaviour in non-TTY environments

- Auto-detected: `progress()` and `ProgressBar` write nothing when stdout
  isn't a TTY. CI logs, redirected output, and `subprocess.run(capture_output=True)`
  stay clean.
- Force-enable with `force=True` if you want progress output in a log file.
- Spinner degrades to a single `<message>...` line — safe in CI.

## Why?

`tqdm` is great but pulls in `colorama` on Windows and is ~3,000 LOC for what
should be a 200-line library. `tiny-cli-progress` is the smallest reliable
progress bar + spinner for the tiny-* ecosystem.

## Sister libraries (OpenClaw tiny-* ecosystem)

- `tiny-cli-table` — beautiful tables for CLI output
- `tiny-cli` — argument parsing + agent output modes
- `tiny-log` — structured logging with secret masking
- `tiny-secret-mask` — redact secrets before logging

## License

MIT — see [LICENSE](LICENSE)
