import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import torch
import clip
from PIL import Image
import requests
from io import BytesIO
from functools import lru_cache

# --- Lazy model loading ---
_clip_model = None
_clip_preprocess = None


def _get_clip():
    global _clip_model, _clip_preprocess
    if _clip_model is None:
        _clip_model, _clip_preprocess = clip.load("RN50", device="cpu")
        _clip_model.eval()
    return _clip_model, _clip_preprocess


def load_image_from_url(url: str) -> Image.Image:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")


def load_image_from_bytes(file_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(file_bytes)).convert("RGB")


def extract_features(img: Image.Image) -> np.ndarray:
    """1024-dim CLIP embedding (RN50)."""
    model, preprocess = _get_clip()
    image_input = preprocess(img).unsqueeze(0)
    with torch.no_grad():
        features = model.encode_image(image_input)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.squeeze(0).numpy().astype(np.float32)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def clip_object_similarity(img1: Image.Image, img2: Image.Image) -> float:
    """
    Now reuses extract_features instead of duplicating logic.
    Since features are already L2-normalized, dot product == cosine similarity.
    """
    feat1 = extract_features(img1)
    feat2 = extract_features(img2)
    return float(np.dot(feat1, feat2))


def compare_images(
    img1: Image.Image,
    img2: Image.Image,
    similarity_threshold: float = 0.75,
    clip_threshold: float = 0.85,
) -> dict:
    feat1 = extract_features(img1)
    feat2 = extract_features(img2)

    # With CLIP, one similarity score covers both cases
    similarity = cosine_similarity(feat1, feat2)
    clip_score = similarity  # same model, no need to compute twice

    is_match = similarity >= similarity_threshold
    object_match = similarity >= clip_threshold

    if is_match:
        verdict = "same_object"
    elif object_match:
        verdict = "same_category_different_instance"
    else:
        verdict = "different"

    return {
        "similarity": round(similarity, 4),
        "clip_score": round(clip_score, 4),
        "is_match": is_match,
        "object_match": object_match,
        "shared_labels": [],
        "verdict": verdict,
    }
