"""
tiny_cli_progress — stdlib-only progress bars and spinners for Python CLIs.

Provides:
    - `progress(iterable, total=None, ...)` — wrap an iterable with a bar
    - `ProgressBar(total, ...)` — manually advance a bar
    - `Spinner(message, ...)` — indeterminate activity indicator
    - `MultiBar(...)` — run several named bars concurrently (e.g. downloads)

Zero deps. ANSI escape codes for terminal output. Non-TTY environments
(no `sys.stdout.isatty()`) automatically fall back to plain periodic
prints so log files and CI pipelines stay readable.

Inspired by `tqdm` but ~250 LOC instead of ~3,000. Designed for the tiny-*
ecosystem where every byte matters.

Example:
    from tiny_cli_progress import progress, Spinner

    for item in progress(items, total=len(items), desc="Processing"):
        process(item)

    with Spinner("Connecting..."):
        connect()
"""

from __future__ import annotations

import os
import sys
import threading
import time
from contextlib import contextmanager
from typing import Iterable, Iterator, Optional, Sequence


__version__ = "0.1.0"
__all__ = [
    "ProgressBar",
    "progress",
    "Spinner",
    "MultiBar",
    "is_tty",
]


# ── Terminal capability detection ────────────────────────────────────────────


def is_tty() -> bool:
    """True if stdout is a terminal (not a pipe / file / CI log)."""
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


# ── ANSI helpers ─────────────────────────────────────────────────────────────


_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_GREEN = "\x1b[32m"
_CYAN = "\x1b[36m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"


def _carriage_return() -> str:
    return "\r"


def _clear_line() -> str:
    return "\r\x1b[2K"


def _hide_cursor() -> str:
    return "\x1b[?25l"


def _show_cursor() -> str:
    return "\x1b[?25h"


# ── Byte / time formatting ───────────────────────────────────────────────────


def _format_eta(seconds: Optional[float]) -> str:
    if seconds is None or seconds == float("inf") or seconds < 0:
        return "--:--"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _human_rate(n: float) -> str:
    """Format a rate (items/sec) as a short human-readable string."""
    if n <= 0:
        return "?/s"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M/s"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k/s"
    return f"{n:.1f}/s"


# ── ProgressBar ──────────────────────────────────────────────────────────────


class ProgressBar:
    """A single progress bar.

    Args:
        total: Total number of steps. Required.
        desc: Optional description prefix (e.g. "Downloading").
        unit: Unit suffix (e.g. "it", "B"). Default: "it".
        width: Bar width in characters. Default: 30.
        file: Output stream. Default: ``sys.stdout``.
        min_interval: Minimum seconds between redraws. Default: 0.05 (20 Hz).
        colour: ANSI colour name for the filled portion. Default: "green".
        disable: If True, print nothing (useful when ``verbose=False``).
        force: If True, write to the stream even when it isn't a TTY.
            Useful for tests or for piping progress output to a log file.
    """

    def __init__(
        self,
        total: int,
        *,
        desc: str = "",
        unit: str = "it",
        width: int = 30,
        file=sys.stdout,
        min_interval: float = 0.05,
        colour: str = "green",
        disable: bool = False,
        force: bool = False,
    ) -> None:
        if total <= 0:
            raise ValueError(f"total must be > 0, got {total}")
        self.total = total
        self.desc = desc
        self.unit = unit
        self.width = width
        self.file = file
        self.min_interval = min_interval
        self.colour = _RESET if not is_tty() else {
            "green": _GREEN,
            "cyan": _CYAN,
            "yellow": _YELLOW,
            "red": _RED,
            "none": "",
        }.get(colour, _GREEN)
        self.disable = disable or (not is_tty() and not force)
        self.force = force
        self.n = 0
        self._start = time.monotonic()
        self._last_redraw = 0.0
        self._closed = False

    def update(self, n: int = 1) -> None:
        """Advance the bar by ``n`` steps."""
        if self.disable or self._closed:
            return
        self.n = min(self.n + n, self.total)
        now = time.monotonic()
        if now - self._last_redraw < self.min_interval and self.n < self.total:
            return
        self._last_redraw = now
        self._render()

    def set_description(self, desc: str) -> None:
        self.desc = desc
        self._render()

    def _render(self) -> None:
        pct = self.n / self.total
        filled = int(pct * self.width)
        bar = "█" * filled + "░" * (self.width - filled)
        elapsed = time.monotonic() - self._start
        if self.n > 0:
            rate = self.n / elapsed
            eta = (self.total - self.n) / rate if rate > 0 else None
            rate_str = _human_rate(rate)
        else:
            eta = None
            rate_str = "?/s"
        prefix = f"{self.desc}: " if self.desc else ""
        line = (
            f"{_clear_line()}{prefix}"
            f"{self.colour}{bar}{_RESET} "
            f"{self.n}/{self.total} "
            f"[{pct * 100:5.1f}%] "
            f"{rate_str} "
            f"eta {_format_eta(eta)}"
        )
        self.file.write(line)
        self.file.flush()

    def close(self) -> None:
        if self._closed or self.disable:
            self._closed = True
            return
        self._render()
        self.file.write("\n")
        self.file.flush()
        self._closed = True

    def __enter__(self) -> "ProgressBar":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def progress(
    iterable: Iterable,
    total: Optional[int] = None,
    *,
    desc: str = "",
    unit: str = "it",
    disable: bool = False,
    file=sys.stdout,
    min_interval: float = 0.05,
    width: int = 30,
    colour: str = "green",
    force: bool = False,
) -> Iterator:
    """Wrap an iterable with a progress bar.

    Example:
        for x in progress(items, desc="Processing"):
            process(x)
    """
    if total is None:
        try:
            total = len(iterable)  # type: ignore[arg-type]
        except TypeError:
            total = 0
    bar = ProgressBar(
        total=total or 1,
        desc=desc,
        unit=unit,
        disable=disable,
        file=file,
        min_interval=min_interval,
        width=width,
        colour=colour,
        force=force,
    )
    try:
        for item in iterable:
            yield item
            bar.update(1)
    finally:
        bar.close()


