"""Modal app for the customer-facing AI accuracy audit.

Deploy:
    modal deploy src/inference_service/modal_audit.py

Serves a single POST endpoint (``/audit``) consumed by
``lintpdf.audit.customer.CustomerAuditor`` on the engine side.
Request/response shapes match the CustomerAuditor contract:

    POST  /audit
    body: {
      "findings": [
        {"index": 0, "inspection_id": "LPDF_OVER_001", "severity": "warning",
         "message": "...", "page_num": 1, "bbox": [x0,y0,x1,y1] | null,
         "page_png_b64": "iVBORw0KGgoAAAANSUhEUg..." | null},
        ...
      ]
    }
    200 OK
    body: {
      "verdicts": [
        {"finding_index": 0, "status": "confirmed", "rationale": "..."},
        ...
      ]
    }

## Model

**Qwen2-VL-7B-Instruct** on A10G (24 GB VRAM, comfortably fits the
7B fp16 weights + the rendered page tensor). Selected over Llama 3.2
Vision for stronger JSON-output discipline — the engine caller
depends on strictly-structured verdicts, and Qwen2-VL's
``chat_template`` + greedy-decode consistently emits parsable JSON.

Model weights are cached in a Modal Volume under ``/models`` so
cold-starts past the first container amortise (first cold start
downloads ~17 GB, subsequent cold starts are ~15 s).

## Why separate from ``modal_deploy.py``?

The main ``lintpdf-inference`` app bundles narrow inspection models
(image-quality, NSFW, logo detector, etc.) into one container. The
audit pass is a 7 B-param vision-LLM that dwarfs those models and
has a different latency / batching profile. Keeping it as its own
Modal app lets:

* The GPU autoscaling profile tune independently (audits are
  latency-sensitive; the smaller inspectors are throughput-bound).
* An audit-heavy burst never starve the existing inspectors.
* The 17 GB model weights stay out of the `lintpdf-inference`
  container image.
"""

from __future__ import annotations

import modal

app = modal.App("lintpdf-audit")

# Volume for caching the ~17 GB Qwen2-VL checkpoint across cold-starts.
model_cache = modal.Volume.from_name("lintpdf-audit-models", create_if_missing=True)

audit_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "libgl1-mesa-glx",
        "libglib2.0-0",
    )
    .pip_install(
        # FastAPI web endpoint.
        "fastapi>=0.115.0",
        "pydantic>=2.8.0",
        "Pillow>=10.0.0",
        # ML stack. Pinning torch to the CUDA 12.1 wheel aligned with
        # Modal's A10G driver — bare ``torch>=2`` would sometimes grab
        # the CPU wheel on cold builds.
        "torch==2.4.0",
        "torchvision==0.19.0",
        "transformers>=4.45.0",
        "accelerate>=0.34.0",
        "qwen-vl-utils>=0.0.8",
        "huggingface_hub>=0.25.0",
        "bitsandbytes>=0.43.0",
    )
    .env({"HF_HOME": "/models/hf_home"})
)


MODEL_ID = "Qwen/Qwen2-VL-7B-Instruct"
_ALLOWED_STATUSES = ("confirmed", "disputed", "needs_context")
_MAX_NEW_TOKENS = 96  # "confirmed" + one-sentence rationale is ~60 tokens


_SYSTEM_PROMPT = (
    "You audit print-preflight findings against rendered PDF pages. "
    "For each finding, reply strictly as compact JSON on a single line "
    'of the form {"status": "<s>", "rationale": "<one sentence>"}. '
    "Status must be exactly one of: confirmed, disputed, needs_context. "
    "Choose 'disputed' only when the rendered image clearly contradicts "
    "the engine's claim; default to 'confirmed' when the finding is "
    "plausible against the pixels. Use 'needs_context' when the "
    "decision requires a JDF sidecar or brand spec you can't see."
)


