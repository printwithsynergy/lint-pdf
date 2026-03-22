"""Tests for the hot folder watcher — stabilization and file detection."""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

from lintpdf_hotfolder.watcher import HotFolderWatcher, SUPPORTED_EXTENSIONS


def test_supported_extensions():
    """All expected extensions are in the supported set."""
    expected = {".pdf", ".eps", ".ps", ".tiff", ".tif", ".jpg", ".jpeg", ".png", ".ai"}
    assert expected == SUPPORTED_EXTENSIONS


def test_detects_new_pdf(tmp_path: Path):
    """A new PDF in the watch directory is queued after stabilization."""
    ready_queue: queue.Queue[Path] = queue.Queue()
    shutdown = threading.Event()

    watcher = HotFolderWatcher(
        watch_dir=tmp_path,
        ready_queue=ready_queue,
        stabilization_seconds=0.3,
        shutdown_event=shutdown,
    )
    watcher.start()

    try:
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 fake content")

        # Wait for stabilization + processing
        result = ready_queue.get(timeout=5)
        assert result.name == "test.pdf"
    finally:
        shutdown.set()
        watcher.stop()


def test_ignores_unsupported_extension(tmp_path: Path):
    """Files with unsupported extensions are not queued."""
    ready_queue: queue.Queue[Path] = queue.Queue()
    shutdown = threading.Event()

    watcher = HotFolderWatcher(
        watch_dir=tmp_path,
        ready_queue=ready_queue,
        stabilization_seconds=0.2,
        shutdown_event=shutdown,
    )
    watcher.start()

    try:
        (tmp_path / "readme.txt").write_text("not a PDF")
        (tmp_path / "data.csv").write_text("a,b,c")

        # Give enough time for stabilization if it were triggered
        time.sleep(1.0)
        assert ready_queue.empty()
    finally:
        shutdown.set()
        watcher.stop()


def test_stabilization_restarts_on_size_change(tmp_path: Path):
    """If the file size changes during stabilization, the timer restarts."""
    ready_queue: queue.Queue[Path] = queue.Queue()
    shutdown = threading.Event()

    watcher = HotFolderWatcher(
        watch_dir=tmp_path,
        ready_queue=ready_queue,
        stabilization_seconds=0.5,
        shutdown_event=shutdown,
    )
    watcher.start()

    try:
        test_file = tmp_path / "growing.pdf"
        test_file.write_bytes(b"%PDF partial")

        # Write more data before stabilization completes
        time.sleep(0.2)
        test_file.write_bytes(b"%PDF partial with more data appended")

        # Should not yet be queued (stabilization restarted)
        time.sleep(0.3)
        assert ready_queue.empty()

        # Now wait for the full stabilization period
        result = ready_queue.get(timeout=5)
        assert result.name == "growing.pdf"
    finally:
        shutdown.set()
        watcher.stop()


def test_processes_existing_files_on_start(tmp_path: Path):
    """Files already in the directory when the watcher starts are processed."""
    # Create files before starting the watcher
    (tmp_path / "existing.pdf").write_bytes(b"%PDF-1.4 existing")
    (tmp_path / "also.eps").write_bytes(b"%!PS-Adobe existing eps")

    ready_queue: queue.Queue[Path] = queue.Queue()
    shutdown = threading.Event()

    watcher = HotFolderWatcher(
        watch_dir=tmp_path,
        ready_queue=ready_queue,
        stabilization_seconds=0.3,
        shutdown_event=shutdown,
    )
    watcher.start()

    try:
        results = set()
        for _ in range(2):
            result = ready_queue.get(timeout=5)
            results.add(result.name)
        assert results == {"existing.pdf", "also.eps"}
    finally:
        shutdown.set()
        watcher.stop()
