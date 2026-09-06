# Legal Metrology (Packaged Commodities) Rules, 2011 — Validation Engine Spec
### Source: LM(PC) Rules 2011, as amended by GSR 748(E) dated 24.10.2011 (eff. 01.07.2012) and GSR 734(E) dated 30.09.2011
### Built for: SIH26034 — Packaged Commodity Compliance Scanner

> **Use this doc as your rule table.** Each rule below is written as: `RULE_ID | Field | Condition to PASS | Data source (OCR/manual) | Notes/Edge cases`. Build your engine so each rule is an independent, testable function returning PASS/FAIL/NOT_APPLICABLE — this maps directly to a report generator.

---

## 0. SCOPE CHECK (run first — determines if Chapter II applies at all)

| ID | Check | Logic |
|---|---|---|
| SCOPE-1 | Excluded by quantity | If net qty > 25 kg or > 25 L → Chapter II does NOT apply (exception: cement/fertilizer bags up to 50 kg still covered) |
| SCOPE-2 | Excluded — industrial/institutional | If package is sold direct to an industrial or institutional consumer (hotels, hospitals, airlines, railways, transport) buying directly from manufacturer → exempt |
| SCOPE-3 | Excluded — tiny packages | Net weight/measure ≤ 10 g or ≤ 10 mL → fully exempt from these rules. **BUT**: packages 10g–20g / 10mL–20mL must still declare MRP and net quantity (this proviso was withdrawn w.e.f. 01.07.2012 — flag as "check current applicability" since your engine should let users toggle old/new rule version) |
| SCOPE-4 | Excluded — fast food | Fast food packed by restaurant/hotel for immediate sale → exempt |
| SCOPE-5 | Excluded — drug formulations | Scheduled/non-scheduled formulations under Drugs (Price Control) Order 1995 → exempt |
| SCOPE-6 | Excluded — bulk agri produce | Agricultural farm produce packages above 50 kg → exempt |
| SCOPE-7 | Sector overrides | Food articles → declarations (b),(d)-adjacent items follow PFA Act 1954, not this rule for some fields; Cosmetics → Drugs & Cosmetics Rules 1945 for mfg-date field; Alcohol → State Excise laws for MRP field (LM rules apply only if state law doesn't cover MRP) |

**If SCOPE fails → mark package "OUT OF SCOPE", skip remaining checks, but still let officer log it.**

---

## 1. MANDATORY DECLARATIONS — PRESENCE CHECK (Rule 6(1))

This is the core OCR/NLP extraction target list. Each must be detected as present on the label (principal display panel or elsewhere per rule):

| ID | Declaration | Rule Ref | Required format/notes |
|---|---|---|---|
| DECL-1 | Name & address of manufacturer (and packer if different; and importer if imported) | 6(1)(a) | If only one name+address with no "mfd by"/"packed by" qualifier → **presume it's the manufacturer** (Explanation I) — engine should still flag as valid but note the presumption. If multiple names appear, prosecution logic falls on first-listed manufacturer only (Explanation II) — informational, not a fail. |
| DECL-2 | Common/generic name of commodity | 6(1)(b) | For multi-product packs, each product's name + quantity/number must appear |
| DECL-3 | Net quantity (weight/measure/number) | 6(1)(c) | Must use standard unit — cross-check against Rule 13 unit rules (Section 5) |
| DECL-4 | Month & year of manufacture/pre-packing/import | 6(1)(d) | NOT required for: bidis, incense sticks, domestic LPG cylinders (14.2kg/5kg from PSU). Can be words, numerals, or both. |
| DECL-5 | Retail Sale Price (MRP) | 6(1)(e) | NOT required for: bidi packages, domestic LPG under Administrative Price Mechanism. Must follow exact format — see Section 3. |
| DECL-6 | Dimensions (if size is relevant to the commodity) | 6(1)(f) | Applicable to bed-sheets, fabric, sarees, towels, cables, etc. — conditional field |
| DECL-7 | Consumer care details: name, address, phone, email (if available) of contact for complaints | 6(2) | Mandatory on every package regardless of other exemptions |

**FAIL condition for each**: declaration is absent, illegible, or not on the principal display panel where required.

---

## 2. FONT SIZE / READABILITY CHECK (Rule 7) — CRITICAL for image-analysis engine

This is likely your hardest CV task — measure numeral height in the net-quantity declaration against these tables.

### Table I — quantity declared by weight/volume
| Net Qty | Min height (normal print), mm | Min height (blown/molded/embossed), mm |
|---|---|---|
| Up to 200 g/ml | 1 | 2 |
| 200–500 g/ml | 2 | 4 |
| Above 500 g/ml | 4 | 6 |

### Table II — quantity declared by length/area/number (based on principal display panel area)
| PDP area | Min height (normal), mm | Min height (blown/molded), mm |
|---|---|---|
| Up to 100 cm² | 1 | 2 |
| 100–500 cm² | 2 | 4 |
| 500–2500 cm² | 4 | 6 |
| Above 2500 cm² | 6 | 6 |

**Additional rules:**
- ENGINE-FONT-1: Absolute minimum letter height anywhere in declarations = 1 mm (normal), 2 mm (blown/molded/embossed/perforated) — Rule 7(3)
- ENGINE-FONT-2: Numeral/letter **width** must be ≥ ⅓ of its height (exception: numeral "1" and letters i, I, l)
- ENGINE-FONT-3: Rule 7 does NOT apply if the same info is already mandated in required format by another law (avoid false negatives)
- ENGINE-FONT-4: Retail sale price + net quantity numerals must be printed in a **contrasting colour** vs background (Rule 9(1)(b)) — unless blown/formed/molded on glass/plastic (exempt from colour-contrast check)
- ENGINE-FONT-5: Free-space buffer around the quantity declaration — space above/below ≥ height of the numeral; space left/right ≥ 2× height of numeral (Rule 8(1)) — check for surrounding clutter/overlapping text in the image region

---

## 3. MRP FORMAT VALIDATION (Rule 2(m)) — string-pattern check

MRP must appear as one of these exact patterns (case-insensitive), immediately followed by the number and "inclusive of all taxes" (or "incl. of all taxes"):
```
Maximum retail price Rs./₹ ___ inclusive of all taxes
Max. retail price Rs./₹ ___ inclusive of all taxes
MRP Rs./₹ ___ incl. of all taxes
```
**Rounding rule to validate (if raw price is known/computable):**
- Fraction < 50 paise → round DOWN to nearest rupee
- Fraction ≥ 50 paise and ≤ 95 paise → round to 50 paise
- (Implies fraction > 95 paise rounds up to next rupee)

**Other MRP checks:**
- MRP-1: No stickers allowed to alter/cover the original MRP, EXCEPT a sticker showing a *reduced* MRP, and it must not obscure the original manufacturer/packer MRP (Rule 6(3))
- MRP-2: Manufacturer/packer must never alter price on a wrapper already printed and in use (Rule 6(6))
- MRP-3: No sale above declared MRP by any dealer (Rule 18(2)) — this is a market-conduct check, not label check
- MRP-4: Soft-drink/beverage returnable bottles may show MRP on crown cap OR bottle, format "MRP Rs...." is sufficient (Rule 8(2)) — treat as valid alt-location

---

## 4. NET QUANTITY DECLARATION RULES (Rules 11–17)

| ID | Rule | Check |
|---|---|---|
| QTY-1 | 11(1) | Net quantity excludes wrapper/packaging weight |
| QTY-2 | 11(2)/(3) | Quantity declared must be genuine net qty consumer receives (no "when packed" qualifier) UNLESS commodity is in the "when packed" list (Third Schedule: soaps, lotions, creams other than milk cream) |
| QTY-3 | 12(6) | Declaration must NOT contain words like "minimum," "not less than," "average," "about," "approximately" — **flag these as automatic violations if found near quantity text** (post-2012 amendment broadens this to ANY misleading word, not just the listed examples) |
| QTY-4 | 12(2) | Unit type must match commodity nature: mass (solid/semi-solid/viscous), length, area, volume (liquid), or number — cross check against Fourth Schedule exceptions (Section 6 below) |
| QTY-5 | 13(2)/(3) | Unit-size rule: If declared qty < 1kg/1m/1sq.m/1cu.m/1L → must use gram/cm/sq.dm/cc/mL (the smaller unit); if ≥ 1 of those → use kg/m/sq.m/cu.m/L with decimals, not the smaller unit (some flexibility allowed at exactly 1 unit) |
| QTY-6 | 13(4) | Words like "dozen," "score," "gross," "great gross" must NEVER appear as the stated quantity unit |
| QTY-7 | 13(5) | Must use SI units only; number-sold items use symbol "N" or "U" |
| QTY-8 | 14 | Bedsheets/fabric/sarees/towels/napkins/tablecloths: must declare number + finished dimensions; if multiple pieces of different sizes, declare each piece's dimension + price, and mark each piece individually |
| QTY-9 | 16 | Sheet-type products (foil, tissues, toilet paper, waxed paper): must state number of usable sheets + dimension of each sheet |
| QTY-10 | 17 | Container-type commodities (bags/boxes/cups/pans sold as containers): declare per sub-type — bag type→count+linear dims; rect/square→count+L×W×D; round→count+diameter+depth |

---

## 5. STANDARD PACKAGE SIZES (Second Schedule) — cross-reference table

For the commodities below, flag "NON-STANDARD SIZE" if the declared net quantity doesn't match the list (this proviso requiring the "non-standard size" disclaimer text was **withdrawn w.e.f. 01.07.2012** — decide which rule-version your engine targets; recommend defaulting to "informational only" not a hard fail, since it's a repealed provision but Second Schedule sizes are still cited as recommended standards).