@app.cls(
    image=audit_image,
    gpu="A10G",
    volumes={"/models": model_cache},
    scaledown_window=300,
    min_containers=0,
    max_containers=30,
    timeout=300,
    memory=24576,
)
class AuditModel:
    """Qwen2-VL-7B-Instruct wrapper.

    Loaded once per container via ``@modal.enter()`` — the 7B fp16
    weights consume ~14 GB of VRAM, well inside the A10G's 24 GB, so
    a single container handles back-to-back audits without reloading.
    """

    @modal.enter()
    def load(self) -> None:
        import torch
        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
            device_map="auto",
        ).eval()
        self.processor = AutoProcessor.from_pretrained(MODEL_ID)

    @modal.fastapi_endpoint(method="POST", label="audit")
    def audit(self, payload: dict) -> dict:
        """Verify each finding in the batch against its page image.

        Runs one forward pass per finding — batching multiple findings
        into a single generate() call saves negligible time for 7B
        vision models (the per-token decode dominates), and keeping
        one-per-call makes the JSON-parse layer trivial. Containers
        still handle many back-to-back audits without reloading the
        model.
        """
        findings = payload.get("findings") or []
        verdicts: list[dict] = []
        for f in findings:
            verdicts.append(_audit_single(self.processor, self.model, self.device, f))
        return {"verdicts": verdicts}


def _audit_single(processor, model, device: str, finding: dict) -> dict:  # noqa: ANN001
    """Run one vision-LLM forward pass against a single finding."""
    import base64
    import io
    import json

    from PIL import Image

    idx = finding.get("index")
    page_png_b64 = finding.get("page_png_b64")
    image: Image.Image | None = None
    if page_png_b64:
        try:
            image = Image.open(io.BytesIO(base64.b64decode(page_png_b64))).convert("RGB")
        except Exception:
            image = None

    user_text = (
        "Finding details (JSON):\n"
        f"  inspection_id: {finding.get('inspection_id')}\n"
        f"  severity:      {finding.get('severity')}\n"
        f"  page_num:      {finding.get('page_num')}\n"
        f"  message:       {finding.get('message')}\n"
        f"  bbox:          {finding.get('bbox')}\n\n"
        "Reply with compact JSON only — no prose before or after."
    )

    content: list[dict] = []
    if image is not None:
        content.append({"type": "image", "image": image})
    content.append({"type": "text", "text": user_text})

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]

    prompt = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    inputs = processor(
        text=[prompt],
        images=[image] if image is not None else None,
        padding=True,
        return_tensors="pt",
    ).to(device)

    import torch

    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=_MAX_NEW_TOKENS,
            do_sample=False,  # deterministic — we want the same verdict every rerun
            temperature=1.0,
        )
    trimmed = generated[:, inputs.input_ids.shape[1] :]
    out_text = processor.batch_decode(
        trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False,
    )[0].strip()

    status, rationale = _parse_verdict(out_text)
    return {
        "finding_index": idx,
        "status": status,
        "rationale": rationale,
    }


def _parse_verdict(raw: str) -> tuple[str, str]:
    """Pull ``{"status": ..., "rationale": ...}`` out of the model output.

    Qwen2-VL with a strict system prompt + greedy decode reliably
    emits a single JSON object, but real production text occasionally
    wraps the JSON in a code fence. The parser strips those and
    falls back to a permissive substring search so a malformed
    response degrades to "confirmed" rather than crashing the worker.
    """
    import json
    import re

    match = re.search(r"\{.*?\}", raw, re.DOTALL)
    if match is not None:
        candidate = match.group(0)
        try:
            doc = json.loads(candidate)
        except Exception:
            doc = None
        if isinstance(doc, dict):
            status = str(doc.get("status", "")).strip().lower()
            rationale = str(doc.get("rationale", "")).strip()
            if status in _ALLOWED_STATUSES:
                return status, rationale or "No rationale."
    # Soft fallback — the caller drops unknown statuses anyway, so
    # emitting "confirmed" with the raw output as rationale keeps
    # the verdict visible for operators to triage.
    return "confirmed", f"Unparseable model output: {raw[:200]}"