# ── Spinner ───────────────────────────────────────────────────────────────────


_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


@contextmanager
def Spinner(message: str = "", *, file=sys.stdout, interval: float = 0.08):
    """Indeterminate activity indicator (a spinner).

    Example:
        with Spinner("Connecting..."):
            connect()
    """
    if not is_tty() or not message:
        if message:
            file.write(f"{message}...\n")
            file.flush()
        yield
        return
    stop = threading.Event()
    tty = file

    def spin() -> None:
        i = 0
        while not stop.is_set():
            frame = _SPINNER_FRAMES[i % len(_SPINNER_FRAMES)]
            tty.write(f"{_clear_line()}{frame} {message}")
            tty.flush()
            i += 1
            stop.wait(interval)

    t = threading.Thread(target=spin, daemon=True)
    t.start()
    try:
        file.write(_hide_cursor())
        file.flush()
        yield
    finally:
        stop.set()
        t.join(timeout=1.0)
        file.write(_clear_line())
        file.write(f"{_GREEN}✓{_RESET} {message}\n")
        file.write(_show_cursor())
        file.flush()


# ── MultiBar ─────────────────────────────────────────────────────────────────


class MultiBar:
    """Run several named progress bars concurrently (e.g. parallel downloads).

    Example:
        mb = MultiBar()
        bar1 = mb.add("file-1.bin", total=1000)
        bar2 = mb.add("file-2.bin", total=500)
        # ... update each from a thread ...
        mb.close()
    """

    def __init__(self, file=sys.stdout, min_interval: float = 0.05, force: bool = False) -> None:
        self.file = file
        self.min_interval = min_interval
        self.force = force
        self._bars: list[ProgressBar] = []
        self._lock = threading.Lock()
        self._stopped = False
        self._tty = is_tty() or force
        if self._tty:
            self.file.write(_hide_cursor())
            self.file.flush()

    def add(self, desc: str, total: int, **kwargs) -> ProgressBar:
        # Propagate force=True to each bar so non-TTY tests work.
        if self.force and "force" not in kwargs:
            kwargs["force"] = True
        bar = ProgressBar(
            total=total, desc=desc, file=self.file, min_interval=self.min_interval,
            **kwargs,
        )
        with self._lock:
            self._bars.append(bar)
        return bar

    def render(self) -> None:
        """Redraw all bars at their current state."""
        if not self._tty:
            return
        with self._lock:
            # Move cursor up to the first bar line.
            if len(self._bars) > 1:
                self.file.write(f"\x1b[{len(self._bars) - 1}A")
            for bar in self._bars:
                bar._render()
                self.file.write("\n")
            self.file.flush()

    def close(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        for bar in self._bars:
            bar.close()
        if self._tty:
            self.file.write(_show_cursor())
            self.file.flush()

    def __enter__(self) -> "MultiBar":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
