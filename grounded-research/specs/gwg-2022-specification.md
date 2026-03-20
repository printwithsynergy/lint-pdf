# GWG 2022 Specification - Complete Requirements Catalog

**Document**: GWG 2022 Specification
**Format**: 7-sheet Excel workbook
**Scope**: Complete specification for packaging, print, and label production workflows

---

## Document Overview

The GWG (Good Working Group) 2022 specification defines comprehensive requirements for PDF files intended for print production across 14 distinct print segments. This specification ensures consistency, predictability, and quality in digital print workflows.

### Key Features

1. **Modular Architecture**: Separate requirement definitions that apply differently across print segments
2. **14 Print Segments**: Distinct variations covering packaging, labels, magazine printing, and digital output
3. **Severity Levels**: Requirements marked as error, warning, or ignore depending on print segment
4. **Parameterized Requirements**: Use placeholder values (e.g., <A>) that are filled in by specific print segment variants

---

## Print Segments (14 Variants)

The specification defines requirements for these 14 print segments:

### Publishing/Advertising
1. Magazine Ads CMYK
2. Magazine Ads CMYK + RGB
3. Newspaper Ads CMYK
4. Newspaper Ads CMYK + RGB

### Sheet-Fed Offset
5. SheetCMYK CMYK
6. SheetCMYK CMYK + RGB
7. SheetSpot CMYK
8. SheetSpot CMYK + RGB

### Web/Digital Offset
9. WebCMYK CMYK
10. WebCMYK CMYK + RGB
11. WebSpot CMYK
12. WebSpot CMYK + RGB
13. WebCMYKNews CMYK
14. WebCMYKNews CMYK + RGB

### Packaging/Flexibles
15. Packaging Offset
16. Packaging Gravure
17. Packaging Flexo
18. Label & Leaflet
19. Folding Carton & Corrugated Box
20. Flexible
21. Corrugated Display

### Digital/Large Format
22. Digital Print
23. Large Format Print

---

## Definitions (D0001 - D0031)

Key terminology and threshold definitions used throughout the specification:


### D0001: PDF Standard

The ISO 32000-1 standard document as published by the ISO.


### D0002: Element

A graphics object as defined in the PDF Standard (D0001), section 8.2.


### D0003: Page Element

A Visible (D0030) Element (D0002) that is not a processing step PDF object as defined in ISO 19593-1 3.1 and that does not lie completely outside the surface of the printed product, whereby the surface of the printed product is defined in ISO 19593-1 7.4.1. If the document has an OCProperties dictionary, the Element (D0002) has to be visible as defined in the default state (value of the D key in the OCProperties dictionary).


### D0004: Path Element

A type of Page Element (D0003) defined as a "path object".


### D0005: Text Element

A type of Page Element (D0003) defined as a "text object".


### D0006: Image Element

A type of Page Element (D0003) defined as "inline image object" or "image XObject".


### D0007: 1-Bit Image Element

An Image Element (D0006) containing only color channel(s) with one-bit samples.


### D0008: Continuous-Tone Image Element

An Image Element (D0006) that is not a 1-Bit Image Element (D0007).


### D0009: Image Mask Element

An Image Element (D0006) where the image dictionary contains an ImageMask (or IM for inline images) key set to true.


### D0010: White Colour

A colour defined by any of the following combinations:
- Colour space set to DeviceCMYK and colour values set to 0, 0, 0, 0.
- Colour space set to Separation and colour value set to 0.
- Colour space set to DeviceN and the value of all colorants (ignoring None colorants) set to 0.
- Colour space set to DeviceGray and colour value set to 1.


### D0011: White Fill Colour

A White Colour (D0010) set as the colour used for filling an Element (D0002).


### D0012: White Stroke Colour

A White Colour (D0010) set as the colour used for stroking an Element (D0002).


### D0013: Black Colour

A colour defined by any of the following combinations:
- Colour space set to DeviceCMYK and colour values set to 0, 0, 0, 1.
- Colour space set to Separation, with name set to Black and colour value set to 1.
- Colour space set to DeviceN with one colorant set to Black and colour value set to 1, and the value of all other colorants (ignoring None colorants) set to 0.
- Colour space set to DeviceGray and colour value set to 0.


### D0014: Black Fill Colour

