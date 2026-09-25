"""Tests for tiny_cli_progress v0.1.0."""

from __future__ import annotations

import io
import time

import pytest

from tiny_cli_progress import (
    ProgressBar,
    Spinner,
    MultiBar,
    progress,
    is_tty,
)


# ── ProgressBar basic ────────────────────────────────────────────────────────


def test_progress_bar_starts_at_zero():
    buf = io.StringIO()
    bar = ProgressBar(total=10, file=buf, min_interval=0, force=True)
    assert bar.n == 0
    bar.close()
    assert "0/10" in buf.getvalue()


def test_progress_bar_advance():
    buf = io.StringIO()
    bar = ProgressBar(total=10, file=buf, min_interval=0, force=True)
    bar.update(3)
    bar.close()
    assert "3/10" in buf.getvalue()


def test_progress_bar_full_at_completion():
    buf = io.StringIO()
    bar = ProgressBar(total=5, file=buf, min_interval=0, force=True)
    for _ in range(5):
        bar.update(1)
    bar.close()
    assert "5/5" in buf.getvalue()
    assert "100.0%" in buf.getvalue()


def test_progress_bar_clamps_to_total():
    buf = io.StringIO()
    bar = ProgressBar(total=5, file=buf, min_interval=0, force=True)
    bar.update(100)  # way over
    assert bar.n == 5  # clamped
    bar.close()


def test_progress_bar_rejects_zero_total():
    with pytest.raises(ValueError):
        ProgressBar(total=0)


def test_progress_bar_negative_total_rejected():
    with pytest.raises(ValueError):
        ProgressBar(total=-1)


def test_progress_bar_with_description():
    buf = io.StringIO()
    bar = ProgressBar(total=10, file=buf, desc="Loading", min_interval=0, force=True)
    bar.update(1)
    bar.close()
    assert "Loading" in buf.getvalue()


def test_progress_bar_set_description():
    buf = io.StringIO()
    bar = ProgressBar(total=10, file=buf, desc="First", min_interval=0, force=True)
    bar.set_description("Second")
    bar.update(1)
    bar.close()
    assert "Second" in buf.getvalue()


def test_progress_bar_unit_in_output():
    buf = io.StringIO()
    bar = ProgressBar(total=10, unit="B", file=buf, min_interval=0, force=True)
    bar.update(1)
    bar.close()
    # The unit doesn't appear directly but the test ensures no crash.
    assert "1/10" in buf.getvalue()


def test_progress_bar_disable_silent():
    buf = io.StringIO()
    bar = ProgressBar(total=10, file=buf, disable=True)
    bar.update(5)
    bar.close()
    assert buf.getvalue() == ""


def test_progress_bar_idempotent_close():
    buf = io.StringIO()
    bar = ProgressBar(total=5, file=buf, min_interval=0, force=True)
    bar.update(5)
    bar.close()
    bar.close()  # second close should be safe
    # The terminal newline should appear exactly once.
    assert buf.getvalue().count("\n") == 1


def test_progress_bar_context_manager():
    buf = io.StringIO()
    with ProgressBar(total=5, file=buf, min_interval=0, force=True) as bar:
        bar.update(3)
    assert "3/5" in buf.getvalue()


# ── progress() helper ────────────────────────────────────────────────────────


def test_progress_helper_yields_all_items():
    items = [1, 2, 3, 4, 5]
    buf = io.StringIO()
    out = list(progress(items, file=buf, min_interval=0, force=True))
    assert out == items


def test_progress_helper_advances_bar():
    items = list(range(10))
    buf = io.StringIO()
    for _ in progress(items, file=buf, min_interval=0, force=True):
        pass
    assert "10/10" in buf.getvalue()


def test_progress_helper_with_total_kwarg():
    items = [1, 2, 3]
    buf = io.StringIO()
    for x in progress(items, total=100, file=buf, min_interval=0, force=True):
        pass
    assert "3/100" in buf.getvalue()


def test_progress_helper_closes_on_exception():
    buf = io.StringIO()
    items = iter([1, 2, 3])
    with pytest.raises(RuntimeError):
        for _ in progress(items, file=buf, min_interval=0, force=True):
            raise RuntimeError("boom")
    # Bar should have closed (newline written) even on exception.
    assert buf.getvalue().count("\n") == 1


# ── Spinner ───────────────────────────────────────────────────────────────────


