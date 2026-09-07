import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class OCRConfig:
    device: str = "cpu"
    use_angle_cls: bool = True
    lang: str = "en"
    enable_mkldnn: bool = False
    cpu_threads: int = 4
    min_confidence: float = 0.4
    text_detection_model_name="PP-OCRv5_mobile_det"
    text_recognition_model_name="PP-OCRv5_mobile_rec"

# SLM idea is rested for now - also remember 1gb is memory limit
# @dataclass
# class LLMConfig:
#     repo_id: str = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
#     filename: str = "*q4_k_m.gguf"
#     n_ctx: int = 2048
#     n_threads: int = 4
#     temperature: float = 0.0
#     max_tokens: int = 256
#     verbose: bool = False

# TODO: Actually make PreprocessConfig work with the Preprocessor logic
@dataclass
class PreprocessConfig:
    default_preset: str = "standard"
    target_width: int = 1280
    denoise_h: int = 10
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: tuple = (8, 8)
    sharpen: bool = True

@dataclass
class SystemConfig:
    ocr: OCRConfig = field(default_factory=OCRConfig)
    # llm: LLMConfig = field(default_factory=LLMConfig)
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    target_fields: List[str] = field(default_factory=lambda: [
        "brand_name",
        "manufacturer_name",
        "importer_name",
        "mfg_date",
        "expiry_date",
        "mrp",
        "quantity",
        "country_of_origin",
        "customer_care"
    ])

default_config = SystemConfig()