A Black Colour (D0013) set as the colour used for filling an Element, where the ca value in the extended graphic state for the Element equals 1 and the blend mode is set to Normal.


### D0015: Black Stroke Colour

A Black Colour (D0013) set as the colour used for stroking an Element, where the CA value in the extended graphic state for the Element equals 1 and the blend mode is set to Normal.


### D0016: CTM

The current transformation matrix as defined in the PDF Standard (D0001) in section 8.4.1.


### D0017: Effective Line Width

Line width is defined by the line width parameter ("w") of the graphics state as defined in the PDF Standard (D0001), section 8.4.4. In general, effective line width is defined by combining the CTM (D0016) with the value of the line width parameter. 
In some cases Path Elements (D0004) may visually look like a line due to the way they are painted. Such Path Elements (D0004) are covered by this definition. See also implementation note I00004 for more details.

If, for a variant, the Scaling Factor (D0025) and/or Viewing Distance (D0026) have to be taken into account, the point size limit in the variant shall be modified using the following formula: <final line width> = (<variant line width> / <scaling factor>).


### D0018: Effective Image Resolution

A pixel per inch value, calculated by combining the values of the Width and Height keys in the image dictionary from an Image Element (D0006) with the value of the CTM (D0016). If the effective image resolution differs for width and height, the smaller of the two values applies. The unit of effective image resolution is pixels per inch (ppi).

If, for a variant, the Scaling Factor (D0025) and/or Viewing Distance (D0026) have to be taken into account, the resolution limit in the variant shall be modified using the following formula: <final resolution> = (<variant resolution> / <viewing distance>) * <scaling factor>.


### D0019: Effective Font Size

Defined by combining the font size parameter of the text state (as defined in the PDF Standard (D0001) in section 9.3.1), with the text matrix (as defined in the PDF Standard (D0001) in section 9.4.2) and the CTM (D0016). Expressed in points.

If, for a variant, the Scaling Factor (D0025) and/or Viewing Distance (D0026) have to be taken into account, the effective font size shall be modified using the following formula: <final point size> = (<variant point size> / <scaling factor>).


### D0020: Fill Overprint

An Element (D0002) uses fill overprint if the extended graphics state for it has an op key with the value true, or, if the op key is missing, an OP key with the value true.


### D0021: Stroke Overprint

An Element (D0002) uses stroke overprint if the extended graphics state for it has an OP key with the value true.


### D0022: Spot Colour Name

The second element of the array defining a Separation colour space or any of the names in the second element of a DeviceN colour space.


### D0023: Active Spot Colours

The collection of all spot colors (defined through a Separation or DeviceN colour space) used by at least one Element (D0002).


### D0024: Active Spot Colour Names

The collection of Spot colour Names (D0022) for all Active Spot Colours (D0023).


### D0025: Scaling Factor

The scaling factor is the factor with which the PDF file (the page boxes and all objects on each page) must be scaled up before being the final, printed size. A scaling factor of "1" signifies that the job is delivered at final size. A scaling factor of 48 signifies that the job must be scaled up by a factor of 48 before it's final size. Scaling factor is an absolute number, it has no measurement unit connected to it.
The PDF Standard (D0001) already defines a page-level scaling factor through the use of the UserUnit key in the page dictionary for a page. If a page in a PDF file contains a UserUnit key, its value shall be used as the scaling factor defined here. If the UserUnit key is not present, the scaling factor typically is a convention agreed upon between the sender and receiver of the file.


### D0026: Viewing Distance

Viewing distance is the average, expected distance between de final, printed artwork and the viewer. For a banner, it would be between 1m and 5m. For a billboard, it would be closer to 50m to 100m. The viewing distance is expressed in meter.


### D0027: Ink Coverage of all separations

Ink coverage is defined as the sum of all colorants (process and spot colorants) in a rendered version of all Page Elements (D0003). Rendering shall be done in accordance with the rules defined in the relevant ISO standard, as defined in D0001.


### D0028: Ink Coverage of CMYK separations

CMYK ink coverage is defined as the sum of all CMYK colorants in a rendered version of all Page Elements (D0003). Rendering shall be done in accordance with the rules defined in the relevant ISO standard, as defined in D0001.


### D0029: Product Type

