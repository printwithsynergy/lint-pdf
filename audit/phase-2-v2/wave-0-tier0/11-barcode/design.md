# Tier-0 Batch 11 — Barcode predicates

**Wave:** 0 (Tier-0 primitives) — final batch
**Category:** barcode.*
**Primitive count:** 9
**EM estimate:** 0.20
**Date:** 2026-04-25

Per universe enumeration §4.11.

## Primitives (all under `barcode.*` namespace)

| Primitive | Inputs | Returns |
|-----------|--------|---------|
| `is_barcode(obj)` | object event / dict | bool — has barcode classification |
| `symbology(obj)` | object | str ("EAN-13", "Code128", "QR", "Datamatrix", "UPC-A", "ITF-14") or None |
| `is_1d(obj)` | object | bool — linear barcode |
| `is_2d(obj)` | object | bool — 2D matrix barcode |
| `narrow_bar_width(obj)` | object | float (pt) — minimum bar width / X-dimension |
| `quiet_zone(obj)` | object | tuple[float,float,float,float] (pt) or None |
| `is_decodable(obj)` | object | bool — decoder verified scan |
| `decoded_value(obj)` | object | str or None |
| `gs1_compliant(obj)` | object | bool — GS1 application identifier check |

## Module

`packages/engine/src/lintpdf/primitives/barcode.py`

## POC migration

`barcode.py` analyzer hand-rolls symbology detection; flip to `barcode_p.symbology()` + `barcode_p.is_2d()` predicates.

## Read-only / no-stub

- ✓ Pure functions; no PDF mutation; ruff + mypy clean
