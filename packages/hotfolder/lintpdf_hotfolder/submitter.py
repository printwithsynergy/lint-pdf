"""Worker that submits queued files to the LintPDF API."""

from __future__ import annotations

import json
import logging
import queue
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

log = logging.getLogger(__name__)


class Submitter:
    """Processes files from the ready queue: submit → poll → route."""

    def __init__(
        self,
        ready_queue: queue.Queue[tuple[Path, Path | None]],
        *,
        api_key: str,
        base_url: str = "https://api.lintpdf.com",
        profile: str = "lintpdf-default",
        pass_dir: Path | None = None,
        fail_dir: Path | None = None,
        error_dir: Path | None = None,
        write_sidecar: bool = True,
        poll_interval: float = 5.0,
        shutdown_event: threading.Event | None = None,
    ) -> None:
        self._queue = ready_queue
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._profile = profile
        self._pass_dir = pass_dir
        self._fail_dir = fail_dir
        self._error_dir = error_dir
        self._write_sidecar = write_sidecar
        self._poll_interval = poll_interval
        self._shutdown_event = shutdown_event or threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the submitter worker thread."""
        self._thread = threading.Thread(target=self._run, daemon=True, name="submitter")
        self._thread.start()

    def stop(self) -> None:
        """Signal the worker to stop and wait for it to finish."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=120)

    def _run(self) -> None:
        """Main worker loop."""
        while not self._shutdown_event.is_set():
            try:
                file_path, jdf_path = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                self._process_file(file_path, jdf_path)
            except Exception:
                log.exception("Unexpected error processing %s", file_path)
                self._move_file(
                    file_path, self._error_dir, error_info="Unexpected processing error"
                )

    def _process_file(self, file_path: Path, jdf_path: Path | None = None) -> None:
        """Submit a file to LintPDF and route based on results."""
        if not file_path.exists():
            log.warning("File no longer exists: %s", file_path)
            return

        log.info("Submitting: %s", file_path.name)
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            # Submit
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                if jdf_path and jdf_path.exists():
                    jdf_fh = open(jdf_path, "rb")
                    files["jdf_file"] = (
                        jdf_path.name,
                        jdf_fh,
                        "application/octet-stream",
                    )
                else:
                    jdf_fh = None

                try:
                    response = httpx.post(
                        f"{self._base_url}/api/v1/jobs",
                        headers=headers,
                        files=files,
                        data={"profile_id": self._profile},
                        timeout=120,
                    )
                finally:
                    if jdf_fh is not None:
                        jdf_fh.close()

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                log.warning("Rate limited. Retrying after %ds", retry_after)
                time.sleep(retry_after)
                # Re-queue the file
                self._queue.put((file_path, jdf_path))
                return

            response.raise_for_status()
            job_data = response.json()
            job_id = job_data["id"]
            log.info("Job submitted: %s -> %s", file_path.name, job_id)

        except Exception as exc:
            log.error("Submit failed for %s: %s", file_path.name, exc)
            self._move_file(file_path, self._error_dir, error_info=str(exc))
            return

        # Poll for completion
        result = self._poll_for_result(job_id, headers)
        if result is None:
            log.error("Job %s timed out for %s", job_id, file_path.name)
            self._move_file(
                file_path, self._error_dir, error_info=f"Job {job_id} timed out"
            )
            return

        # Route based on results
        summary = result.get("summary", {})
        passed = summary.get("passed", False)
        errors = summary.get("error_count", 0)
        warnings = summary.get("warning_count", 0)
        advisory = summary.get("advisory_count", 0)

        log.info(
            "Result for %s — %s | errors=%d warnings=%d advisory=%d",
            file_path.name,
            "PASS" if passed else "FAIL",
            errors,
            warnings,
            advisory,
        )

        dest_dir = self._pass_dir if passed else self._fail_dir
        dest = self._move_file(file_path, dest_dir)

        if self._write_sidecar and dest:
            self._write_sidecar_report(dest, file_path.name, result)

    def _poll_for_result(self, job_id: str, headers: dict) -> dict | None:
        """Poll until the job completes or times out (10 minutes)."""
        max_attempts = int(600 / self._poll_interval)
        for _ in range(max_attempts):
            if self._shutdown_event.is_set():
                return None

            time.sleep(self._poll_interval)

            try:
                resp = httpx.get(
                    f"{self._base_url}/api/v1/jobs/{job_id}",
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status")
                if status in ("complete", "failed"):
                    return data
            except httpx.HTTPError as exc:
                log.warning("Poll error for job %s: %s", job_id, exc)

        return None

    def _move_file(
        self,
        file_path: Path,
        dest_dir: Path | None,
        error_info: str | None = None,
    ) -> Path | None:
        """Move a file to the destination directory. Returns the new path."""
        if dest_dir is None:
            return None

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / file_path.name

        # Handle name collisions
        if dest.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        try:
            shutil.move(str(file_path), str(dest))
            log.info("Moved %s -> %s", file_path.name, dest)
        except OSError as exc:
            log.error("Failed to move %s: %s", file_path.name, exc)
            return None

        if error_info and self._write_sidecar:
            sidecar = dest.parent / f"{dest.name}.lintpdf.json"
            sidecar.write_text(
                json.dumps(
                    {
                        "error": error_info,
                        "file_name": file_path.name,
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                )
            )

        return dest

    def _write_sidecar_report(
        self, dest: Path, original_name: str, result: dict
    ) -> None:
        """Write a JSON sidecar report alongside the moved file."""
        summary = result.get("summary", {})
        sidecar_path = dest.parent / f"{dest.name}.lintpdf.json"

        report = {
            "job_id": result.get("id", result.get("job_id", "")),
            "file_name": original_name,
            "profile_id": result.get("profile_id", self._profile),
            "passed": summary.get("passed", False),
            "summary": {
                "error_count": summary.get("error_count", 0),
                "warning_count": summary.get("warning_count", 0),
                "advisory_count": summary.get("advisory_count", 0),
                "total_findings": summary.get("total_findings", 0),
            },
            "findings": result.get("findings", []),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            sidecar_path.write_text(json.dumps(report, indent=2))
            log.debug("Sidecar written: %s", sidecar_path)
        except OSError as exc:
            log.error("Failed to write sidecar for %s: %s", dest.name, exc)