The type of printed product as defined in the first column of the "Product types" sheet. Product Type is not a value specified in the PDF specification but can be communicated in a number of different ways. This specification does not specify the way Product Type is communicated, but assumes that for some variants it will be available.


### D0030: Visible

An Element (D0002) is visible if it is not completely clipped away or if it is not completely obscured by an opaque, not overprinting, Element (D0002)


### D0031: Overlapping

An Element (D0002) is overlapping if it intersects with and is in front of another Visible (D0030) Element (D0002).


---

## Requirements (R0001 - R0999)

Comprehensive requirements catalog with severity mappings across all 14 print segments.


### R0001: Base ISO standards

**Requirement Text**: A PDF file shall be compliant to the ISO standard(s): <A>. In case of (perceived) conflict, the requirements of the base ISO standards shall always take precedence over any requirements defined here.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | error |
| SheetCMYK CMYK + RGB | error |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | error |
| Large Format Print | error |


### R0002: Page scaling

**Requirement Text**: No page dictionary in the PDF file shall contain the UserUnit key.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | error |
| SheetCMYK CMYK + RGB | error |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | error |
| Large Format Print | warning |


### R0003: Visible page area

**Requirement Text**: For all pages in the PDF file, the CropBox shall coincide with the MediaBox. 

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | error |
| SheetCMYK CMYK + RGB | error |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | error |
| Large Format Print | error |


### R0004: Same page size and orientation

**Requirement Text**: The size of the TrimBox shall be the same for all pages in the PDF file. No pages in the PDF file shall be rotated through the use of the Rotate key.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | warning |
| Large Format Print | ignore |


### R0005: Empty page

**Requirement Text**: No page in the PDF file shall be completely empty. A page is considered empty if the Total Ink Coverage (D0027) is equal to zero.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | warning |


### R0006: One page

**Requirement Text**: The number of pages in the PDF file shall be exactly one (1).

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | ignore |
| SheetSpot CMYK + RGB | ignore |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | ignore |
| WebSpot CMYK + RGB | ignore |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0007: Overprinting white text

**Requirement Text**: An Overlapping (D0031) Text Element (D0005) that is set to fill, or stroke and fill, and uses a White Fill Colour (D0011), shall not use Fill Overprint (D0020). 
An Overlapping (D0031) Text Element (D0005) that is set to stroke, or stroke and fill, and uses a White Stroke Colour (D0012), shall not use Stroke Overprint (D0021).

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | error |
| SheetCMYK CMYK + RGB | error |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | error |
| Large Format Print | error |


### R0008: Overprinting white paths

**Requirement Text**: An Overlapping (D0031) Path Element (D0004) that is set to fill, or stroke and fill, and uses a White Fill Colour (D0011), shall not use Fill Overprint (D0020). 
An Overlapping (D0031) Path Element (D0004) that is set to stroke, or stroke and fill, and uses a White Stroke Colour (D0012), shall not use Stroke Overprint (D0021).

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | warning |
| Large Format Print | warning |


### R0009: Overprinting pure black text

**Requirement Text**: An Overlapping (D0031) Text Element (D0005) that is set to fill, or stroke and fill, and uses a Black Fill Colour (D0014) and has an Effective Font Size (D0019) smaller than <A> point shall use Fill Overprint (D0020).
An Overlapping (D0031) Text Element that is set to stroke, or stroke and fill, and uses a Black Stroke Colour (D0015) and has an Effective Font Size (D0019) smaller than <A> point shall use Stroke Overprint (D0021).

- If the colour space in use for either of the above rules is defined as DeviceCMYK, the value of the OPM key additionally shall be set to 1.
- If the colour space in use for the fill or stroke part of the above rules is defined as DeviceGray, that rule shall not apply at all.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | warning |


### R0010: Overprinting pure black thin lines

**Requirement Text**: An Overlapping (D0031) Path Element (D0004) that is filled, and uses Black Fill Colour (D0014), and has an Effective Line Width (D0017) less than <A>, shall use Fill Overprint (D0020).
An Overlapping (D0031) Path Element (D0004) that is stroked, and uses Black Stroke Colour (D0015), and has an Effective Line Width (D0017) less than <A>, shall use Stroke Overprint (D0021).