| Commodity | Standard sizes |
|---|---|
| Baby food / weaning food | 100g–900g (100g steps), 1kg, 2kg, 5kg, 10kg |
| Biscuits | 25,50,75,100,150,200,250,300g then 100g multiples to 1kg |
| Bread (excl. bun) | 100g multiples |
| Butter/margarine (uncanned) | 25,50,100,200,500g,1,2,5kg then 5kg multiples |
| Cereals & pulses | 100,200,500g,1,2,5kg then 5kg multiples |
| Coffee | 25,50,100,200,250,500g,1kg then 1kg multiples |
| Tea | 25,50,100,125,250,500g,1kg then 1kg multiples |
| Beverage-reconstitution materials | 25,50,100,200,500g,1kg then 1kg multiples |
| Edible oils/vanaspati/ghee/butter oil | 50,100,200,500g,1,2,3,5kg then 5kg multiples (volume equivalents allowed, mass shown in bracket) |
| Milk powder | <50g unrestricted; 50,100,200,500g,1kg then 500g multiples |
| Detergent powder (non-soapy) | <50g unrestricted; 50,100,200,500,700g,1,1.5,2kg then 1kg multiples |
| Rice/flour/atta/rawa/suji | 100,200,500g,1,2,5kg then 5kg multiples |
| Salt | <50g in 10g steps; 50,100,200,500,750g,1,2,5kg then 5kg multiples |
| Laundry soap | 50,75,100g then 50g multiples |
| Detergent cakes/bars | 50,75,100,125,150,200,250,300g then 100g multiples |
| Toilet/bath soap | 25,50,75,100,125,150g then 50g multiples |
| Aerated/soft drinks | 65,100,125,150,200,250,300,330(cans),500ml,750ml,1,1.5,2,3,4,5L |
| Mineral/drinking water | 100,150,200,250,300,500,750ml,1,1.5,2,3,4,5L |
| Cement bags | 1,2,5,10,20,25,40(white cement only),50kg |
| Paint/varnish (liquid) | 50,100,200,500ml,1,2,3,4,5L then 5L multiples |
| Paste/solid paint | 500g,1,1.5,2,3,5,7kg then 5kg multiples |
| Base paint | 450,500,900,925,950,975ml,1L,3.6–3.9L, no restriction above 4L |

