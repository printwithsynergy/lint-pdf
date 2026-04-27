# Engine convenience targets.
#
# Most CI / dev tasks run via `uv run pytest` directly; this Makefile
# captures the opt-in smoke targets that need a specific marker selector
# or env-var sentinel so they don't run by default.

.PHONY: smoke-preflight smoke-live-ai

# In-process preflight smoke — stubs Claude, runs offline, free.
# See tests/test_preflight_smoke.py and the v2 playbook PR 8.
smoke-preflight:
	uv run pytest tests/test_preflight_smoke.py -s -v

# Live-AI verification — hits real Claude Haiku 4.5. Costs ~$0.01.
# Requires ANTHROPIC_API_KEY. Use at release-tag time.
# See tests/integration/test_explain_live.py and the v2 playbook PR 20.
smoke-live-ai:
	uv run pytest -m live_ai
