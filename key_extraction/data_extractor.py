import cv2
import numpy as np
import re
from rapidfuzz import fuzz, process

from ocr_engine import OCRResult

# ==============================================================================
# CONFIGURATION & DICTIONARIES
# ==============================================================================
KEYWORD_DICTIONARY = {
    "mrp": ["mrp", "max retail price", "incl of all taxes", "rs.", "price"],
    "mfg_date": ["mfg date", "date of mfg", "pkd", "packed date", "mfg", "date of packaging"],
    "expiry_date": ["exp date", "expiry date", "use by", "best before", "date of expiry"],
    "country_of_origin": ["country of origin", "made in", "produced in", "product of"],
    "brand_name": ["brand", "brand name", "trademark"],
    "manufacturer": ["mfd by", "manufactured by", "mktd by", "marketed by"]
}

KNOWN_COUNTRIES = [
    # Existing & Common Variations
    "india", "china", "usa", "united states", "america", "vietnam",
    "thailand", "germany", "japan", "taiwan", "korea", "south korea", "malaysia",

    # Asia & Oceania
    "indonesia", "philippines", "singapore", "bangladesh", "sri lanka",
    "pakistan", "australia", "new zealand",

    # Europe
    "uk", "united kingdom", "great britain", "france", "italy", "spain",
    "netherlands", "switzerland", "poland", "sweden", "belgium", "austria",
    "ireland", "denmark", "czech republic", "czechia", "turkey", "turkiye", "russia",

    # Americas
    "canada", "mexico", "brazil", "argentina", "colombia", "chile",

    # Middle East & Africa
    "uae", "united arab emirates", "saudi arabia", "israel", "egypt",
    "south africa", "morocco", "kenya", "nigeria"
]

MONTH_ABBRS = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec"
]

GENERIC_FIELDS = {"brand_name", "manufacturer", "customer_care", "importer_name"}

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
import numpy as np


# ==============================================================================
# DATACLASS DEFINITIONS
# ==============================================================================
@dataclass
class FieldResult:
    anchor_found: Optional[str] = None
    extracted_value: Optional[str] = None
    raw_matched_text: Optional[str] = None
    direction: Optional[str] = None
    distance: Optional[float] = None
    all_valid_candidates: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        if not self.extracted_value:
            return "<Not Extracted>"

        details = []
        if self.anchor_found:
            details.append(f"anchor='{self.anchor_found}'")
        if self.direction:
            details.append(f"dir={self.direction}")
        if self.distance is not None:
            details.append(f"dist={self.distance:.1f}px")

        meta_str = f" ({', '.join(details)})" if details else ""
        return f"'{self.extracted_value}'{meta_str}"


@dataclass
class DataExtractionResult:
    mrp: Optional[FieldResult] = None
    mfg_date: Optional[FieldResult] = None
    expiry_date: Optional[FieldResult] = None
    country_of_origin: Optional[FieldResult] = None
    brand_name: Optional[FieldResult] = None
    manufacturer: Optional[FieldResult] = None
    extra_fields: Dict[str, FieldResult] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Optional[FieldResult]:
        """Maintains dictionary-style lookup (e.g., result['mrp'])."""
        if hasattr(self, key) and key != "extra_fields":
            return getattr(self, key)
        return self.extra_fields.get(key)

    def to_dict(self) -> dict:
        """Converts result object to a clean nested dictionary."""
        return asdict(self)

    @classmethod
    def from_dict_map(cls, results_map: Dict[str, FieldResult]) -> "DataExtractionResult":
        """Factory constructor mapping field dictionary into class attributes."""
        known_fields = {
            "mrp", "mfg_date", "expiry_date",
            "country_of_origin", "brand_name", "manufacturer"
        }
        known_kwargs = {k: v for k, v in results_map.items() if k in known_fields}
        extra_kwargs = {k: v for k, v in results_map.items() if k not in known_fields}
        return cls(**known_kwargs, extra_fields=extra_kwargs)

    def __str__(self) -> str:
        lines = ["=== DataExtractionResult ==="]

        known_fields = [
            ("mrp", "MRP"),
            ("mfg_date", "Mfg Date"),
            ("expiry_date", "Expiry Date"),
            ("country_of_origin", "Country of Origin"),
            ("brand_name", "Brand Name"),
            ("manufacturer", "Manufacturer"),
        ]

        for attr_name, label in known_fields:
            res: Optional[FieldResult] = getattr(self, attr_name)
            val_display = str(res) if res else "<Not Found>"
            lines.append(f"  {label:<18}: {val_display}")

        if self.extra_fields:
            lines.append("  -- Extra Fields --")
            for key, res in self.extra_fields.items():
                val_display = str(res) if res else "<Not Found>"
                lines.append(f"  {key:<18}: {val_display}")

        lines.append("===========================")
        return "\n".join(lines)

