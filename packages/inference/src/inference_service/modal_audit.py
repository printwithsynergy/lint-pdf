"""Modal app for the customer-facing AI accuracy audit.

Deploy:
    modal deploy src/inference_service/modal_audit.py

Serves a single POST endpoint at ``/audit`` consumed by
``lintpdf.audit.customer.CustomerAuditor`` on the engine side.
Request/response shapes match the CustomerAuditor contract:

    POST /audit
    {
      "findings": [
        {"index": 0, "inspection_id": "LPDF_OVER_001", "severity": "warning",
         "message": "...", "page_num": 1, "bbox": [x0,y0,x1,y1] | null,
         "page_png_b64": "iVBORw0KGgoAAAANSUhEUg..." | null},
        ...
      ]
    }
    → 200 OK
    {
      "verdicts": [
        {"finding_index": 0, "status": "confirmed", "rationale": "..."},
        ...
      ]
    }

## Model

Intended to run **Qwen2-VL-7B-Instruct** (or **Llama-3.2-11B-Vision-Instruct**
as an alternate — swap the ``MODEL_ID`` + prompt template below) on an
A10G GPU. The loader uses ``transformers`` with ``torch_dtype="auto"``
so Modal's CUDA driver picks fp16 / bf16 based on the instance.

## Why separate from ``modal_deploy.py``?

The main ``lintpdf-inference`` app bundles many tasks (image quality,
logo detection, NSFW, etc.) into a single container image. The audit
pass is a vision-LLM that needs fundamentally different weights +
memory profile + prompt flow, and is gated to a different plan tier
(Scale + Enterprise only). Keeping it as its own Modal app:

* lets the GPU autoscaling profile tune independently (audits are
  latency-sensitive; the image-quality models are throughput-bound);
* prevents an audit-heavy burst from starving the existing inspectors;
* keeps the vision-LLM weights out of the existing image — the main
  `lintpdf-inference` container stays small.

## Stub status (WS3c checkpoint)

The handler below returns **placeholder "confirmed" verdicts** so
the full Railway → engine → Modal → verdict → DB pipeline can be
wired and tested end-to-end before the GPU model lands. Replace
``_run_audit_model`` with a real Qwen2-VL call once the model
loader is ready. The CustomerAuditor client treats unknown /
missing verdicts as ``None`` (no chip), so shipping the placeholder
causes no incorrect customer-visible state — worst case, every
finding comes back confirmed.
"""

from __future__ import annotations

import modal

app = modal.App("lintpdf-audit")

audit_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "libgl1-mesa-glx",
        "libglib2.0-0",
    )
    .pip_install(
        "fastapi>=0.115.0",
        "Pillow>=10.0.0",
        # Real deployment will add:
        # "torch>=2.0.0",
        # "transformers>=4.45.0",
        # "accelerate>=0.34.0",
        # "qwen-vl-utils",
    )
)


@app.function(
    image=audit_image,
    # gpu="A10G",                 # enable once the vision LLM is plugged in
    scaledown_window=120,
    min_containers=0,
    max_containers=30,
    timeout=180,
    memory=4096,
)
@modal.fastapi_endpoint(method="POST", label="audit")
def audit(request_body: dict):
    """Return per-finding verdicts for the batch.

    Placeholder implementation — returns ``confirmed`` for every
    finding so the caller's (engine-side) error handling paths can
    be exercised end-to-end without actually loading a vision model.
    Swap ``_run_audit_model`` for the real Qwen2-VL call when ready.
    """
    findings = request_body.get("findings") or []
    verdicts = [
        {
            "finding_index": f.get("index"),
            "status": "confirmed",
            "rationale": (
                "Stub auditor — the real Qwen2-VL vision pass has not been "
                "deployed yet. Returning 'confirmed' for every finding so the "
                "engine-side integration can be validated without false "
                "negatives poisoning customer data."
            ),
        }
        for f in findings
    ]
    return {"verdicts": verdicts}


def _run_audit_model(
    findings: list[dict],
) -> list[dict]:  # pragma: no cover — not wired yet
    """Real vision-LLM implementation (stub).

    Pseudo-code for the Qwen2-VL path::

        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        import torch
        from PIL import Image
        import base64, io

        model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-7B-Instruct",
            torch_dtype="auto",
            device_map="auto",
        )
        processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")

        out = []
        for f in findings:
            img_bytes = base64.b64decode(f["page_png_b64"]) if f.get("page_png_b64") else None
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB") if img_bytes else None
            prompt = (
                "Verify this PDF preflight finding against the rendered page. "
                "Reply strictly as JSON {status: confirmed|disputed|needs_context, "
                "rationale: str}. Finding: " + f["message"]
            )
            # ... build chat template with image + text, generate, parse JSON
            verdict = {"finding_index": f["index"], "status": "...", "rationale": "..."}
            out.append(verdict)
        return out
    """
    raise NotImplementedError("Qwen2-VL wiring pending")