- If the colour space in use for either of the above rules is defined as DeviceCMYK, the value of the OPM key additionally shall be set to 1.
- If the colour space in use for the fill or stroke part of the above rules is defined as DeviceGray, that rule shall not apply at all.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0011: Overprinting pure black small text in DeviceGray

**Requirement Text**: An Overlapping (D0031) Text Element (D0005) with an Effective Font Size (D0019) less than <A> shall not have a stroke colour space of DeviceGray if it is stroked, and it shall not have a fill colour space of DeviceGray if it is filled.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | warning |


### R0012: Overprinting pure black thin lines in DeviceGray

**Requirement Text**: An Overlapping (D0031) Path Element (D0004) with an Effective Line Width (D0017) less than <A>, shall not have a stroke colour space of DeviceGray if it is stroked, and it shall not have a fill colour space of DeviceGray if it is filled.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0013: Overprinting device gray

**Requirement Text**: An Overlapping (D0031) Page Element (D0003) that is filled and has DeviceGray as fill colour space shall not use Fill Overprint (D0020).
An Overlapping (D0031) Page Element (D0003) that is stroked and has DeviceGray as stroke colour space shall not use Stroke Overprint (D0021).

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0014: Use of the Courier font

**Requirement Text**: Any Text Element (D0005) shall not use a font with the name "Courier". This requirement does not restrict the use of fonts with slightly different names such as for example "Courier New".

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0015: Rich black text

**Requirement Text**: A Visible (D0030) Text Element (D0005) that is using a fill colour space that is DeviceCMYK or DeviceN (where the DeviceN colour space has at least two process colour components, one of which being Black), shall not have a Black colour component larger than or equal to <A>, if the sum of all process colour components for that Text Element (D0005) is larger than <B>.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | warning |
| Large Format Print | ignore |


### R0016: Registration problems with small white text

**Requirement Text**: An Overlapping (D0031) Text Element (D0005) shall not have an Effective Font Size (D0019) smaller than <A> if it uses a White Fill Colour (D0011).

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | warning |
| Large Format Print | warning |


### R0017: Registration problems with small multi-channel text

**Requirement Text**: A Text Element (D0005) shall not have an Effective Font Size (D0019) smaller than <A> if more than one of its colour components have a value greater than 0.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | warning |
| Large Format Print | warning |


### R0018: Registration problems with thin white lines

**Requirement Text**: An Overlapping (D0031) Path Element (D0004) shall not have an Effective Line Width (D0017) smaller than <A> if the colour used to calculate the Effective Line Width (D0017) is a White Colour (D0010).

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | warning |
| Large Format Print | warning |


### R0019: Registration problems with thin multi-channel lines

**Requirement Text**: A Path Element (D0004) shall not have an Effective Line Width (D0017) smaller than <A> if more than 1 of the colour components of the colour space used to calculate the Effective Line Width (D0017) have a value greater than 0.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | warning |
| Large Format Print | warning |


### R0020: Use of spot colours

**Requirement Text**: A PDF file shall have no more than <A> different names in the Active Spot Colour Names (D0024).

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | error |
| SheetCMYK CMYK + RGB | error |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | ignore |
| Packaging Gravure | ignore |
| Packaging Flexo | ignore |
| Label & Leaflet | ignore |
| Folding Carton & Corrugated Box | ignore |
| Flexible | ignore |
| Corrugated Display | ignore |
| Digital Print | warning |
| Large Format Print | ignore |


### R0021: Spot colours with different suffixes

**Requirement Text**: The Active Spot Colour Names (D0024) collection in a PDF shall not contain names that are different but equivalent. Equivalence is considered for those spot colours where the name of the spot colour ends in a SPACE character (20h) followed by a single one of these character combinations: C, CP, E, K, M, N, U, UP, Z, CV, CVU, CVC, HC, PC, TC, TCX, TP, TPX, XGC, EC.

For all spot colour names that comply with the above requirement, a case-insensitive string comparison is done on the string consisting of all characters before the last SPACE character identified by the above requirement. String equality is then identical to spot colour name equivalence.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0022: Case-sensitive spot colour names

**Requirement Text**: The Active Spot Colour Names (D0024) collection in a PDF shall not contain names that are only different in their capitalization or that are canonically equivalent in Unicode. Canonically equivalent means that the unicode string would be identical after decomposition and/or precomposition.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0023: Different spot colours that are visually identical

