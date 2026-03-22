"""CLI entry point for the LintPDF hot folder watcher."""

from __future__ import annotations

import logging
import os
import queue
import signal
import sys
import threading
from pathlib import Path

import click

from .submitter import Submitter
from .watcher import HotFolderWatcher


@click.command("lintpdf-watch")
@click.option(
    "--watch-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory to watch for new files.",
)
@click.option(
    "--api-key",
    envvar="LINTPDF_API_KEY",
    required=True,
    help="LintPDF API key (or set LINTPDF_API_KEY env var).",
)
@click.option(
    "--base-url",
    envvar="LINTPDF_BASE_URL",
    default="https://api.lintpdf.com",
    show_default=True,
    help="LintPDF API base URL.",
)
@click.option(
    "--profile",
    envvar="LINTPDF_PROFILE",
    default="grounded-default",
    show_default=True,
    help="Voyage Plan profile ID.",
)
@click.option(
    "--pass-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Move passed files here.",
)
@click.option(
    "--fail-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Move failed files here.",
)
@click.option(
    "--error-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Move errored files here.",
)
@click.option(
    "--sidecar/--no-sidecar",
    default=True,
    show_default=True,
    help="Write JSON sidecar reports alongside processed files.",
)
@click.option(
    "--stabilization",
    type=float,
    default=2.0,
    show_default=True,
    help="Seconds to wait for file size stability before submitting.",
)
@click.option(
    "--poll-interval",
    type=float,
    default=5.0,
    show_default=True,
    help="Seconds between LintPDF job status polls.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    show_default=True,
    help="Logging level.",
)
def main(
    watch_dir: Path,
    api_key: str,
    base_url: str,
    profile: str,
    pass_dir: Path | None,
    fail_dir: Path | None,
    error_dir: Path | None,
    sidecar: bool,
    stabilization: float,
    poll_interval: float,
    log_level: str,
) -> None:
    """Watch a directory for new files and submit them to LintPDF for preflight.

    Files are routed to pass, fail, or error directories based on results.
    A JSON sidecar report is written alongside each processed file.
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger("lintpdf_hotfolder")

    shutdown_event = threading.Event()
    ready_queue: queue.Queue[Path] = queue.Queue()

    watcher = HotFolderWatcher(
        watch_dir=watch_dir,
        ready_queue=ready_queue,
        stabilization_seconds=stabilization,
        shutdown_event=shutdown_event,
    )

    submitter = Submitter(
        ready_queue=ready_queue,
        api_key=api_key,
        base_url=base_url,
        profile=profile,
        pass_dir=pass_dir,
        fail_dir=fail_dir,
        error_dir=error_dir,
        write_sidecar=sidecar,
        poll_interval=poll_interval,
        shutdown_event=shutdown_event,
    )

    def handle_shutdown(signum: int, frame: object) -> None:
        sig_name = signal.Signals(signum).name
        log.info("Received %s — shutting down gracefully...", sig_name)
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    log.info("LintPDF Hot Folder v%s", "0.1.0")
    log.info("Watch dir: %s", watch_dir)
    log.info("Profile: %s", profile)
    log.info("API: %s", base_url)
    if pass_dir:
        log.info("Pass dir: %s", pass_dir)
    if fail_dir:
        log.info("Fail dir: %s", fail_dir)
    if error_dir:
        log.info("Error dir: %s", error_dir)

    watcher.start()
    submitter.start()

    # Block main thread until shutdown
    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(timeout=1.0)
    except KeyboardInterrupt:
        log.info("Keyboard interrupt — shutting down...")
        shutdown_event.set()

    watcher.stop()
    submitter.stop()
    log.info("Shutdown complete.")