---

## 6. UNIT-TYPE EXCEPTIONS (Fourth Schedule) — override QTY-4 for these commodities

| Commodity | Must be declared in |
|---|---|
| Aerosol products | Weight |
| Acids (liquid) | Weight or volume |
| Compressed/liquefied gas (not LPG) | Weight + equivalent volume @ stated temp/pressure |
| Curd | Weight |
| Electric cable/wire | Length or weight |
| Fencing wire | Number or weight |
| Fruits | Number or weight |
| Furnace oil | Weight or volume |
| Edible/non-edible oil, vanaspati, ghee, butter oil | Weight or volume |
| Heavy residual fuel oil | Weight |
| Industrial diesel | Volume |
| Honey/malt extract/golden syrup/treacle | Weight |
| Ice cream & frozen products | **Weight** (was Volume, amended 01.07.2012) |
| Liquid chemicals | Weight or volume |
| LPG | Weight |
| Nails/wood screws | Number or weight |
| Paint/varnish (liquid) | Volume |
| Paste/solid paint | Weight |
| Rasgulla, Gulabjamun, sweets | Weight |
| Ready-made garments | Number |
| Sauces | Weight |
| Tyres/tubes | Number |
| Yarn | Weight or length |
| Cosmetics (creams, shampoo, lotion, perfume) | Weight or measure |