**Requirement Text**: The Active Spot Colours (D0023) in a PDF file shall not contain spot colours that have the same tintTransform and alternateSpace but different names. In evaluating equivalence, PDF objects shall be compared rather than the computational result of the use of those objects, but the difference between direct or indirect objects shall be ignored.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0024: Registration colour

**Requirement Text**: No Page Element (D0003) shall use a Spot Colour Name (D0022) equal to "All".

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | warning |
| Large Format Print | ignore |


### R0025: Average ink coverage of all separations

**Requirement Text**: Ink coverage of all separations (D00027) shall not exceed the average value <A>, within any square area with side <B>.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | ignore |
| SheetSpot CMYK + RGB | ignore |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | ignore |
| WebSpot CMYK + RGB | ignore |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0026: Average ink coverage of CMYK separations

**Requirement Text**: Ink coverage of CMYK separations (D00028) shall not exceed the average value <A>, within any square area with side <B>.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | warning |
| Magazine Ads CMYK + RGB | warning |
| Newspaper Ads CMYK | warning |
| Newspaper Ads CMYK + RGB | warning |
| SheetCMYK CMYK | warning |
| SheetCMYK CMYK + RGB | warning |
| SheetSpot CMYK | warning |
| SheetSpot CMYK + RGB | warning |
| WebCMYK CMYK | warning |
| WebCMYK CMYK + RGB | warning |
| WebSpot CMYK | warning |
| WebSpot CMYK + RGB | warning |
| WebCMYKNews CMYK | warning |
| WebCMYKNews CMYK + RGB | warning |
| Packaging Offset | ignore |
| Packaging Gravure | ignore |
| Packaging Flexo | ignore |
| Label & Leaflet | ignore |
| Folding Carton & Corrugated Box | ignore |
| Flexible | ignore |
| Corrugated Display | ignore |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0027: Early binding mode

**Requirement Text**: No Page Element (D0003) shall use the following colour spaces as intended or alternate colour space:
- DeviceRGB
- CalRGB
- CalGray
- ICCBased (ICC based grayscale, RGB, Lab and CMYK)

No Page Element (D0003) shall use the following colour space as an intended colour space:
- Lab

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | error |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | ignore |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | ignore |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0028: Intermediate binding mode

**Requirement Text**: Page Elements (D0003) that are Image Elements (D0006) but not Image Mask Elements (D0009), shall not use the following colour spaces as intended colour space:
- DeviceRGB
- ICCBasedGray
- CalGray
- ICCBasedCMYK

Page Elements (D0003) that are not Image Elements (D0006), or that are Image Mask Elements (D0009), shall not use the following colour space as an intended colour space:
- DeviceRGB
- CalRGB
- CalGray
- ICCBased (ICC based grayscale, RGB, Lab and CMYK)
- Lab

Page Elements (D0003) shall not use the following colour space as an alternate colour space:
- DeviceRGB
- ICCBasedGray
- CalGray
- ICCBasedCMYK

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | error |
| SheetSpot CMYK | ignore |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | ignore |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | ignore |
| Packaging Gravure | ignore |
| Packaging Flexo | ignore |
| Label & Leaflet | ignore |
| Folding Carton & Corrugated Box | ignore |
| Flexible | ignore |
| Corrugated Display | ignore |
| Digital Print | error |
| Large Format Print | ignore |


### R0029: Late binding mode

**Requirement Text**: Page Elements (D0003) that are Image Elements (D0006) but not Image Mask Elements (D0009), shall not use the following colour spaces as intended colour space:
- DeviceRGB
- ICCBasedGray
- CalGray

Page Elements (D0003) that are not Image Elements (D0006), or that are Image Mask Elements (D0009), shall not use the following colour space as an intended colour space:
- DeviceRGB
- CalRGB
- CalGray
- ICCbasedCMYK
- ICCbasedGray

Page Elements (D0003) shall not use the following colour space as an alternate colour space:
- DeviceRGB
- ICCBasedGray
- CalGray

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | ignore |
| SheetSpot CMYK + RGB | ignore |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | ignore |
| WebSpot CMYK + RGB | ignore |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | ignore |
| Packaging Gravure | ignore |
| Packaging Flexo | ignore |
| Label & Leaflet | ignore |
| Folding Carton & Corrugated Box | ignore |
| Flexible | ignore |
| Corrugated Display | ignore |
| Digital Print | ignore |
| Large Format Print | error |


