import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import torch
import clip
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing import image as keras_image
from PIL import Image
import requests
from io import BytesIO

_feature_model = MobileNetV2(weights="imagenet", include_top=False, pooling="avg")

_clip_model, _clip_preprocess = clip.load("ViT-B/32")
_clip_model.eval()


def load_image_from_url(url: str) -> Image.Image:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")


def load_image_from_bytes(file_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(file_bytes)).convert("RGB")


def _preprocess_mobilenet(img: Image.Image) -> np.ndarray:
    img = img.resize((224, 224))
    arr = keras_image.img_to_array(img)
    arr = np.expand_dims(arr, axis=0)
    return preprocess_input(arr)


def extract_features(img: Image.Image) -> np.ndarray:
    """Returns 1280-dim float32 vector for cosine similarity."""
    processed = _preprocess_mobilenet(img)
    features = _feature_model.predict(processed, verbose=0)
    return features.flatten()


def extract_clip_features(img: Image.Image) -> np.ndarray:
    """
    Returns a 512-dim CLIP embedding vector.
    CLIP understands image content semantically — works for any object.
    NOT stored in Supabase (computed on the fly during compare).
    """
    image_input = _clip_preprocess(img).unsqueeze(0)
    with torch.no_grad():
        features = _clip_model.encode_image(image_input)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.squeeze(0).numpy()


def clip_object_similarity(img1: Image.Image, img2: Image.Image) -> float:
    """
    Compares two images semantically using CLIP embeddings.
    Returns a score from 0-1. No fixed category list needed.
    >= 0.85 means same type of object.
    """
    feat1 = extract_clip_features(img1)
    feat2 = extract_clip_features(img2)
    return float(np.dot(feat1, feat2))


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def compare_images(
    img1: Image.Image,
    img2: Image.Image,
    similarity_threshold: float = 0.75,
    clip_threshold: float = 0.85,
) -> dict:
    # MobileNetV2 visual similarity
    feat1 = extract_features(img1)
    feat2 = extract_features(img2)
    similarity = cosine_similarity(feat1, feat2)

    clip_score = clip_object_similarity(img1, img2)
    is_match = similarity >= similarity_threshold
    object_match = clip_score >= clip_threshold

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