---

## 7. MAXIMUM PERMISSIBLE ERROR (First Schedule) — for physical/lab verification module (not image-scannable, but include for the "inspection" module of your dashboard)

### By weight/volume
| Declared qty | Max error |
|---|---|
| Up to 50g/ml | 9% |
| 50–100 | 4.5% |
| 100–200 | 4.5% |
| 200–300 | 9% |
| 300–500 | 3% |
| 500–1000 | 15% |
| 1000–10000 | 1.5% |
| 10000–15000 | 150 (absolute, not %) |
| >15000 | 1.0% |

Round % result to nearest 0.1g/ml (≤1000g/ml) or nearest whole g/ml (>1000g/ml).

### By length/area/number
| Type | Max error |
|---|---|
| Length | 2% up to 10m, then 1% |
| Area | 4% up to 10 sq.m, then 1% |
| Number | 2% |

---

## 8. LANGUAGE & PLACEMENT RULES

| ID | Rule | Check |
|---|---|---|
| LANG-1 | 9(4) | All declarations must be in Hindi (Devanagari) OR English (other languages may be added, not substituted) |
| PLACE-1 | 8(1) | All declarations on principal display panel |
| PLACE-2 | 9(2) | Declaration must not require reading through liquid contents |
| PLACE-3 | 9(3) | If package has outer wrapper/container, wrapper must repeat all declarations UNLESS wrapper is transparent and inner declarations are clearly readable through it |
| PLACE-4 | 9(1)(b) proviso | Handwritten declarations allowed only if clear, unambiguous, legible |
| PLACE-5 | 7(1) | Packages ≤5 cm³ capacity: PDP may be a card/tape affixed to package |

---

## 9. WHOLESALE PACKAGE DECLARATIONS (Rule 24) — separate check set for B2B packs

