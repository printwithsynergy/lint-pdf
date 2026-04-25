# T2-ISO05 — Auto-suggest ISO 19593-1 processing-step tagging

## What the check detects

ISO 19593-1 standardises the `/PageContent /ProcessingSteps`
metadata that identifies which page elements correspond to
production processes (cutting, folding, varnish, white underprint,
etc.). When a tenant ships spot inks named `CutContour`, `Crease`,
`Varnish`, etc., they almost always want a corresponding
ProcessingSteps category set so downstream finishing tools
recognise the spot as a production process rather than a print-able
ink.

This check fires one **advisory** per recognised spot whose name
maps to a known ISO 19593-1 group. The analyzer reuses the
canonical taxonomy already maintained by `spot_name_normaliser`
(T3-D11) — same taxonomy keys, with a new `category → ISO group`
mapping table on top.

New inspection_id: `LPDF_PSTEP_SUGGEST`. Severity **advisory**.

## Mapping (canonical → ISO 19593-1 group)

| Canonical spot | Suggested ISO 19593-1 group |
|---|---|
| `CutContour` / `ThroughCut` | `Cutting` |
| `KissCut` | `KissCutting` |
| `Crease` | `Folding` |
| `Perforation` | `Perforating` |
| `White` | `White` |
| `Varnish` | `Varnish` |
| `VarnishFree` | `VarnishFree` |

## Detection

Run after `spot_name_normaliser` completes. For each canonical name
discovered, emit one `LPDF_PSTEP_SUGGEST` finding suggesting the
ISO 19593-1 group. The finding's details carry both the actual
spot name and the suggested ISO group so the operator can wire the
processing-step metadata once and silence the finding by adding
the appropriate `/ProcessingSteps /Group` entry.

## Output

```
Finding(
    inspection_id="LPDF_PSTEP_SUGGEST",
    severity=Severity.ADVISORY,
    message="Spot 'CutContour' should be tagged ISO 19593-1 group 'Cutting'",
    details={
        "actual_name": "CutContour",
        "canonical_name": "CutContour",
        "iso_group": "Cutting",
    },
    iso_clause="ISO 19593-1 §5.3",
    object_id="CutContour",
    object_type="spot_color",
)
```

## Read-only / scope

Read-only. Universal advisory. Silent when no recognised spots
present. Wires into the existing spot-naming pass in
`queue/tasks.py` so it runs alongside `LPDF_SPOT_NONCANONICAL`.
