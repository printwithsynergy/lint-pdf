# T4-A09 — Encryption permission bit 10 (screen reader)

## What the check detects

When the PDF is encrypted, the `/Encrypt /P` permission flags
include bit 10 ("Extract text and graphics in support of
accessibility"). When the bit is **clear**, screen readers can't
extract the document text — a hard accessibility fail.

Per ISO 32000-2 §7.6.4.2 Table 22, the P value is a 32-bit signed
integer where bit 10 (= 1 << 9 = 0x200) governs accessibility
extraction.

New inspection_id: `LPDF_ACCESS_SCREEN_READER`. Severity **warning**.

## Detection

1. Read `document.is_encrypted`. Skip if False (no permissions to
   check).
2. Read `document.trailer.get("/Encrypt").get("/P")`.
3. Bit 10 = `(p_value >> 9) & 1`. When 0, fire.

The /P field may be a negative number (signed 32-bit). Treat as
unsigned for bit testing — Python int has arbitrary precision so
`(p_value & 0x200) != 0` works on negative inputs after masking.

## Output

```
Finding(
    inspection_id="LPDF_ACCESS_SCREEN_READER",
    severity=Severity.WARNING,
    message="Encryption permissions deny screen-reader access (bit 10 cleared)",
    details={
        "p_value": -3392,
        "screen_reader_allowed": False,
    },
)
```

## Read-only / profiles

Confirmed read-only. Universal warning. Silent on unencrypted PDFs.