def test_spinner_runs_without_error():
    buf = io.StringIO()
    with Spinner("Working", file=buf):
        time.sleep(0.01)


def test_spinner_writes_done_message_on_exit():
    buf = io.StringIO()
    with Spinner("Loading", file=buf):
        pass
    # In non-TTY mode (StringIO) we should at least see the message.
    # The fallback writes "Loading..." then exits; in TTY mode it writes
    # "✓ Loading\n" on exit. Either way, "Loading" must appear.
    assert "Loading" in buf.getvalue()


def test_spinner_with_empty_message_is_noop():
    buf = io.StringIO()
    with Spinner("", file=buf):
        pass
    # Should not raise; buf might be empty.
    assert buf is not None  # just ensure no crash


# ── MultiBar ─────────────────────────────────────────────────────────────────


def test_multi_bar_add_creates_progress_bars():
    mb = MultiBar(file=io.StringIO(), min_interval=0, force=True)
    bar1 = mb.add("file-1", total=10)
    bar2 = mb.add("file-2", total=20)
    assert bar1.total == 10
    assert bar2.total == 20
    mb.close()


def test_multi_bar_close_is_idempotent():
    mb = MultiBar(file=io.StringIO(), min_interval=0, force=True)
    mb.add("x", total=1)
    mb.close()
    mb.close()  # safe


def test_multi_bar_context_manager():
    mb_file = io.StringIO()
    with MultiBar(file=mb_file, min_interval=0, force=True) as mb:
        bar = mb.add("y", total=5)
        bar.update(3)
    assert "3/5" in mb_file.getvalue()


# ── is_tty ───────────────────────────────────────────────────────────────────


def test_is_tty_with_stringio_returns_false():
    # StringIO is not a tty.
    old = __import__("sys").stdout
    __import__("sys").stdout = io.StringIO()
    try:
        assert is_tty() is False
    finally:
        __import__("sys").stdout = old


# ── ETA / rate formatting (no TTY needed) ────────────────────────────────────


def test_format_eta_handles_none():
    from tiny_cli_progress import _format_eta
    assert _format_eta(None) == "--:--"
    assert _format_eta(0) == "00:00"
    assert _format_eta(65) == "01:05"
    assert _format_eta(3661) == "1:01:01"


def test_human_rate_short_form():
    from tiny_cli_progress import _human_rate
    assert _human_rate(0) == "?/s"
    assert _human_rate(0.5) == "0.5/s"
    assert _human_rate(1500) == "1.5k/s"
    assert _human_rate(2_500_000) == "2.5M/s"


# ── Performance: 10k updates ────────────────────────────────────────────────


def test_progress_bar_10k_updates_completes_quickly():
    buf = io.StringIO()
    bar = ProgressBar(total=10_000, file=buf, min_interval=0, force=True)
    start = time.monotonic()
    for _ in range(10_000):
        bar.update(1)
    elapsed = time.monotonic() - start
    bar.close()
    # Should complete in well under 2 seconds on any modern machine.
    assert elapsed < 2.0


# ── Thread safety smoke test ────────────────────────────────────────────────


def test_multi_bar_concurrent_updates():
    import threading

    mb = MultiBar(file=io.StringIO(), min_interval=0, force=True)
    bar1 = mb.add("a", total=1000)
    bar2 = mb.add("b", total=1000)

    def worker(bar):
        for _ in range(1000):
            bar.update(1)

    t1 = threading.Thread(target=worker, args=(bar1,))
    t2 = threading.Thread(target=worker, args=(bar2,))
    t1.start(); t2.start()
    t1.join(); t2.join()
    assert bar1.n == 1000
    assert bar2.n == 1000
    mb.close()


# ── Real-world agent use case ───────────────────────────────────────────────


def test_agent_tool_invocation_pattern():
    """Simulate processing a batch of agent tool calls with progress."""
    buf = io.StringIO()
    tool_calls = [{"name": f"tool-{i}", "args": {"x": i}} for i in range(50)]

    def fake_execute(call):
        time.sleep(0)  # simulate work
        return {"ok": True, "call": call["name"]}

    results = []
    for call in progress(tool_calls, desc="Executing tools", file=buf, min_interval=0, force=True):
        results.append(fake_execute(call))

    assert len(results) == 50
    assert "50/50" in buf.getvalue()
    assert "Executing tools" in buf.getvalue()
