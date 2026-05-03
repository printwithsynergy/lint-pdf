# LintPDF SDK Specification

The contract every official LintPDF client SDK must implement. The
spec is the union of three concerns:

1. **Transport** — how requests are constructed (auth, content
   types, idempotency, retry).
2. **Security primitives** — webhook signature verification,
   share-link token handling, TLS validation defaults.
3. **Type surface** — request / response models matching the
   OpenAPI spec.

This document is the source of truth for all per-language
implementations under `sdk-{ts,go,ruby,java,php,laravel,perl}`.
Any deviation needs an explicit waiver written into the SDK's
README.

---

## 1. Transport

### 1.1 Bearer authentication

Every request carries:

```
Authorization: Bearer {api_key}
```

Where `{api_key}` is the customer's `lpdf_live_...` (production)
or `lpdf_test_...` (sandbox) API key. The SDK must NOT log the
key, must NOT echo it in error messages, and must support
overriding it per-request for impersonation flows that require
admin keys (`X-Admin-Key: {admin_key}` instead).

### 1.2 Base URL

Default: `https://api.lintpdf.com`

The SDK constructor accepts an override (`base_url=` /
`baseUrl:` / equivalent idiomatic form). Self-hosted OSS deploys
will set this to their internal hostname.

### 1.3 Content types

- Request body: `application/json` for all routes except multipart
  uploads (`POST /api/v1/jobs`, `POST /api/v1/batch/submit`,
  `POST /api/v1/ai/config/logos`) which use `multipart/form-data`.
- Response body: `application/json` always. Annotated PDF
  downloads route through pre-signed URLs returned as JSON, not
  binary response bodies.
- Charset: UTF-8 in both directions; SDK must NOT BOM-prefix.

### 1.4 Idempotency keys

Routes that mint persistent state (notably
`POST /api/v1/jobs/{id}/reports`) accept an optional
`Idempotency-Key: {uuid}` header. SDKs must expose this as a
per-request option named `idempotency_key` / `idempotencyKey`
following each language's idiomatic casing.

When set, the engine returns the same `report_token` on retry of
the same key within 24h.

### 1.5 Retry policy

Default: 3 retries on `5xx`, `429`, and connect-level errors
with exponential backoff: 1s, 2s, 4s. Total wall-clock cap: 30s.
SDK consumers may override the schedule with a `retry=` /
`retry:` parameter.

`429 Too Many Requests` responses always include
`Retry-After: {seconds}`; SDK retry must honor that value over
its own backoff schedule when present.

### 1.6 Telemetry headers

- `User-Agent: LintPDF-SDK-{lang}/{version}` — required, must
  identify the SDK + version cleanly so support requests can be
  triaged.
- `X-Request-Id` — optional client-supplied request correlation
  ID. The engine echoes it back on the response. SDKs SHOULD
  expose a hook for callers to set this.

---

## 2. Security primitives

### 2.1 Webhook signature verification

The engine signs every outbound webhook payload with HMAC-SHA256
using the tenant's webhook secret. The signature lives in the
`X-LintPDF-Signature` header in the form:

```
X-LintPDF-Signature: sha256={hex_digest}
```

The signed body is the raw, sort_keys-canonical JSON of the
payload — exactly the bytes the engine put on the wire. Don't
re-serialize before verifying.

**Required SDK helper:**

```pseudocode
verify_webhook_signature(
    secret: str,
    body: bytes | str,
    header_value: str,
) -> bool
```

Implementation:

```pseudocode
prefix = "sha256="
if not header_value.startswith(prefix):
    return False
expected = prefix + hmac_sha256_hex(secret, body)
return constant_time_compare(expected, header_value)
```

**Constant-time compare**: every language's stdlib has one
(`hmac.compare_digest` in Python, `crypto.timingSafeEqual` in
Node, `subtle.ConstantTimeCompare` in Go's `crypto/subtle`,
etc.). DO NOT use `==`.

The matching event type travels in `X-LintPDF-Event:
{event_name}`. The SDK helper SHOULD return both the verified
flag and the parsed event name as a tuple / record so callers
don't need to read two headers separately.

### 2.2 Share-link tokens

Public report share links are token-based, not HMAC-signed
URLs. The engine mints a `report_token` on
`POST /api/v1/jobs/{id}/reports`; the customer embeds the token
in a URL like:

```
https://reports.lintpdf.com/view/{token}
```

The SDK does NOT need a signing helper for these — the token IS
the credential. SDKs SHOULD expose:

```pseudocode
build_share_link(token: str, base_url: str = "https://reports.lintpdf.com") -> str
```

Single-line helper that concatenates `base_url + "/view/" +
token`. The wrapper exists so customers don't accidentally hand-
build URLs that miss the `/view/` path segment.