# ==============================================================================
# HELPER FUNCTIONS CLASS
# ==============================================================================
class HelperFuncs:
    @staticmethod
    def my_fuzzy_search(alias: str, norm_text: str) -> float:
        """
        Prevents false positives on short acronyms (e.g., 'mrp', 'pkd')
        while preserving fuzzy flexibility on long multi-word labels.
        """
        alias_len = len(alias)

        # Strategy A: Short terms (<= 4 chars like 'mrp', 'rs.')
        if alias_len <= 4:
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, norm_text):
                return 100.0
            return float(fuzz.ratio(alias, norm_text))

        # Strategy B: Longer phrases ('max retail price')
        return float(fuzz.token_set_ratio(alias, norm_text))

    @staticmethod
    def overlap_area(boxA, boxB) -> float:
        """Calculates overlap area between two [x1, y1, x2, y2] bounding boxes."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        return max(0, xB - xA) * max(0, yB - yA)

    @staticmethod
    def repair_ocr_digits(text: str) -> str:
        """
        Fixes common OCR character substitutions in numeric/date contexts:
        'O'/'o' -> '0', 'I'/'l'/'!' -> '1', 'S'/'s' -> '5'
        """
        repaired = text

        # 1. Replace O/o with 0 when adjacent to digits or delimiters
        repaired = re.sub(r'([\d\/\.-])[Oo]', r'\g<1>0', repaired)
        repaired = re.sub(r'[Oo]([\d\/\.-])', r'0\g<1>', repaired)

        # 2. Replace I/l/! with 1 when adjacent to digits
        repaired = re.sub(r'(\d)[Il!]', r'\g<1>1', repaired)
        repaired = re.sub(r'[Il!](\d)', r'1\g<1>', repaired)

        # 3. Replace S/s with 5 when placed between digits
        repaired = re.sub(r'(\d)[Ss](\d)', r'\g<1>5\g<2>', repaired)

        return repaired

    @staticmethod
    def fuzzy_validate_mrp(text: str) -> bool:
        """Matches prices even if currency symbols or digits are partially corrupted."""
        cleaned = HelperFuncs.repair_ocr_digits(text.lower().strip())
        pattern = r'(\d{1,5}(?:\.\d{1,2})?)'
        match = re.search(pattern, cleaned)
        if match:
            val = float(match.group(1))
            return 0.1 <= val <= 500000
        return False

    @staticmethod
    def fuzzy_validate_date(text: str) -> bool:
        """Matches dates with OCR repairs (e.g., '12/2O26', 'N0V 2026', '12 MTHS')."""
        norm = text.lower().strip()
        cleaned = HelperFuncs.repair_ocr_digits(norm)

        # 1. Numeric Date Check (MM/YY, MM/YYYY, DD/MM/YYYY)
        numeric_pattern = r'\b(0?[1-9]|1[0-2])[\/\.-](\d{2,4})\b'
        if re.search(numeric_pattern, cleaned):
            return True

        # 2. Fuzzy Month Check
        words = re.findall(r'[a-z0-9]+', norm)
        for word in words:
            if len(word) >= 3:
                match = process.extractOne(word, MONTH_ABBRS, scorer=fuzz.ratio)
                if match and match[1] >= 75:
                    return True

        # 3. Shelf-life Duration Check ('24 months', '12 mths', '2 yrs')
        shelf_pattern = r'\b(\d{1,2})\s*(m|mth|mths|months|month|yrs|years)\b'
        if re.search(shelf_pattern, cleaned):
            return True

        return False

    @staticmethod
    def fuzzy_validate_country(text: str) -> bool:
        """Fuzzy matches country names (e.g., 'IN0IA' -> 'INDIA')."""
        norm = text.lower().strip()
        clean_text = re.sub(r'[^a-z\s]', '', norm)

        words = clean_text.split()
        for word in words:
            if len(word) >= 3:
                match = process.extractOne(word, KNOWN_COUNTRIES, scorer=fuzz.ratio)
                if match and match[1] >= 75:
                    return True
        return False

    @staticmethod
    def validate_candidate_type_fuzzy(field_name: str, text: str) -> bool:
        """Main fuzzy dispatcher for type validation."""
        if field_name == "mrp":
            return HelperFuncs.fuzzy_validate_mrp(text)
        elif field_name in ["mfg_date", "expiry_date"]:
            return HelperFuncs.fuzzy_validate_date(text)
        elif field_name == "country_of_origin":
            return HelperFuncs.fuzzy_validate_country(text)
        elif field_name in ["brand_name", "manufacturer"]:
            return bool(re.search(r'[a-zA-Z]{2,}', text))
        return True

    @staticmethod
    def clean_value_substring(field_name: str, text: str) -> str:
        """
        Extracts ONLY the value portion when label and value are inside
        the same string (e.g., 'PRODUCT OF INDIA' -> 'INDIA').
        """
        norm = text.lower().strip()
        repaired = HelperFuncs.repair_ocr_digits(norm)

        if field_name == "mrp":
            match = re.search(r'(\d{1,5}(?:\.\d{1,2})?)', repaired)
            return match.group(1) if match else text

        elif field_name in ["mfg_date", "expiry_date"]:
            match = re.search(r'\b(0?[1-9]|1[0-2])[\/\.-](\d{2,4})\b', repaired)
            if match:
                return match.group(0)

            month_match = re.search(
                r'\b(?:\d{1,2}\s*)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\.-]*\d{2,4}\b',
                norm
            )
            if month_match:
                return month_match.group(0)

        elif field_name == "country_of_origin":
            clean_words = re.sub(r'[^a-z\s]', '', norm).split()
            for word in clean_words:
                if len(word) >= 3:
                    match = process.extractOne(word, KNOWN_COUNTRIES, scorer=fuzz.ratio)
                    if match and match[1] >= 75:
                        return word.upper()

        return text

# ==============================================================================
# MAIN DATA EXTRACTOR CLASS
# ==============================================================================
class DataExtractor(HelperFuncs):
    def collect_candidates_filtered(self, ocr_result: OCRResult, score_threshold=80, max_distance_px=200) -> dict:
        """
        Matches anchors using strict matching rules, limits candidate search distance,
        and enforces matching orientation between anchors and candidates.
        """
        if not len(ocr_result.texts):
            return {}

        texts = ocr_result.texts
        scores = ocr_result.scores
        boxes = ocr_result.boxes
        orientations = ocr_result.orientations

        parsed_boxes = []
        for i in range(len(texts)):
            if float(scores[i]) < 0.4:
                continue
            box = boxes[i].astype(int)
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)

            parsed_boxes.append({
                "idx": i,
                "text": str(texts[i]),
                "norm_text": str(texts[i]).lower().strip(),
                "box": box,
                "center": (cx, cy),
                "orientation": str(orientations[i])
            })

        anchors_and_candidates = {}

        for field_name, aliases in KEYWORD_DICTIONARY.items():
            best_anchor = None
            best_score = 0

            # 1. Anchor Identification
            for item in parsed_boxes:
                for alias in aliases:
                    score = self.my_fuzzy_search(alias, item["norm_text"])
                    if score > best_score and score >= score_threshold:
                        best_score = score
                        best_anchor = item

            if not best_anchor:
                continue

            ax1, ay1, ax2, ay2 = best_anchor["box"]
            ah = max(ay2 - ay1, 1)
            aw = max(ax2 - ax1, 1)

            # 2. ROI Boundaries capped by max_distance_px
            roi_right_width = min(int(3.0 * aw), max_distance_px)
            roi_below_height = min(int(2.5 * ah), max_distance_px)

            right_roi = np.array([ax2, ay1 - int(0.2 * ah), ax2 + roi_right_width, ay2 + int(0.2 * ah)])
            below_roi = np.array([ax1 - int(0.2 * aw), ay2, ax2 + int(1.0 * aw), ay2 + roi_below_height])

            candidates = []

            # 3. Collect Candidates within Distance Limit and Matching Orientation
            for item in parsed_boxes:
                if item["idx"] == best_anchor["idx"]:
                    continue

                # Skip spatial matching if candidate has a different orientation than the anchor
                if item["orientation"] != best_anchor["orientation"]:
                    continue

                bx = item["box"]
                dist = float(np.linalg.norm(np.array(item["center"]) - np.array(best_anchor["center"])))

                if dist > max_distance_px:
                    continue

                right_overlap = self.overlap_area(right_roi, bx)
                below_overlap = self.overlap_area(below_roi, bx)

                direction = None
                if right_overlap > 0:
                    direction = "right"
                elif below_overlap > 0:
                    direction = "below"

                if direction:
                    candidates.append({
                        "text": item["text"],
                        "box": bx.tolist(),
                        "direction": direction,
                        "distance": round(dist, 2),
                        "orientation": item["orientation"]
                    })

            candidates.sort(key=lambda c: c["distance"])

            anchors_and_candidates[field_name] = {
                "anchor_text": best_anchor["text"],
                "anchor_box": best_anchor["box"].tolist(),
                "anchor_orientation": best_anchor["orientation"],
                "fuzzy_score": round(best_score, 1),
                "candidates": candidates
            }

        return anchors_and_candidates

    def extract_validated_declarations(self, ocr_result: OCRResult) -> DataExtractionResult:
        """
        Evaluates candidates, completely disabling distance=0 for generic fields
        and only permitting distance=0 on structured fields if an inline value exists.
        Returns a DataExtractionResult object instead of a raw dictionary.
        """
        anchors_and_candidates = self.collect_candidates_filtered(ocr_result)
        field_results: Dict[str, FieldResult] = {}

        for field_name, data in anchors_and_candidates.items():
            candidates = data.get("candidates", [])
            all_candidates_to_check = []
            anchor_text = data["anchor_text"]

            # 1. Evaluate self-candidate (distance=0.0) ONLY for structured fields with inline values
            if field_name not in GENERIC_FIELDS:
                cleaned_anchor_val = self.clean_value_substring(field_name, anchor_text)
                is_inline_value_present = cleaned_anchor_val.lower().strip() != anchor_text.lower().strip()

                if is_inline_value_present and self.validate_candidate_type_fuzzy(field_name, anchor_text):
                    all_candidates_to_check.append({
                        "text": anchor_text,
                        "box": data["anchor_box"],
                        "direction": "self",
                        "distance": 0.0
                    })

            # 2. Append external candidates (distance > 0)
            all_candidates_to_check.extend(candidates)

            valid_candidates = []
            for cand in all_candidates_to_check:
                cand_text = cand["text"]
                if self.validate_candidate_type_fuzzy(field_name, cand_text):
                    cleaned_value = self.clean_value_substring(field_name, cand_text)
                    valid_candidates.append({
                        "raw_text": cand_text,
                        "clean_value": cleaned_value,
                        "direction": cand["direction"],
                        "distance": cand["distance"]
                    })

            best_match = valid_candidates[0] if valid_candidates else None

            field_results[field_name] = FieldResult(
                anchor_found=data["anchor_text"],
                extracted_value=best_match["clean_value"] if best_match else None,
                raw_matched_text=best_match["raw_text"] if best_match else None,
                direction=best_match["direction"] if best_match else None,
                distance=best_match["distance"] if best_match else None,
                all_valid_candidates=[c["clean_value"] for c in valid_candidates]
            )

        return DataExtractionResult.from_dict_map(field_results)

    def extract(self, ocr_result: OCRResult) -> DataExtractionResult:
        return self.extract_validated_declarations(ocr_result)