### R0030: Transparency blend colour space

**Requirement Text**: In a transparency group attributes dictionary, if the CS key is present, it shall have the value DeviceCMYK. As an exception to this rule, if the transparency group attributes dictionary is the value of the G key in a Luminosity sub-type soft mask dictionary, the value of the CS key shall either be DeviceCMYK or DeviceGray.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | error |
| SheetCMYK CMYK + RGB | error |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | error |
| Large Format Print | error |


### R0031: Image resolution for grayscale and colour images

**Requirement Text**: The Effective Image Resolution (D0018) of a Continuous-Tone Image Element (D0008) not covered by the requirement on Rasterized pages (R0033), shall be greater than <A> for images with a width or height greater than 16 pixels.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error
warning |
| Magazine Ads CMYK + RGB | error
warning |
| Newspaper Ads CMYK | error
warning |
| Newspaper Ads CMYK + RGB | error
warning |
| SheetCMYK CMYK | error
warning |
| SheetCMYK CMYK + RGB | error
warning |
| SheetSpot CMYK | error
warning |
| SheetSpot CMYK + RGB | error
warning |
| WebCMYK CMYK | error
warning |
| WebCMYK CMYK + RGB | error
warning |
| WebSpot CMYK | error
warning |
| WebSpot CMYK + RGB | error
warning |
| WebCMYKNews CMYK | error
warning |
| WebCMYKNews CMYK + RGB | error
warning |
| Packaging Offset | error
warning |
| Packaging Gravure | error
warning |
| Packaging Flexo | error
warning |
| Label & Leaflet | error
warning |
| Folding Carton & Corrugated Box | error
warning |
| Flexible | error
warning |
| Corrugated Display | error
warning |
| Digital Print | error
warning |
| Large Format Print | error
warning |


### R0032: Image resolution for 1-bit images

**Requirement Text**: The Effective Image Resolution (D0018) of a 1-Bit Image Element (D0007), shall be greater than <A> for images with a width or height greater than 16 pixels.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error
warning |
| Magazine Ads CMYK + RGB | error
warning |
| Newspaper Ads CMYK | error
warning |
| Newspaper Ads CMYK + RGB | error
warning |
| SheetCMYK CMYK | error
warning |
| SheetCMYK CMYK + RGB | error
warning |
| SheetSpot CMYK | error
warning |
| SheetSpot CMYK + RGB | error
warning |
| WebCMYK CMYK | error
warning |
| WebCMYK CMYK + RGB | error
warning |
| WebSpot CMYK | error
warning |
| WebSpot CMYK + RGB | error
warning |
| WebCMYKNews CMYK | error
warning |
| WebCMYKNews CMYK + RGB | error
warning |
| Packaging Offset | error
warning |
| Packaging Gravure | error
warning |
| Packaging Flexo | error
warning |
| Label & Leaflet | error
warning |
| Folding Carton & Corrugated Box | error
warning |
| Flexible | error
warning |
| Corrugated Display | error
warning |
| Digital Print | error
warning |
| Large Format Print | error
warning |


### R0033: Rasterized pages

**Requirement Text**: If a page in a PDF file contains only one Page Element (D0003), which is a Continuous-Tone Image Element (D0008) that covers the TrimBox, its Effective Image Resolution (D0018) shall be greater than <A>.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error
warning |
| Magazine Ads CMYK + RGB | error
warning |
| Newspaper Ads CMYK | error
warning |
| Newspaper Ads CMYK + RGB | error
warning |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | ignore |
| SheetSpot CMYK + RGB | ignore |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | ignore |
| WebSpot CMYK + RGB | ignore |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | error
warning |
| Packaging Gravure | error
warning |
| Packaging Flexo | error
warning |
| Label & Leaflet | error
warning |
| Folding Carton & Corrugated Box | error
warning |
| Flexible | error
warning |
| Corrugated Display | error
warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0034: Optional content

