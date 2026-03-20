# PDF/UA Specifications and Technical Supplements
## Preflight-Relevant Requirements Analysis

**Analysis Date:** 2026-03-11
**Documents Analyzed:** 13

## Overview

This document consolidates preflight validation requirements extracted from PDF/UA specifications and technical supplements. Requirements are categorized by type to support implementation in a preflight validation engine.

## Table of Contents

- [PDF/UA-1: Universal Accessibility](#iso-14289-12014)
- [PDF/UA-2: Universal Accessibility](#iso-14289-22024)
- [Structure Namespace and Role Mapping](#iso-ts-320052023)
- [PDF/UA Reference - Logical Structure](#iso-ts-320012022)
- [PDF/UA Reference - Artifacts & Role Mapping](#iso-ts-320022022)
- [PDF/UA Reference - Marked Content](#iso-ts-320032023)
- [PDF/UA Reference - Conformance & Testing](#iso-ts-320042024)
- [Well-Tagged PDF Specification](#wtpdf-1.0)
- [Tagged PDF Best Practices](#best-practice-guide)
- [PDF Metadata Declarations](#pdf-declarations)
- [Best Practice Contents](#pdf-2.0-an001)
- [Associated Files](#pdf-2.0-an002)
- [Object Metadata Locations](#pdf-2.0-an003)

---

## Consolidated Preflight Requirements

### Purpose and Scope

This analysis extracts preflight-relevant requirements from 13 key PDF/UA and accessibility-related documents:

**Core Standards:**
- ISO 14289-1:2014 (PDF/UA-1) - Foundation for PDF accessibility using ISO 32000-1
- ISO 14289-2:2024 (PDF/UA-2) - Extended specification using ISO 32000-2

**Technical Supplements & Reference Implementations:**
- ISO TS 32001:2022 - Logical structure implementation
- ISO TS 32002:2022 - Artifacts and role mapping
- ISO TS 32003:2023 - Marked content handling
- ISO TS 32004:2024 - Conformance and testing procedures
- ISO TS 32005:2023 - Structure namespace and role mapping

**Best Practices and Guidelines:**
- Well-Tagged PDF (WTPDF) 1.0 - Specification for well-tagged PDFs
- Tagged PDF Best Practice Guide - Industry guidelines
- PDF Declarations - Metadata declaration specifications
- PDF 2.0 Annexes - Associated files, best practice contents, metadata locations

### Categorization Approach

Requirements are extracted and organized into six categories:

| Category | Purpose | Applicability |
|----------|---------|----------------|
| **Must-Have** | Critical requirements for PDF/UA conformance | All PDF/UA files |
| **Prohibited** | Features that must NOT appear in conforming files | Rejection criteria |
| **Recommended** | Best practice features for enhanced accessibility | Quality improvements |
| **Tag Requirements** | Specific logical structure and tagging rules | Document structure validation |
| **Metadata Requirements** | XMP and document metadata rules | Metadata validation |
| **Validation Rules** | Specific checks for preflight engines | Automated detection |


### Critical Requirements (Must-Have)

These requirements MUST be satisfied for PDF/UA conformance:

1. (ISO 32000-2:2020, 7.12). It shall be included as an array entry under the prefix.

2. (except as exempted by 5.2) shall match the descriptions and follow the inclusion rules specified in

3. (except as exempted in 5.2), those elements shall conform to the requirements defined in Clause 5 and

4. 13 When zero, indicates that a PDF MAC token is requiredA tuot hbeC opdreesent in all revisions of

5. 32000-1, Table 322) are required that map these custom structure types (e.g., “<DataTable>”) to

6. 7.12) with a prefix name of . This shall contain a developer extensions dictionary in accordance

7. A conforming file shall adhere to all file format provisions in Clause 7.

8. A conforming file shall contain PDF/UA version identification as defined in Clause 5.

9. A file conforming with this document shall identify conformance with at least one of the

10. A file declaring conformance with the conformance level for accessibility shall conform to all

11. A file declaring conformance with the conformance level for reuse shall conform to all the

12. Accordingly, PDF 2.0 processors must be prepared to encounter metadata almost anywhere

13. All rights reserved. Unless otherwise specified, or required in the context of its implementation, no part of this publication may

14. As specified in the following subclauses, applicable conformance level(s) shall be indicated using

15. AuthCode (Required if the document is encrypted with user access permissions bit 13 zero.

16. Catalog Table 29 (Optional; PDF 1.4; shall be an indirect reference) A metadata

17. Conforming files shall adhere to all requirements of ISO 32000-1:2008 as modified by this part of

18. Document Table 162 (Optional; PDF 2.0; shall be an indirect reference) A metadata

19. Document Table 409 (Optional; PDF 2.0; shall be an indirect reference) A metadata

20. Ed448 SHAKE256 Message digests shall be calculated using the fixed length id-shake256 message

21. Encrypted PDF documents making use of the extension specified in this document shall conform to

22. Files conforming to the conformance level for accessibility shall include a PDF Declaration with

23. Files conforming to the conformance level for reuse shall include a PDF Declaration with the URI

24. ICC Profile Table 65 (Optional; PDF 1.4) A metadata stream that shall contain

25. In many important use cases - electronic invoices being the classic example - data must be

26. In order to more precisely specify how message digest algorithms shall be used with elliptic curves, the

27. Internal (Required) Four-digit year of the date of

28. Internal (Required) PDF/UA part identifier

29. Internal Required PDF/UA version identifier

30. KDFSalt (Conditionally required; shall be a direct object)

31. KDFSalt This entry is required in documents that make use of PDF MAC.

32. NOTE 2 This restriction implies that ECDSA signature values are required to be represented using the DER-

33. NOTE 3 Conformance with ISO/TS 32005 is required because, although ISO 32000-2 did not deprecate

34. NOTE A conforming file is not obligated to use any PDF feature other than those explicitly required by

35. PDF 2.0 elements shall explicitly declare their namespace using the PDF 2.0 namespace and may contain

36. PDF documents conforming to this document shall be versioned as PDF 2.0 using either the header or

37. PDF documents using enhaInScOem_ ents described in this document shall include in their document

38. PDF documents using enhancements described in this document shall include in their document

39. Page Table 31 (Optional; PDF 1.4) A metadata stream that shall contain

40. Part (DPart) stream that shall contain metadata for this document part.

41. Shall be a direct object; PDF 2.0)

42. TIShOe_ developer extensions dictionary described in Table 1 shall be included in the document’s extensions

43. Text (page content, metadata, annotations) must be mapped to Unicode in order to be accessible

44. The Identification schema namespace URI is http://www.aiim.org/pdfua/ns/id/. The required schema

45. The PDF/UA version and conformance of a file shall be specified in the metadata stream that is the value

46. The PDF/UA version of a file shall be specified in the value of the entry in the document catalog

47. The crypt filter shall use AES-GCM as specified in NIST SP 800-38D, with the following

48. The developer extensions dictionary in Table 1 shall be part of the document’s extensions dictionary

49. The following clauses clarify what “the metadata shall be attached as closely as possible to

50. The key can take three states: ON, OFF and Default (note that these must be exactly as shown

51. The principle is applicable to any case in which a record must be processed by machines

52. The unique PDF 1.7 elements that are a grouping element type are defined in Table 2 and shall be the

53. The value of pdfuaid: rev shall be for PDF files conforming with this document.

54. The value of shall be the part number of this International Standard to which the file

55. WCAG 2.2[5]. If such an embedded file is a PDF file, it shall conform to ISO 14289 and/or to this

56. When such a PDF declaration is present, it shall conform to the requirements of the PDF Declarations

57. When using the ECDSA elliptic curves in Table 1 for signing data, these shall be used in accordance with

58. When using the Ed25519 EdDSA elliptic curve algorithm, the message digest shall be computed using the SHA512

59. a file shall adhere to all requirements of ISO 32000-2;

60. a file shall adhere to all requirements of ISO/TS 32005;

61. algorithm shall be used to compute both the digest of the SignedData encapContentInfo eContent and

62. authenticates all individual ciphertexts, but a separate mechanism is required to achieve document-

63. borders, sender and receiver must agree on the format and representation of the data. A

64. but must also be readable by humans. An example would be of software license

65. default standard structure namespace, then that document shall conform to the requirements specified

66. desktop computers must take into account that these viewers (at this time) typically do

67. dictionary entries defined below shall be direct objects, with the exception of the entry.

68. dictionary in accordance with ISO 32000-2:2020, 7.12. It shall be included as an array entry under the

69. distinguish “real” content from artifacts. PDF/UA also makes it clear that artifacts must be

70. element has been changed from a shall to a should, and additional normative text added to explicate

71. elliptic curve algorithm, the message digest shall be computed using the SHAKE256 message digest algorithm with OID id-

72. embedded files when unzipped; a workflow must be established in order to keep that

73. encryption dictionary is 6, the algorithm described in ISO/TS 32003 shall be used”.

74. entry is required to contain one of the values defined in PDF 2.0: Source, Data,

75. id-shake256 object identifier (OID) in section 2.3 of RFC 8419 shall be used.

76. integer When is , the key shall be specified in the same manner

77. keys used in PDF signatures shall specify curve parameters (ECParameters) for the subject’s public key

78. namespace, then the requirements of ISO 32000-1 shall be used for their inclusion. In such cases, the

79. notice of (a) patent(s) which may be required to implement this document. However, implementers are

80. number (Required) 6 - (ISO/TS 320A0E3S)V T4he security handler defines the use of encryption

81. number (Required) 7 (ISO/TS 3R2003) if the document is encrypted with a value of 6.

82. objectively verifiable standards, e.g. WCAG 2.2. If such an embedded file is a PDF file, it shall conform

83. of tagged PDF files required for an accessible experience. Other Best Practice Guides will address

84. of the containing file, shall be accessible according to objectively verifiable standards, e.g.,

85. pages must each be linked to the logical structure, in the right order, without restarting the

86. patent(s) which may be required to implement this document. However, implementers are cautioned that

87. pdfd:conformsTo URI (Required) A property containing a URI specifying

88. pdfd:declarations Unordered array (Required) An unordered array of PDF

89. processor must agree on where metadata is present in the often-complex internal PDF

90. regarding the metadata’s location is required. However, since some objects in PDF distribute

91. required computer hardware and/or operating systems;

92. required schema namespace prefix is .

93. shall use the PDF 2.0 namespace and follow the inclusion rules defined in ISO 32000-2:2020, Annex L,

94. specification. Such claim of conformance shall take the form described in Table 1.

95. stream that shall contain metadata for the document.

96. that , then shall be used to subdivide that into the described (captioned)

97. the Metadata entry, the metadata shall be attached as closely as possible to

98. to a part, then the value of shall be the amendment number and year, separated by a colon.

99. when the Scope element is required;

100. with a prefix name of . This shall contain a developer extensions dictionary in accordance with

101. — The 32-byte crypt filter encryption key shall be used as the key for AES-GCM. Hence, the same key

102. — a file shall adhere to all requirements of ISO 32000-2;

103. — a file shall adhere to all requirements of ISO/TS 32005;

104. — an embedded file, if necessary to the understanding of the document, shall be accessible according to

105. — required computer hardware and/or operating system

106. — required computer hardware and/or operating system.

107. — required computer hardware and/or operating systems.

108. — required computer hardware and/or operating systems;

109. “Content shall be marked in the structure tree

110. • a MIME type (as defined in RFC 8118) must be specified in the Subtype entry of the

111. • if the (recommended) Params entry is present, it shall specify the latest

112. ◼ Heading content must be tagged with the correct structure element (<H1>–<H6>), to

113. ◼ References for footnotes must be tagged to reflect all the appropriate semantics, e.g.

114. ◼ The document level XMP metadata must contain a Title (dc:title) (see PDF/UA-1, 8.11,

115. ◼ The document level XMP metadata must include the PDF/UA “flag” (see Annex A).

116. ◼ The document’s View property must be set to display the Title (not the file name) (see

117. ◼ “shall” = required (to avoid confusion with the specifications, this term is not used in this

### Prohibited Features (Must-Not-Have)

These features MUST NOT be present:

1. 14.8.2.2.2) shall not be tagged in the structure tree.

2. A CMap shall not reference any other CMap except those listed in ISO 32000-2:2020, Table 116.

3. ByteRange (Conditionally required; shall not be an indirect reference)

4. CMS unauthenticated attributes shall not be used; the field shall be absent.

5. Conforming files shall use the explicitly numbered heading structure types ( - ) and shall not use the

6. Conforming files shall use the explicitly numbered heading structure types (H1-Hn) and shall not

7. Dynamic XFA forms shall not be used in files conforming to this International Standard. To determine

8. Flickering, blinking, or flashing shall not be used (WCAG 2.0, Guideline 2.3).

9. If MA Cis , this entry shall not be present.

10. If is , this entry shall not be present.

11. In addition, all non-symbolic TrueType fonts shall not define a Differences array unless all the

12. In cases where ruby typesetting is used for other purposes, the Ruby structure element shall not

13. In cases where ruby typesetting is used for other purposes, the structure Aelseimdeent shall not be used.

14. Information shall not be conveyed by contrast, colour, format or layout, or by combinations thereof,

15. MAC (Conditionally required; shall not be an indirect reference) MAC-

16. MACLocation (Required; shall not be an indirect reference)

17. Note standard structure type shall not be present in conforming files.

18. Single user only, copying and networking prohibited.

19. Standard tags defined in ISO 32000-1:2008, 14.8.4, shall not be remapped.

20. Symbolic TrueType fonts shall not contain an Encoding entry in the font dictionary. The

21. The Warichu structure element shall not be used for content that is not typeset as warichu.

22. The key shall not appear in any optional content configuration dictionary.

23. The structure element shall not be used for content that is not typeset as warichu.

24. The version number of a file may be any value from 1.0 to 1.7, and the value shall not be used in

25. Titles shall be identified by the Title standard structure type and shall not be identified as a

26. Titles shall be identified by the standard structure type and shall not be identified as a heading.

27. Within a given explicitly provided namespace, structure types shall not be role mapped to other

28. Within a given explicitly provided namespace, structure types shall not be role mapped to other structure

29. a role is specified, it shall not contradict the semantic intent of the structure element to which it

30. and specifiedCurve options shall not be used.

31. approximates the intended labelling scheme; in such cases the value None shall not be used.

32. database available at www.iso.org/patents. ISO shall not be held responsible for identifying any or all

33. in strict numerical order and shall not skip an intervening heading level. is permissible,

34. is , this entry shall not be present.

35. labelling scheme; in such caseLsI the value shall not be used. Lbl

36. namespace and the PDF 2.0 namespace. PDF 1.7 elements and PDF 2.0 elements shall not have child or

37. other numbering system, and shall not use numerical separators.

38. patent rights. ISO shall not be held responsible for identifying any or all such patent rights. Details of

39. represented by a single semantic structure element with intrinsic semantics shall not be

40. semantic structure element with intrinsic semantics shall not be represented by several such structure

41. shall not occur unless the parent element is used as a grouping level element

42. shall use the letter followed by Arabic numerals without intervening whitespace, shall not use any

43. specified, it shall not contradict the semantic intent of the structure element to which it applies. Part

44. standard structure type shall not be pNroetseent in conforming files.

45. the subject of patent rights. The PDF Association shall not be held responsible for

46. use of namespaces shall not be required and those structure elements are exempt from the provisions

47. www.iso.org/patents. ISO shall not be held responsible for identifying any or all such patent rights.

### Recommended Features

These features are recommended:

1. (e.g. a fragment of text in the of a list item) should not bLe Beondclyosed in a .

2. 14.3.2), the Note should be understood as meaning that:

3. 14.8.4.3.2. The key in ISO 32000-1:2008, 14.7.2, Table 323 should be used to denote document sections.

4. A document should include a document outline that matches the reading order and level of navigational

5. All information conveyed with sound should also be available without sound.

6. Any feedback or questions on this document should be directed to the user’s national standards body. A

7. Developers of indexing software for search engines should consider that a truly complete

8. Exactly one attribute of type AuthenticatedData should be present, as specified in RFC 8933:2020,

9. If appropriate to the content, the attributes described in Table 2 should appear on an FENote

10. If appropriate to the content, the attributes described in Table 3 should appear on an structure

11. If present, the entries in the number tree (ISO 32000-1:2008, 7.7.2, Table 28) should be

12. If the table of contents uses link annotations it is recommended to use <Link> structure elements

13. Irrespective of the definitions in PDF 1.7, it is recommended that processors expect to encounter

14. It is recommended that <TOC> / <TOCI> structure element types be used for all types of tables of

15. It is recommended that quoted content be presented such that a consumer can distinguish

16. Metadata for associated files should be located in the respective file specification

17. Metadata for optional content (layers) should be located in the respective optional

18. Metadata for structure elements should be located in the corresponding structure

19. PDF files including PDF Declarations should include an XMP extension schema for PDF/A,

20. Preservation institutions should be aware that PDF files may include arbitrary embedded

21. Processors are recommended to be prepared to encounter <Caption> elements associated with

22. SVG or WOFF format to Type 3 fonts in PDF. The metadata associated with such fonts should

23. Structure elements of type TH should have a Scope attribute. If the table’s structure is not determinable

24. Sub should be used to identify semantic subdivisions within a block-level element.

25. The generic heading (ISO 32000-1:2008, Tables 334 and 335) should be used in strongly structured

26. The quoted text should be contained inline within a single block-level unit of content. This

27. Their use is therefore only recommended in closed environments.

28. This document summarizes exactly where PDF creators should add XMP metadata to PDF

29. To adequately enable users to navigate larger documents it is strongly recommended that

30. To maximize robustness and interoperability, Associated Files should be embedded (not

31. When a document is divided into sections, Sect structure element(s) should be used to contain

32. When a document is divided into sections, structure elemSeenct(ts) should be used to contain the structure

33. When a grPouapritng of content has semSeacnttic purpose unrelated to the document's headings hierarchy, it should

34. When a more accessible representation exists, the more accessible representation should be used

35. Where not otherwise defined for uses other than <Table>, <L> and <TOC>, it is recommended that

36. a file should not contain any feature that is deprecated in ISO 32000-2;

37. a file should not contain features described in specifications prior to ISO 32000-2 which are

38. and should conform to PDF/A.

39. annotations may be used, and should be used if a visible annotation improves usability. If

40. block-level elements, <Link> elements within a <TOCI> are recommended to have the Placement

41. bodies of important information. These PDF files should be made accessible to users with disabilities.

42. but in workflows where such PDFs are further modified processors should be tested to

43. by identifying the set of PDF components that shall, should or may be used, as well as

44. colours that should be reproduced as accurately as possible, such as brand colours. Whether

45. containing malicious code. Developers of PDF consumer software should therefore make

46. different types of ISO document should be noted. This document was drafted in accordance with the

47. different types of ISO documents should be noted. This document was drafted in accordance with the

48. document fragment as specified in ISO 32000-2:2020, 14.8.4.3, that content should be enclosed in either a

49. documents in their conventional paginated form, PDF files should ensure that their content is

50. element. The P structure type should only be used when content is intended to be a semantic

51. fields should be converted to PDF metadata in XMP format for organizational and

52. here). The default value is Default, which means that whether BPC should be turned on or off is

53. hierarchy, it should be enclosed within a Part structure element. ISO 32000-2:2020, Table 365

54. is recommended that structure elements not be empty unless they serve a semantic role in a

55. of ISO document should be noted. This document was drafted in accordance with the editorial rules of the

56. or <Formula> structure element are recommended to assume that the <Caption> refers to that

57. or as File Attachment annotations. Any such file should be accessible in its own right, as defined by

58. or logical document fragment as specified in ISO 32000-2:2020, 14.8.4.3, that content should be

59. owner should be used as defined in Table 1.

60. page level objects or resources, and thus where PDF processors should search for it, for all

61. recommended place in PDF 2.0 documents for specifying the document title, author,

62. recommended prefix for the Dublin Core metadata schema as defined in the XMP specification, which

63. recommended that each embedded file use one of these mechanisms. This is important,

64. represent considerable bodies of important information. These PDF files should be made accessible to users

65. sequences can be used to enclose dot leaders. Accordingly, it is recommended to avoid the

66. should be used as defined in Table 2.

67. should not be confused with Document Part Metadata (ISO 32000-2, 14.12.4.2), referenced

68. should not be enclosed in a P.

69. should therefore analyze the Names tree as well as all annotation entries on all PDF

70. structure type should only LbBe oudseyd when content is intended to be a semantPic paragraph, or when there is

71. structure types should be used.

72. the specification only highlights document-level semantics for this purpose should not be

73. tion. Articles should be disjoint; that is, they should not contain other articles as constitu-

74. types are allowed for associated files but the embedded form is recommended.”

75. which are not explicitly defined in ISO 32000-1 should not be used.

76. with best practices, these techniques should be refreshed and updated regularly. This document builds

77. — a file should not contain any feature that is deprecated in ISO 32000-2;

78. — a file should not contain features described in specifications prior to ISO 32000-2 which are not explicitly

79. ◼ “should” = strongly recommended

### Tag and Structure Requirements

Specific requirements for PDF structure and tags:

1. 14.8.2.2.2) shall not be tagged in the structure tree.

2. 14.8.4.3 “Document level structure types”; shall be an indirect reference)

3. 32000-1, Table 322) are required that map these custom structure types (e.g., “<DataTable>”) to

4. A caption accompanying a figure shall be tagged with a tag.

5. A metadata stream that shall contain metadata for the structure

6. A structure element with no explicit namespace may be present. Such a structure element shall

7. A structure element with no explicit namespace may be present. Such a structure element shall have, after

8. All real content shall be tagged as defined in ISO 32000-1:2008, 14.8. Artifacts (ISO 32000-1:2008,

9. All structure elements shall belong to, or be role mapped to, at least one of the following

10. All structure elements shall belong to, or be role mapped to, at least one of the following namespaces

11. Any structure Placement Not required

12. Artifact content intended to be consumed in a single unit shall be enclosed within a single structure

13. Content shall be marked in the structure tree with semantically appropriate tags in a logical reading

14. Content shall be tagged in logical reading order. The most semantically appropriate tag shall be used for

15. Graphics objects, other than text objects, shall be tagged with a tag as described in

16. Graphics that possess semantic value only in combination with other graphics shall be tagged with a

17. NOTE 3 Conformance with ISO/TS 32005 is required because, while ISO 32000-2 did not deprecate any structure

18. Non-standard structure types are permitted. However, they shall be mapped to the nearest functionally

19. Standard tags defined in ISO 32000-1:2008, 14.8.4, shall not be remapped.

20. Tagging shall reflect the semantics of the document's real content regardless of how the real content was

21. Tagging shall reflect the semantics of the document’s real content regardless of how the real

22. The DocumentFragment structure type shall only be used when the author’s intent is to identify

23. The structure tree root (defined in ISO 32000-2:2020, 14.7.2) shall contain a single Document

24. The structure tree root (defined in ISO 32000-2:2020, 14.7.2) shall contain a single structure

25. The structure type shall only be used when the author’s intent is to identify real

26. These containment requirements shall also apply to structure elements that are role mapped into the

27. Usage of the standard structure types shall be in accordance with the requirements specified

28. Usage of the standard structure types shall be in accordance with the requirements specified in both

29. Where a title applies to an entire article, the Title structure element shall be included inside the

30. Within a given explicitly provided namespace, structure types shall not be role mapped to other

31. Within a given explicitly provided namespace, structure types shall not be role mapped to other structure

32. contains multiple such articles, that content shall be enclosed in an Art structure element.

33. content that are not included in the tagging structure. For this use case the content must be

34. default standard structure namespace, then that document shall conform to the requirements specified

35. elements in such namespaces shall have their structure types role mapped as described in this

36. from the AES-GCM algorithm. The 16-byte GCM authentication tag shall be appended to the end of the

37. glyphs to form the appearance of a single glyph) shall be tagged using , as specified in

38. namespaces shall have their structure types role mapped as described in this subclause. Such role mapping

39. of tagged PDF files required for an accessible experience. Other Best Practice Guides will address

40. pages must each be linked to the logical structure, in the right order, without restarting the

41. represented by a single semantic structure element with intrinsic semantics shall not be

42. section 9.1. Additionally, the structure that constitutes a PDF MAC token shall satisfy the

43. semantic structure element with intrinsic semantics shall not be represented by several such structure

44. shall be tagged according to Clause 7.

45. shall conform to the requirements for the standard structure types to which they are role mapped, including

46. tags shall include an alternative representation or replacement text that represents the contents

47. two radio buttons, two <Form> structure elements are required to link them to the logical

48. types, they shall conform to the requirements for the standard structure types to which they are

49. use of namespaces shall not be required and those structure elements are exempt from the provisions

50. when heading structure elements are used in a sidebar, they must be semantically appropriate in

51. “Content shall be marked in the structure tree

52. ◼ Heading content must be tagged with the correct structure element (<H1>–<H6>), to

53. ◼ References for footnotes must be tagged to reflect all the appropriate semantics, e.g.

### Metadata Requirements

Specific requirements for PDF metadata:

1. Accordingly, PDF 2.0 processors must be prepared to encounter metadata almost anywhere

2. Catalog Table 29 (Optional; PDF 1.4; shall be an indirect reference) A metadata

3. Document Table 162 (Optional; PDF 2.0; shall be an indirect reference) A metadata

4. Document Table 409 (Optional; PDF 2.0; shall be an indirect reference) A metadata

5. ICC Profile Table 65 (Optional; PDF 1.4) A metadata stream that shall contain

6. PDF Declaration, as specified in PDF Declarations, shall be included through the Metadata entry

7. Page Table 31 (Optional; PDF 1.4) A metadata stream that shall contain

8. Part (DPart) stream that shall contain metadata for this document part.

9. Text (page content, metadata, annotations) must be mapped to Unicode in order to be accessible

10. The PDF/UA version and conformance of a file shall be specified in the metadata stream that is the value

11. The PDF/UA version of a file shall be specified in the value of the entry in the document catalog

12. The following clauses clarify what “the metadata shall be attached as closely as possible to

13. The stream in the document’s catalog dictionary shall contain a dc:title entry, where dc is the

14. processor must agree on where metadata is present in the often-complex internal PDF

15. regarding the metadata’s location is required. However, since some objects in PDF distribute

16. stream that shall contain metadata for the document.

17. the Metadata entry, the metadata shall be attached as closely as possible to

18. ◼ The document level XMP metadata must contain a Title (dc:title) (see PDF/UA-1, 8.11,

19. ◼ The document level XMP metadata must include the PDF/UA “flag” (see Annex A).

### Validation Rules

Rules for preflight validation checks:

1. For the latest resolved errata see: https://pdf-issues.pdfa.org/

2. IETF RFC 2104, Identifiers and Test Vectors for HMAC-SHA-224, HMAC-SHA-256, HMAC-SHA-384, and HMAC-

3. V Describes a PDF MACE tnokcerny ptot validate the

4. agreement with the copyright holder. Such an allowance places unacceptable burdens to verify the existence,

5. applies. For undated references, the latest edition of the referenced document (including any

6. cautioned that this may not represent the latest information, which may be obtained from the patent

7. colour space in the PDF file to the lightest colour

8. cryptographic check sum on data that uses a symmetric key to detect both accidental and intentional

9. for the latest information & updates

10. information on how to validate PDF MAC tokens and Annex C lists a number of examples.

11. material, but also to ensure that the receiving party can verify its integrity. Encryption mechanisms defined

12. references, only the edition cited applies. For undated references, the latest edition of the referenced

13. the latest editioDno couf mtheen rt emferaennacgeedm deonct uampepnlitc (aitnioclnusd i—ng aEnleyc atrmoennicd mdoecnutms)e anptp lfiieles .format enhancement for

14. the latest edition of the referenced document (including any amendments) applies.

15. the latest edition ofD tohceu rmeefenrte mncaenda gdeomcuenmte —nt P(ionrctlaubdlein dgo acnuym aemnte fnodrmmaetn —ts) Paaprptl 2ie: sP.DF 2.0

16. this may not represent the latest information, which may be obtained from the patent database available at

17. tone scale. That aligns the lightest colour in the

18. upon the mechanisms present in ISO 32000-2 and extends and enhances them to meet the latest needs

19. verify the existence, validity, and longevity of such claims.

20. — Reliable: Files comply to the greatest possible extent with applicable specifications to facilitate robustness

---

## Detailed Requirements by Document

## PDF/UA-1: Universal Accessibility

**Standard:** ISO 14289-1:2014

### Must-Have Requirements (12)

- element has been changed from a shall to a should, and additional normative text added to explicate
- when the Scope element is required;
- — required computer hardware and/or operating systems.
- The PDF/UA version and conformance of a file shall be specified in the metadata stream that is the value
- The Identification schema namespace URI is http://www.aiim.org/pdfua/ns/id/. The required schema
- Internal Required PDF/UA version identifier
- The value of shall be the part number of this International Standard to which the file
- to a part, then the value of shall be the amendment number and year, separated by a colon.

### Prohibited Features (12)

- Single user only, copying and networking prohibited.
- patent rights. ISO shall not be held responsible for identifying any or all such patent rights. Details of
- The version number of a file may be any value from 1.0 to 1.7, and the value shall not be used in
- 14.8.2.2.2) shall not be tagged in the structure tree.
- Standard tags defined in ISO 32000-1:2008, 14.8.4, shall not be remapped.
- Flickering, blinking, or flashing shall not be used (WCAG 2.0, Guideline 2.3).
- Information shall not be conveyed by contrast, colour, format or layout, or by combinations thereof,
- in strict numerical order and shall not skip an intervening heading level. is permissible,

### Tag Requirements (12)

- All real content shall be tagged as defined in ISO 32000-1:2008, 14.8. Artifacts (ISO 32000-1:2008,
- 14.8.2.2.2) shall not be tagged in the structure tree.
- Content shall be marked in the structure tree with semantically appropriate tags in a logical reading
- Non-standard structure types are permitted. However, they shall be mapped to the nearest functionally
- Standard tags defined in ISO 32000-1:2008, 14.8.4, shall not be remapped.

### Metadata Requirements (2)

- The PDF/UA version and conformance of a file shall be specified in the metadata stream that is the value
- The stream in the document’s catalog dictionary shall contain a dc:title entry, where dc is the

---

## PDF/UA-2: Universal Accessibility

**Standard:** ISO 14289-2:2024

### Must-Have Requirements (12)

- All rights reserved. Unless otherwise specified, or required in the context of its implementation, no part of this publication may
- patent(s) which may be required to implement this document. However, implementers are cautioned that
- — required computer hardware and/or operating systems;
- The PDF/UA version of a file shall be specified in the value of the entry in the document catalog
- required schema namespace prefix is .
- Internal (Required) PDF/UA part identifier
- Internal (Required) Four-digit year of the date of
- The value of pdfuaid: rev shall be for PDF files conforming with this document.

### Prohibited Features (11)

- Single user only, copying and networking prohibited.
- www.iso.org/patents. ISO shall not be held responsible for identifying any or all such patent rights.
- semantic structure element with intrinsic semantics shall not be represented by several such structure
- Within a given explicitly provided namespace, structure types shall not be role mapped to other structure
- Conforming files shall use the explicitly numbered heading structure types ( - ) and shall not use the
- Titles shall be identified by the standard structure type and shall not be identified as a heading.
- standard structure type shall not be pNroetseent in conforming files.
- In cases where ruby typesetting is used for other purposes, the structure Aelseimdeent shall not be used.

### Tag Requirements (12)

- NOTE 3 Conformance with ISO/TS 32005 is required because, while ISO 32000-2 did not deprecate any structure
- Tagging shall reflect the semantics of the document's real content regardless of how the real content was
- semantic structure element with intrinsic semantics shall not be represented by several such structure
- Artifact content intended to be consumed in a single unit shall be enclosed within a single structure
- All structure elements shall belong to, or be role mapped to, at least one of the following namespaces

### Metadata Requirements (1)

- The PDF/UA version of a file shall be specified in the value of the entry in the document catalog

---

## Structure Namespace and Role Mapping

**Standard:** ISO TS 32005:2023

### Must-Have Requirements (12)

- All rights reserved. Unless otherwise specified, or required in the context of its implementation, no part of this publication may
- When such a PDF declaration is present, it shall conform to the requirements of the PDF Declarations
- specification. Such claim of conformance shall take the form described in Table 1.
- PDF documents conforming to this document shall be versioned as PDF 2.0 using either the header or
- namespace, then the requirements of ISO 32000-1 shall be used for their inclusion. In such cases, the
- default standard structure namespace, then that document shall conform to the requirements specified
- shall use the PDF 2.0 namespace and follow the inclusion rules defined in ISO 32000-2:2020, Annex L,
- PDF 2.0 elements shall explicitly declare their namespace using the PDF 2.0 namespace and may contain

### Prohibited Features (5)

- Single user only, copying and networking prohibited.
- patent rights. ISO shall not be held responsible for identifying any or all such patent rights. Details of
- use of namespaces shall not be required and those structure elements are exempt from the provisions
- namespace and the PDF 2.0 namespace. PDF 1.7 elements and PDF 2.0 elements shall not have child or
- shall not occur unless the parent element is used as a grouping level element

### Tag Requirements (3)

- use of namespaces shall not be required and those structure elements are exempt from the provisions
- default standard structure namespace, then that document shall conform to the requirements specified
- These containment requirements shall also apply to structure elements that are role mapped into the

---

## PDF/UA Reference - Logical Structure

**Standard:** ISO TS 32001:2022

### Must-Have Requirements (5)

- All rights reserved. Unless otherwise specified, or required in the context of its implementation, no part of this publication may
- — required computer hardware and/or operating system
- PDF documents using enhancements described in this document shall include in their document
- with a prefix name of . This shall contain a developer extensions dictionary in accordance with
- id-shake256 object identifier (OID) in section 2.3 of RFC 8419 shall be used.

### Prohibited Features (1)

- patent rights. ISO shall not be held responsible for identifying any or all such patent rights. Details of

---

## PDF/UA Reference - Artifacts & Role Mapping

**Standard:** ISO TS 32002:2022

### Must-Have Requirements (12)

- All rights reserved. Unless otherwise specified, or required in the context of its implementation, no part of this publication may
- — required computer hardware and/or operating system.
- PDF documents using enhaInScOem_ ents described in this document shall include in their document
- 7.12) with a prefix name of . This shall contain a developer extensions dictionary in accordance
- When using the Ed25519 EdDSA elliptic curve algorithm, the message digest shall be computed using the SHA512
- elliptic curve algorithm, the message digest shall be computed using the SHAKE256 message digest algorithm with OID id-
- When using the ECDSA elliptic curves in Table 1 for signing data, these shall be used in accordance with
- keys used in PDF signatures shall specify curve parameters (ECParameters) for the subject’s public key

### Prohibited Features (2)

- patent rights. ISO shall not be held responsible for identifying any or all such patent rights. Details of
- and specifiedCurve options shall not be used.

---

## PDF/UA Reference - Marked Content

**Standard:** ISO TS 32003:2023

### Must-Have Requirements (12)

- All rights reserved. Unless otherwise specified, or required in the context of its implementation, no part of this publication may
- notice of (a) patent(s) which may be required to implement this document. However, implementers are
- authenticates all individual ciphertexts, but a separate mechanism is required to achieve document-
- — required computer hardware and/or operating system.
- TIShOe_ developer extensions dictionary described in Table 1 shall be included in the document’s extensions
- dictionary in accordance with ISO 32000-2:2020, 7.12. It shall be included as an array entry under the
- number (Required) 6 - (ISO/TS 320A0E3S)V T4he security handler defines the use of encryption
- encryption dictionary is 6, the algorithm described in ISO/TS 32003 shall be used”.

### Prohibited Features (1)

- database available at www.iso.org/patents. ISO shall not be held responsible for identifying any or all

### Tag Requirements (1)

- from the AES-GCM algorithm. The 16-byte GCM authentication tag shall be appended to the end of the

---

## PDF/UA Reference - Conformance & Testing

**Standard:** ISO TS 32004:2024

### Must-Have Requirements (12)

- All rights reserved. Unless otherwise specified, or required in the context of its implementation, no part of this publication may
- patent(s) which may be required to implement this document. However, implementers are cautioned that
- — required computer hardware and/or operating system.
- The developer extensions dictionary in Table 1 shall be part of the document’s extensions dictionary
- (ISO 32000-2:2020, 7.12). It shall be included as an array entry under the prefix.
- Encrypted PDF documents making use of the extension specified in this document shall conform to
- KDFSalt (Conditionally required; shall be a direct object)
- KDFSalt This entry is required in documents that make use of PDF MAC.

### Prohibited Features (8)

- www.iso.org/patents. ISO shall not be held responsible for identifying any or all such patent rights.
- MACLocation (Required; shall not be an indirect reference)
- ByteRange (Conditionally required; shall not be an indirect reference)
- is , this entry shall not be present.
- MAC (Conditionally required; shall not be an indirect reference) MAC-
- If is , this entry shall not be present.
- If MA Cis , this entry shall not be present.
- CMS unauthenticated attributes shall not be used; the field shall be absent.

### Tag Requirements (1)

- section 9.1. Additionally, the structure that constitutes a PDF MAC token shall satisfy the

---

## Well-Tagged PDF Specification

**Standard:** WTPDF 1.0

### Must-Have Requirements (12)

- required computer hardware and/or operating systems;
- A file conforming with this document shall identify conformance with at least one of the
- As specified in the following subclauses, applicable conformance level(s) shall be indicated using
- A file declaring conformance with the conformance level for reuse shall conform to all the
- Files conforming to the conformance level for reuse shall include a PDF Declaration with the URI
- A file declaring conformance with the conformance level for accessibility shall conform to all
- Files conforming to the conformance level for accessibility shall include a PDF Declaration with
- a file shall adhere to all requirements of ISO 32000-2;

### Prohibited Features (12)

- represented by a single semantic structure element with intrinsic semantics shall not be
- Within a given explicitly provided namespace, structure types shall not be role mapped to other
- Conforming files shall use the explicitly numbered heading structure types (H1-Hn) and shall not
- Titles shall be identified by the Title standard structure type and shall not be identified as a
- Note standard structure type shall not be present in conforming files.
- In cases where ruby typesetting is used for other purposes, the Ruby structure element shall not
- The Warichu structure element shall not be used for content that is not typeset as warichu.
- approximates the intended labelling scheme; in such cases the value None shall not be used.

### Tag Requirements (12)

- Tagging shall reflect the semantics of the document’s real content regardless of how the real
- represented by a single semantic structure element with intrinsic semantics shall not be
- All structure elements shall belong to, or be role mapped to, at least one of the following
- elements in such namespaces shall have their structure types role mapped as described in this
- A structure element with no explicit namespace may be present. Such a structure element shall

### Metadata Requirements (1)

- PDF Declaration, as specified in PDF Declarations, shall be included through the Metadata entry

---

## Tagged PDF Best Practices

**Standard:** Best Practice Guide

### Must-Have Requirements (12)

- of tagged PDF files required for an accessible experience. Other Best Practice Guides will address
- ◼ “shall” = required (to avoid confusion with the specifications, this term is not used in this
- “Content shall be marked in the structure tree
- ◼ Heading content must be tagged with the correct structure element (<H1>–<H6>), to
- ◼ References for footnotes must be tagged to reflect all the appropriate semantics, e.g.
- Text (page content, metadata, annotations) must be mapped to Unicode in order to be accessible
- ◼ The document level XMP metadata must include the PDF/UA “flag” (see Annex A).
- ◼ The document level XMP metadata must contain a Title (dc:title) (see PDF/UA-1, 8.11,

### Tag Requirements (9)

- of tagged PDF files required for an accessible experience. Other Best Practice Guides will address
- “Content shall be marked in the structure tree
- ◼ Heading content must be tagged with the correct structure element (<H1>–<H6>), to
- ◼ References for footnotes must be tagged to reflect all the appropriate semantics, e.g.
- pages must each be linked to the logical structure, in the right order, without restarting the

### Metadata Requirements (3)

- Text (page content, metadata, annotations) must be mapped to Unicode in order to be accessible
- ◼ The document level XMP metadata must include the PDF/UA “flag” (see Annex A).
- ◼ The document level XMP metadata must contain a Title (dc:title) (see PDF/UA-1, 8.11,

---

## PDF Metadata Declarations

**Standard:** PDF Declarations

### Must-Have Requirements (2)

- pdfd:declarations Unordered array (Required) An unordered array of PDF
- pdfd:conformsTo URI (Required) A property containing a URI specifying

### Prohibited Features (1)

- the subject of patent rights. The PDF Association shall not be held responsible for

---

## Best Practice Contents

**Standard:** PDF 2.0 AN001

### Must-Have Requirements (1)

- The key can take three states: ON, OFF and Default (note that these must be exactly as shown

---

## Associated Files

**Standard:** PDF 2.0 AN002

### Must-Have Requirements (9)

- entry is required to contain one of the values defined in PDF 2.0: Source, Data,
- • a MIME type (as defined in RFC 8118) must be specified in the Subtype entry of the
- • if the (recommended) Params entry is present, it shall specify the latest
- desktop computers must take into account that these viewers (at this time) typically do
- In many important use cases - electronic invoices being the classic example - data must be
- borders, sender and receiver must agree on the format and representation of the data. A
- The principle is applicable to any case in which a record must be processed by machines
- but must also be readable by humans. An example would be of software license

---

## Object Metadata Locations

**Standard:** PDF 2.0 AN003

### Must-Have Requirements (12)

- processor must agree on where metadata is present in the often-complex internal PDF
- Catalog Table 29 (Optional; PDF 1.4; shall be an indirect reference) A metadata
- stream that shall contain metadata for the document.
- Page Table 31 (Optional; PDF 1.4) A metadata stream that shall contain
- ICC Profile Table 65 (Optional; PDF 1.4) A metadata stream that shall contain
- Document Table 162 (Optional; PDF 2.0; shall be an indirect reference) A metadata
- Document Table 409 (Optional; PDF 2.0; shall be an indirect reference) A metadata
- Part (DPart) stream that shall contain metadata for this document part.

### Tag Requirements (3)

- content that are not included in the tagging structure. For this use case the content must be
- 14.8.4.3 “Document level structure types”; shall be an indirect reference)
- A metadata stream that shall contain metadata for the structure

### Metadata Requirements (12)

- processor must agree on where metadata is present in the often-complex internal PDF
- Catalog Table 29 (Optional; PDF 1.4; shall be an indirect reference) A metadata
- stream that shall contain metadata for the document.
- Page Table 31 (Optional; PDF 1.4) A metadata stream that shall contain
- ICC Profile Table 65 (Optional; PDF 1.4) A metadata stream that shall contain

---

## Summary Statistics

**Critical Must-Have Requirements:** 117

**Prohibited Features:** 47

**Recommended Features:** 79

**Tag Requirements:** 53

**Metadata Requirements:** 19

**Validation Rules:** 20