If package is a "wholesale package" (contains ≥10 retail packs, OR intended for an intermediary, not sold to a single consumer):
- WS-1: Name & address of manufacturer/importer/packer
- WS-2: Identity of commodity
- WS-3: Total number of retail packages inside OR net quantity of commodity in standard units
(Full Chapter II declaration set is NOT required on wholesale packages — don't cross-apply Section 1 rules here)

---

## 10. PRICE-REVISION EDGE CASE (Rule 18(3)) — for dashboard "tax revision" scenarios
If tax on a pre-packed commodity changes after packing:
- Manufacturer must publish revised price via ≥2 newspaper ads + notices to dealers/Controller (not required for state-tax-only revisions)
- Price difference (old label vs revised) must not exceed the actual tax change amount
- Only applies to stock packed in the month of tax change or the following month
- Lower revised prices always apply immediately regardless of pack month

---

## 11. PENALTIES (Rule 32) — for report/violation-summary generator

| Violation type | Fine |
|---|---|
| Contravention of Rules 27–31 (registration) | ₹4,000 |
| Any other rule contravention with no specified penalty | ₹2,000 |

(Note: these are rule-level fines under the 2011 Rules; your compliance report should cite rule number + this fine as the "regulatory reference," while noting actual enforcement/penalty amounts may have been revised by later amendments not in this document — flag as "verify current fine schedule" if your report is meant for real enforcement use.)

---

## 12. SUGGESTED VALIDATION ENGINE OUTPUT SCHEMA

```json
{
  "product_id": "string",
  "scan_timestamp": "ISO8601",
  "scope_check": { "in_scope": true, "reason": "" },
  "declarations": {
    "manufacturer_address": { "present": true, "text": "", "rule": "6(1)(a)" },
    "commodity_name": { "present": true, "rule": "6(1)(b)" },
    "net_quantity": { "present": true, "value": "", "unit": "", "rule": "6(1)(c)" },
    "mfg_date": { "present": true, "exempt": false, "rule": "6(1)(d)" },
    "mrp": { "present": true, "value": "", "format_valid": true, "rule": "6(1)(e), 2(m)" },
    "dimensions": { "applicable": false },
    "consumer_care": { "present": true, "rule": "6(2)" }
  },
  "font_checks": { "numeral_height_mm": 0.0, "required_min_mm": 0.0, "pass": true, "contrast_pass": true },
  "quantity_checks": { "unit_correct": true, "misleading_words_found": [], "standard_size_match": true },
  "violations": [ { "rule_id": "", "rule_ref": "", "description": "", "severity": "" } ],
  "overall_status": "COMPLIANT | NON_COMPLIANT | PARTIAL | OUT_OF_SCOPE"
}
```

---

## 13. IMPORTANT CAVEATS FOR YOUR TEAM (things judges will likely probe)

1. **This PDF is the 2011 Rules as amended up to late 2011/2012.** The Legal Metrology (Packaged Commodities) Rules were further amended multiple times after 2012 (e.g., 2017 amendments added country-of-origin/QR code style requirements in later years, and MRP/unit-sale-price display rules were tightened). For a hackathon demo this document is sufficient, but say explicitly in your PPT/report that your rule engine is versioned against "LM(PC) Rules 2011 (as amended up to 2012)" and is designed to be **rule-table-driven** so newer amendments can be added without re-architecting — this is a strong differentiator to mention to judges.
2. Font-size measurement from a photo requires you to know the real-world scale (a reference object, or the DPI/known package dimension) — call this out as a known technical constraint in your submission; a common workaround is asking the user to also input a reference dimension or photograph with a coin/scale reference.
3. Many checks (Sections 7, 10, 11) are **not label-scannable** — they need lab/physical verification or officer input. Design your dashboard to separate "auto-scanned" checks from "manual/physical-inspection" checks so you don't overclaim full automation.
4. Rule 26(a)'s 10–20g/ml proviso and the Second Schedule "non-standard size" disclaimer were **withdrawn effective 01.07.2012** — decide and document which rule version you're validating against, since including a repealed clause as a hard-fail would be factually wrong in front of judges from DoCA.
