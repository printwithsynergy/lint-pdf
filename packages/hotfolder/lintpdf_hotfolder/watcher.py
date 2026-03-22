"""File system watcher with stabilization logic."""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset({
    ".pdf", ".eps", ".ps",
    ".tiff", ".tif",
    ".jpg", ".jpeg", ".png",
    ".ai",
})


class _StabilizationHandler(FileSystemEventHandler):
    """Watches for new files and waits for them to stabilize before queueing."""

    def __init__(
        self,
        ready_queue: queue.Queue[Path],
        stabilization_seconds: float,
        shutdown_event: threading.Event,
    ) -> None:
        super().__init__()
        self._ready_queue = ready_queue
        self._stabilization_seconds = stabilization_seconds
        self._shutdown_event = shutdown_event
        # Track pending files: path -> (last_size, timer)
        self._pending: dict[str, tuple[int, threading.Timer]] = {}
        self._lock = threading.Lock()

    def _is_supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            self._start_stabilization(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            self._start_stabilization(event.src_path)

    def _start_stabilization(self, path: str) -> None:
        """Start or restart the stabilization timer for a file."""
        if self._shutdown_event.is_set():
            return

        with self._lock:
            # Cancel existing timer if any
            if path in self._pending:
                _, old_timer = self._pending[path]
                old_timer.cancel()

            try:
                size = os.path.getsize(path)
            except OSError:
                return

            timer = threading.Timer(
                self._stabilization_seconds,
                self._check_stable,
                args=(path, size),
            )
            timer.daemon = True
            self._pending[path] = (size, timer)
            timer.start()
            log.debug("Stabilization started for %s (size=%d)", path, size)

    def _check_stable(self, path: str, expected_size: int) -> None:
        """Check if the file size has stabilized."""
        if self._shutdown_event.is_set():
            return

        try:
            current_size = os.path.getsize(path)
        except OSError:
            with self._lock:
                self._pending.pop(path, None)
            return

        if current_size == expected_size:
            # File is stable — queue it
            with self._lock:
                self._pending.pop(path, None)
            log.info("File stabilized: %s (%d bytes)", path, current_size)
            self._ready_queue.put(Path(path))
        else:
            # Size changed — restart stabilization
            log.debug("File still changing: %s (%d -> %d)", path, expected_size, current_size)
            self._start_stabilization(path)

    def cancel_all(self) -> None:
        """Cancel all pending stabilization timers."""
        with self._lock:
            for _, (_, timer) in self._pending.items():
                timer.cancel()
            self._pending.clear()


class HotFolderWatcher:
    """Watches a directory for new files and queues stable files for processing."""

    def __init__(
        self,
        watch_dir: Path,
        ready_queue: queue.Queue[Path],
        stabilization_seconds: float = 2.0,
        shutdown_event: threading.Event | None = None,
    ) -> None:
        self.watch_dir = watch_dir
        self._ready_queue = ready_queue
        self._shutdown_event = shutdown_event or threading.Event()
        self._handler = _StabilizationHandler(
            ready_queue=ready_queue,
            stabilization_seconds=stabilization_seconds,
            shutdown_event=self._shutdown_event,
        )
        self._observer = Observer()

    def start(self) -> None:
        """Start watching the directory."""
        self._observer.schedule(self._handler, str(self.watch_dir), recursive=False)
        self._observer.start()
        log.info("Watching directory: %s", self.watch_dir)

        # Process existing files in the directory
        for entry in self.watch_dir.iterdir():
            if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                log.info("Found existing file: %s", entry.name)
                self._handler._start_stabilization(str(entry))

    def stop(self) -> None:
        """Stop watching and cancel pending timers."""
        self._handler.cancel_all()
        self._observer.stop()
        self._observer.join(timeout=5)
        log.info("Watcher stopped")