### 2.3 TLS / certificate validation

**TLS is mandatory.** Every official SDK constructor MUST default
to verifying the server's TLS certificate. SDKs MAY expose an
escape hatch (`insecure=true` / `tlsInsecure: true`) for
self-signed-cert testing, but it MUST be:

1. Documented as DEVELOPMENT-ONLY in the SDK's README.
2. Logged at WARN level on every constructor call that enables it.
3. Refused if the base URL is `https://api.lintpdf.com` (cannot
   disable TLS verification against the production endpoint).

### 2.4 Secret handling

API keys, webhook secrets, and admin keys are secrets. SDKs
MUST:

- Pull from environment variables when not constructor-supplied
  (`LINTPDF_API_KEY`, `LINTPDF_ADMIN_KEY`, `LINTPDF_WEBHOOK_SECRET`).
- Redact secrets in any debug/info logging — replace with
  `lpdf_live_***` / `lpdf_test_***` based on the prefix.
- NOT serialize secrets when the SDK's client object is
  printed / dumped (`__repr__` in Python, `MarshalJSON` in Go,
  etc. must explicitly mask).

---

## 3. Type surface

### 3.1 Source of truth

The engine ships an OpenAPI 3.1.0 spec at
`https://api.lintpdf.com/openapi.json`. SDK type generation
should run from this spec, not from hand-curated DTOs. Each SDK
ships a `scripts/regen-from-openapi.{sh,ts,go,...}` that fetches
the spec and regenerates request / response models.

The Postman collection at
`https://lintpdf.com/postman/lintpdf.postman_collection.json` is
the human-readable companion — use it to verify that SDK call
sites match the documented examples.

### 3.2 Naming conventions

Each language follows its own idiomatic casing for SDK API
surfaces, but the underlying field names match the OpenAPI
spec exactly (snake_case). E.g.:

- TypeScript: camelCase methods + camelCase request fields
  (`{ profileId: 'lintpdf-default' }`) with a transformer layer
  that maps to/from snake_case before/after the wire.
- Go: PascalCase methods + struct fields with explicit
  `json:"profile_id"` tags.
- Ruby: snake_case methods (idiomatic) + snake_case fields (no
  transform needed).
- Java: camelCase methods + Jackson annotations
  (`@JsonProperty("profile_id")`).
- PHP / Laravel: camelCase methods + snake_case array keys (no
  transform; PHP arrays are loose).
- Perl: snake_case methods + hashref keys matching the wire.

### 3.3 Error model

Every non-2xx response decodes into an SDK-language exception
carrying:

- `status: int` — HTTP status code.
- `error_code: str` — engine's machine-readable error tag (e.g.
  `plan_upgrade_required`, `entitlement_denied`,
  `invalid_signature`).
- `message: str` — human-readable summary.
- `request_id: str | None` — engine-assigned correlation ID
  from the response's `X-Request-Id` header.
- `details: dict | None` — structured per-error extras from the
  engine (e.g. `required_plan: 'scale'` for upgrade errors).

The exception class hierarchy SHOULD mirror the major error
families:

- `LintPDFError` (base)
  - `AuthError` (401, 403)
  - `RateLimitError` (429) — exposes `retry_after_seconds: int`
  - `EntitlementError` (402) — exposes `required_plan: str`
  - `ValidationError` (422) — exposes `field_errors: list`
  - `ServerError` (5xx) — retryable
  - `NetworkError` (no HTTP response)

---

## 4. Compatibility matrix

| Concern | Spec section |
|---|---|
| Auth header | 1.1 |
| Base URL override | 1.2 |
| JSON body | 1.3 |
| Multipart uploads | 1.3 |
| Idempotency keys | 1.4 |
| Retry / backoff | 1.5 |
| User-Agent | 1.6 |
| HMAC webhook verify | 2.1 |
| Share-link helper | 2.2 |
| TLS default-on | 2.3 |
| Secret redaction | 2.4 |
| OpenAPI-derived types | 3.1 |
| Error class hierarchy | 3.3 |

Per-language SDKs ship a `COMPATIBILITY.md` checking each row
explicitly. CI rejects an SDK PR that adds a new method but
silently skips a row.

---

## 5. Versioning

SDK versions follow semver:

- **Major bump** on a breaking SDK API change OR an engine
  breaking change that requires SDK callsite changes.
- **Minor bump** on a new method / new field / new optional
  parameter.
- **Patch bump** on a bug fix or doc-only change.

The SDK major version IS NOT tied to the engine OpenAPI version
— a single SDK major can span multiple engine minor releases
since the OpenAPI is additive. SDKs SHOULD pin a *minimum*
engine version in their README.