**Requirement Text**: If the document catalog dictionary contains an optional content properties dictionary as the value of the OCProperties key, the optional content properties dictionary shall not contain a Configs key.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | ignore |
| SheetSpot CMYK + RGB | ignore |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | ignore |
| WebSpot CMYK + RGB | ignore |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | warning |
| Packaging Gravure | warning |
| Packaging Flexo | warning |
| Label & Leaflet | warning |
| Folding Carton & Corrugated Box | warning |
| Flexible | warning |
| Corrugated Display | warning |
| Digital Print | ignore |
| Large Format Print | ignore |


### R0035: Output intent colour space

**Requirement Text**: The colour space of the ICC Profile that is the destination profile in PDF/X output intent object(s), shall be CMYK.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | error |
| Magazine Ads CMYK + RGB | error |
| Newspaper Ads CMYK | error |
| Newspaper Ads CMYK + RGB | error |
| SheetCMYK CMYK | error |
| SheetCMYK CMYK + RGB | error |
| SheetSpot CMYK | error |
| SheetSpot CMYK + RGB | error |
| WebCMYK CMYK | error |
| WebCMYK CMYK + RGB | error |
| WebSpot CMYK | error |
| WebSpot CMYK + RGB | error |
| WebCMYKNews CMYK | error |
| WebCMYKNews CMYK + RGB | error |
| Packaging Offset | error |
| Packaging Gravure | error |
| Packaging Flexo | error |
| Label & Leaflet | error |
| Folding Carton & Corrugated Box | error |
| Flexible | error |
| Corrugated Display | error |
| Digital Print | error |
| Large Format Print | error |


### R0036: Hidden optional content

**Requirement Text**: If the document contains an optional content properties dictionary as the value of the D entry in the OCProperties entry of the document catalog dictionary, it shall be configured so that the initial state of all optional content groups it references is ON.

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | ignore |
| SheetSpot CMYK + RGB | ignore |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | ignore |
| WebSpot CMYK + RGB | ignore |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | ignore |
| Packaging Gravure | ignore |
| Packaging Flexo | ignore |
| Label & Leaflet | ignore |
| Folding Carton & Corrugated Box | ignore |
| Flexible | ignore |
| Corrugated Display | ignore |
| Digital Print | ignore |
| Large Format Print | error |


### R0037: Scaling factor and viewing distance

**Requirement Text**: If the variant table contains a value of "Warning" or "Error" for this requirement, the Scaling Factor (D0025) and Viewing Distance (D0026) will be taken into account in the defintions for Effective Line Width (D0017), Effective Image Resolution (D0018), and Effective Font Size (D0019).

**Print Segment Mapping**:

| Print Segment | Severity |
|---|---|
| Magazine Ads CMYK | ignore |
| Magazine Ads CMYK + RGB | ignore |
| Newspaper Ads CMYK | ignore |
| Newspaper Ads CMYK + RGB | ignore |
| SheetCMYK CMYK | ignore |
| SheetCMYK CMYK + RGB | ignore |
| SheetSpot CMYK | ignore |
| SheetSpot CMYK + RGB | ignore |
| WebCMYK CMYK | ignore |
| WebCMYK CMYK + RGB | ignore |
| WebSpot CMYK | ignore |
| WebSpot CMYK + RGB | ignore |
| WebCMYKNews CMYK | ignore |
| WebCMYKNews CMYK + RGB | ignore |
| Packaging Offset | ignore |
| Packaging Gravure | ignore |
| Packaging Flexo | ignore |
| Label & Leaflet | ignore |
| Folding Carton & Corrugated Box | ignore |
| Flexible | ignore |
| Corrugated Display | ignore |
| Digital Print | ignore |
| Large Format Print | error |


---

## Implementation Notes (I00001+)

Guidance for implementers of the GWG 2022 specification:


### I00001: Checking XMP

When performing XMP validation, it shall only be done on document level XMP and not on the XMP referenced from other locations in the PDF document.


### I00003: Spot colour names

The special colorant names Cyan, Magenta, Yellow, Black, All and None refer to special colorants and do not count as spot colour names. If the special colorant name "None" is used, its tint value shall not be taken into account (it shall be considered zero (0)).


### I00004: Effective line width for thin rectangles

