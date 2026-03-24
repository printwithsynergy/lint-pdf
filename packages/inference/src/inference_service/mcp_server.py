"""Modal MCP server for LintPDF inference service management.

Provides tools for deploying, monitoring, and managing the Modal inference
service directly from Claude Code.

Run:
    uv run --project packages/inference python -m inference_service.mcp_server
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "modal-lintpdf",
    description="Manage the LintPDF Modal inference service",
)

# Resolve project root (packages/inference)
_INFERENCE_DIR = Path(__file__).resolve().parent.parent.parent


def _run_modal(*args: str, cwd: Path | None = None) -> dict[str, Any]:
    """Run a modal CLI command and return structured output."""
    cmd = [sys.executable, "-m", "modal", *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=cwd or _INFERENCE_DIR,
            check=False,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Command timed out (300s)",
            "success": False,
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Modal CLI not found. Install with: pip install modal",
            "success": False,
        }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def deploy() -> str:
    """Deploy the LintPDF inference service to Modal.

    Runs `modal deploy` on the inference service. This builds the container
    image, uploads the code, and creates/updates the Modal app. Returns
    the deployment URL on success.
    """
    result = _run_modal(
        "deploy",
        "src/inference_service/modal_deploy.py",
    )
    if result["success"]:
        return f"Deployment successful.\n\n{result['stdout']}"
    return f"Deployment failed (exit {result['exit_code']}).\n\nstdout:\n{result['stdout']}\n\nstderr:\n{result['stderr']}"


@mcp.tool()
def serve() -> str:
    """Start the inference service locally with hot-reload (modal serve).

    Useful for development — runs the service locally with live code updates.
    The service will be accessible at a temporary Modal URL.
    """
    result = _run_modal(
        "serve",
        "src/inference_service/modal_deploy.py",
    )
    if result["success"]:
        return f"Serve started.\n\n{result['stdout']}"
    return (
        f"Serve failed.\n\nstdout:\n{result['stdout']}\n\nstderr:\n{result['stderr']}"
    )


@mcp.tool()
def app_list() -> str:
    """List all Modal apps in the workspace.

    Shows deployed apps, their status, and URLs.
    """
    result = _run_modal("app", "list")
    if result["success"]:
        return result["stdout"] or "No apps found."
    return f"Failed to list apps.\n\n{result['stderr']}"


@mcp.tool()
def app_status() -> str:
    """Get the status of the lintpdf-inference Modal app.

    Shows whether the app is deployed, container count, and endpoint URL.
    """
    # Modal doesn't have a direct "status" command, so we check the app list
    result = _run_modal("app", "list")
    if not result["success"]:
        return f"Failed to check status.\n\n{result['stderr']}"

    lines = result["stdout"].split("\n")
    matching = [line for line in lines if "lintpdf-inference" in line]
    if matching:
        header = lines[0] if lines else ""
        return f"{header}\n{''.join(matching)}"
    return "App 'lintpdf-inference' not found. It may not be deployed yet."


@mcp.tool()
def app_logs(n: int = 50) -> str:
    """View recent logs from the lintpdf-inference app.

    Args:
        n: Number of log lines to retrieve (default 50).
    """
    result = _run_modal("app", "logs", "lintpdf-inference", "--n", str(n))
    if result["success"]:
        return result["stdout"] or "No logs available."
    return f"Failed to get logs.\n\n{result['stderr']}"


@mcp.tool()
def app_stop() -> str:
    """Stop the lintpdf-inference Modal app.

    This stops all running containers. The app can be restarted by
    deploying again or by sending a request (auto-scales from 0).
    """
    result = _run_modal("app", "stop", "lintpdf-inference")
    if result["success"]:
        return "App stopped successfully."
    return f"Failed to stop app.\n\n{result['stderr']}"


@mcp.tool()
def volume_list() -> str:
    """List all Modal volumes in the workspace."""
    result = _run_modal("volume", "list")
    if result["success"]:
        return result["stdout"] or "No volumes found."
    return f"Failed to list volumes.\n\n{result['stderr']}"


@mcp.tool()
def volume_contents(path: str = "/") -> str:
    """Browse the model cache volume contents.

    Args:
        path: Path within the volume to list (default: root "/").
    """
    result = _run_modal("volume", "ls", "lintpdf-model-cache", path)
    if result["success"]:
        return result["stdout"] or f"No files at {path}"
    return f"Failed to list volume contents.\n\n{result['stderr']}"


@mcp.tool()
def secret_list() -> str:
    """List all Modal secrets in the workspace."""
    result = _run_modal("secret", "list")
    if result["success"]:
        return result["stdout"] or "No secrets found."
    return f"Failed to list secrets.\n\n{result['stderr']}"


@mcp.tool()
def secret_create(name: str, env_vars: dict[str, str] | None = None) -> str:
    """Create a Modal secret.

    Args:
        name: Name for the secret (e.g., 'lintpdf-inference-secrets').
        env_vars: Optional dict of environment variable key-value pairs.
    """
    args = ["secret", "create", name]
    if env_vars:
        for key, value in env_vars.items():
            args.append(f"{key}={value}")

    result = _run_modal(*args)
    if result["success"]:
        return f"Secret '{name}' created.\n\n{result['stdout']}"
    return f"Failed to create secret.\n\n{result['stderr']}"


@mcp.tool()
def health_check(endpoint_url: str) -> str:
    """Check the health of a deployed inference service.

    Args:
        endpoint_url: The Modal endpoint URL (e.g., https://...modal.run).
    """
    import httpx

    url = endpoint_url.rstrip("/") + "/health"
    try:
        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        return f"Health check passed: {json.dumps(body, indent=2)}"
    except httpx.HTTPStatusError as exc:
        return f"Health check failed: HTTP {exc.response.status_code}"
    except Exception as exc:
        return f"Health check error: {exc}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
