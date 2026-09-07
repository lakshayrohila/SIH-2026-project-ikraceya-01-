"""
 - Call `main` function with `input_image_path`.
 - Output is stored to temporarily created csv file.
 - `main` returns name of the output csv file.
"""

import tempfile
import json
import shutil

import cv2
import pandas as pd

from preprocessor import ImagePreprocessor
from ocr_engine import OCREngine
from data_extractor import DataExtractor


from pathlib import Path
TEST_DIR = Path(__file__).resolve().parent / "test"


def extract_keys_from_document(image_path, verbose=False):
    preprocessed_image, _ = ImagePreprocessor().process(image_path)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cv2.imwrite(tmp_path, preprocessed_image)

        ocr_result = OCREngine().predict(tmp_path)

        data_extractor_res = DataExtractor().extract(ocr_result)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if verbose:
        cv2.imwrite(str(TEST_DIR / "preprocess.jpg"), preprocessed_image)

        with open(TEST_DIR / "ocr_result.txt", "w", encoding="utf-8") as f:
            f.write(f"OCR Result:\n\n{str(ocr_result)}")

        with open(TEST_DIR / "data_extractor.txt", "w", encoding="utf-8") as f:
            f.write(f"DataExtractor Result:\n\n{str(data_extractor_res)}")
            formatted_dict = json.dumps(data_extractor_res.to_dict(), indent=2)
            f.write(f"\n\nDataExtractor Result (.to_dict()):\n\n{formatted_dict}")

    return data_extractor_res


def main(image_path, verbose=False):
    res = extract_keys_from_document(image_path, verbose=verbose)
    res_dict = res.to_dict()

    out_dict = {
        key: val.get("extracted_value") if isinstance(val, dict) else None
        for key, val in res_dict.items()
        if key != "extra_fields"
    }

    extra_fields = res_dict.get("extra_fields")
    if isinstance(extra_fields, dict):
        for extra_key, extra_val in extra_fields.items():
            out_dict[extra_key] = extra_val.get("extracted_value") if isinstance(extra_val, dict) else None

    df = pd.DataFrame([out_dict])

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    df.to_csv(tmp_path, index=False)

    if verbose:
        formatted_dict = json.dumps(out_dict, indent=2)
        with open(TEST_DIR / "data_extractor.txt", "w", encoding="utf-8") as f:
            f.write(f"main() -> out_dict:\n\n{formatted_dict}")

        shutil.copy(tmp_path, TEST_DIR / "output.csv")

    return str(tmp_path)


if __name__ == "__main__":
    from urllib.request import urlretrieve

    Path(TEST_DIR).mkdir(parents=True, exist_ok=True)

    INPUT_IMG_PATH = str(TEST_DIR / "input.jpg")

    urlretrieve("https://i.ibb.co/BHZvfR3J/besan.jpg", INPUT_IMG_PATH)

    print(f"main() returned: {main(INPUT_IMG_PATH, verbose=True)}")
