---
title: "AI Regulatory Compliance"
description: "Detailed guide to regulatory compliance features: FDA, EU Food Information, GHS/CLP, and Pharmaceutical packaging."
---

# AI Regulatory Compliance

LintPDF AI inspections validate packaging artwork against major regulatory frameworks. This document covers each supported regulation, what is checked, and how findings are reported.

## FDA Nutrition Facts (21 CFR 101.9)

The FDA regulatory category validates nutrition labeling requirements for food packaging sold in the United States.

### Inspections

| Inspection ID | Description | Severity |
|---------------|-------------|----------|
| `ai.fda.nutrition_panel` | Detects and validates Nutrition Facts panel structure | Error |
| `ai.fda.nutrient_order` | Validates nutrient ordering per FDA requirements | Error |
| `ai.fda.font_sizes` | Checks minimum font size requirements (8pt body, 13pt header) | Error |
| `ai.fda.serving_size` | Validates serving size declaration format and placement | Error |
| `ai.fda.daily_value` | Checks Percent Daily Value column presence and formatting | Warning |

### What Is Checked

- Nutrition Facts panel detection and structural validation
- Nutrient ordering: Calories, Total Fat, Saturated Fat, Trans Fat, Cholesterol, Sodium, Total Carbohydrate, Dietary Fiber, Total Sugars (Added Sugars), Protein
- Font size requirements: 13pt+ header, 8pt+ body (6pt for packages under 40 sq in PDP)
- Serving size and servings per container formatting
- Daily Value percentage column alignment
- Horizontal rule weight and placement
- Footnote presence for standard format labels

### Limitations

- Does not validate nutritional values for accuracy (content correctness is the responsibility of the food manufacturer)
- Dual-column and aggregate formats are supported but may have lower confidence scores
- Supplement Facts panels are not currently supported (planned for future release)

## EU Food Information Regulation (1169/2011)

The EU FIR category validates food labeling requirements for products sold in the European Union.

### Inspections

| Inspection ID | Description | Severity |
|---------------|-------------|----------|
| `ai.eu_fir.x_height` | Validates minimum x-height for mandatory information | Error |
| `ai.eu_fir.allergen_emphasis` | Checks allergen typographic distinction | Error |
| `ai.eu_fir.nutrition_order` | Validates nutritional declaration ordering | Error |
| `ai.eu_fir.mandatory_fields` | Checks presence of all mandatory label fields | Error |

### What Is Checked

- x-height minimum: 1.2mm for standard packages, 0.9mm for packages under 80 cm²
- Allergen emphasis in ingredients list: bold, underline, or CAPITALS
- Nutritional declaration order: energy, fat, saturates, carbohydrate, sugars, protein, salt
- Energy expressed in both kJ and kcal
- Per 100g/100ml declaration
- Mandatory field presence: product name, ingredients, allergens, net quantity, date marking, storage conditions, origin (where required)

### Limitations

- Country-specific requirements beyond EU baseline are not currently validated
- Multi-language label validation checks for field presence but does not verify translation accuracy
- Organic certification mark detection is planned but not yet available

## GHS/CLP Chemical Labels (Regulation 1272/2008)

The GHS/CLP category validates hazard labeling requirements for chemical products.

### Inspections

| Inspection ID | Description | Severity |
|---------------|-------------|----------|
| `ai.ghs.pictogram_detect` | Detects and identifies GHS hazard pictograms | Error |
| `ai.ghs.pictogram_size` | Validates pictogram minimum size | Error |
| `ai.ghs.signal_word` | Checks signal word presence and correctness | Error |
| `ai.ghs.h_statements` | Validates Hazard statement presence and text | Error |
| `ai.ghs.p_statements` | Checks Precautionary statement presence | Warning |

### What Is Checked

- All 9 GHS pictogram types: GHS01 (exploding bomb), GHS02 (flame), GHS03 (flame over circle), GHS04 (gas cylinder), GHS05 (corrosion), GHS06 (skull and crossbones), GHS07 (exclamation mark), GHS08 (health hazard), GHS09 (environment)
- Pictogram minimum sizing: 1/15th of the label area, at least 1 cm²
- Signal word: "Danger" or "Warning" based on classification
- H-statement codes and text completeness
- P-statement presence appropriate to classification
- Supplier identification (name, address, telephone)
- Product identifier presence

### Limitations

- Does not validate the correctness of classification (i.e., whether the right pictograms are used for the actual chemical composition)
- Transport labels (ADR/IATA) are not currently in scope
- Multi-language H/P statement validation is supported for EN, DE, FR, ES, IT, NL

## Pharmaceutical Packaging (EU FMD & National Requirements)

The Pharma category validates packaging requirements for pharmaceutical products.

### Inspections

| Inspection ID | Description | Severity |
|---------------|-------------|----------|
| `ai.pharma.serialization_area` | Detects EU FMD 2D DataMatrix serialization area | Error |
| `ai.pharma.braille_placeholder` | Validates Braille area presence | Warning |
| `ai.pharma.font_compliance` | Checks font size for patient information | Error |

### What Is Checked

- EU Falsified Medicines Directive (2011/62/EU) serialization: 2D DataMatrix code area detection, quiet zone adequacy
- Braille rendering area on outer packaging
- Font size compliance for patient information (minimum sizes per national guidelines)
- Batch number and expiry date field presence
- Tamper evidence indicator area detection

### Limitations

- Does not validate actual serialization data content
- National-specific requirements beyond EU baseline are limited to DE, FR, UK, ES, IT
- Package insert/leaflet QRD template validation is info-level only