The PDF Standard (D0001) allows creating Path Elements (D0004) using the line or rectangle ("l" or "re") path construction operators (as defined in the PDF Standard (D0001), section 8.5.2), that visually resemble lines because they have a rectangular shape with a small width or height. For such Path Elements (D0004), an effective line width has to be calculated as well, in line with the properties of those objects (whether the objects are filled or stroked, the colours of the fill and stroke and other properties of the objects may contribute to how the effective line width is calculated).


### I00005: Calculations and rounding

When calculations are done, they shall be done using the highest possible precision. Any rounding will be done only after all calculations, when the resulting value needs to be used.


### I00006: Invisible objects

Some requirements in this specification take into account only visible (D0030) Page Elements (D0003). It should be noted that this doesn't mean that preflight vendors have to be able to detect the difference between visible and invisible elements. Rather it means that as a vendor you have the option to make preflight more accurate if you are capable to distinguish between the two types of Page Elements (D0003).


---

## Severity Levels

The GWG 2022 specification uses three severity levels for requirements:

- **error**: Requirement violation is a critical error. The PDF should not proceed to print.
- **warning**: Requirement violation is a warning. The PDF can proceed but may have quality issues.
- **ignore**: Requirement is not applicable for this print segment. Violations are ignored.

---

## Print Segment Categories

### Publishing & Advertising
**Magazine Ads**: For advertisements in magazine environments (CMYK or CMYK+RGB)
**Newspaper Ads**: For advertisements in newspaper environments (CMYK or CMYK+RGB)

### Sheet-Fed Offset
**SheetCMYK**: Color separation (CMYK or CMYK+RGB) for sheet-fed offset presses
**SheetSpot**: Spot color separation (CMYK or CMYK+RGB) for sheet-fed offset presses

### Web Offset
**WebCMYK**: Color separation (CMYK or CMYK+RGB) for web offset presses
**WebSpot**: Spot color separation (CMYK or CMYK+RGB) for web offset presses
**WebCMYKNews**: News print variant with CMYK separation

### Packaging & Labels
**Offset**: Traditional offset printing for packaging
**Gravure**: Gravure printing process for flexible packaging
**Flexo**: Flexographic printing for flexible materials
**Label & Leaflet**: Label and leaflet production
**Folding Carton & Corrugated Box**: Rigid packaging formats
**Flexible**: Flexible packaging materials
**Corrugated Display**: Display and POP materials

### Digital & Large Format
**Digital Print**: For digital printing processes
**Large Format Print**: For wide-format printing (banners, signage, etc.)

---

## Key Requirements by Category

### Page Layout & Structure
- **R0001**: Base ISO standards compliance
- **R0002**: No page scaling (UserUnit key)
- **R0003**: Visible page area (CropBox = MediaBox)
- **R0004**: Same page size and orientation for all pages
- **R0005**: No empty pages
- **R0006**: Single page requirement (variant dependent)

### Color & Overprinting
- **R0007**: Overprinting white text rules
- **R0008**: Overprinting white paths
- **R0009**: Overprinting pure black text with font size thresholds
- **R0010**: Overprinting pure black thin lines
- **R0011-R0019**: Advanced color management and ink specifications

### Processing & Workflow
- **R1000+**: Processing steps for structural, die-cutting, and finishing operations

### CxF (Spectral Color Data)
- **R2000+**: CxF specification requirements for accurate color specification

---

## Source Document Reference

- **File**: GWG 2022.xlsx
- **Sheets**: 7 (Legend, Definitions, Requirements, Processing Steps, Product Types, Implementation Notes, Variants)
- **Extraction Date**: 2026-03-11

---

## Grounded Integration Notes

### Mapping to Grounded Inspection IDs

All GWG 2022 requirements should be mapped to Grounded Inspection IDs using the pattern:

- **GWG-001** to **GWG-039**: Core requirements (R0001-R0039)
- **GWG-PS-001+**: Processing step requirements (R1000+)
- **GWG-CXF-001+**: CxF requirements (R2000+)

### Print Segment Context

When implementing GWG checks, the print segment context is critical:
- Same requirement ID can have different severity levels
- Some requirements only apply to specific print segments
- The same PDF may pass for one segment but fail for another

### Implementation Priority

Based on adoption across print segments:
1. **High Priority**: Requirements applied as 'error' across 18+ print segments
2. **Medium Priority**: Requirements with mixed severity levels
3. **Low Priority**: Requirements applied as 'ignore' or warning for most segments

