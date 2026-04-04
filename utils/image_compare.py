import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import requests
from io import BytesIO

# --- Lazy model loading ---
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        _model.classifier = torch.nn.Identity()
        _model.eval()
    return _model


def load_image_from_url(url: str) -> Image.Image:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")


def load_image_from_bytes(file_bytes: bytes) -> Image.Image:
    return Image.open(BytesIO(file_bytes)).convert("RGB")


def extract_features(img: Image.Image) -> np.ndarray:
    """1280-dim MobileNetV2 embedding."""
    model = _get_model()
    transform = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        features = model(tensor)
        features = features / features.norm(dim=-1, keepdim=True)
    return features.squeeze(0).numpy().astype(np.float32)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def clip_object_similarity(img1: Image.Image, img2: Image.Image) -> float:
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

    similarity = cosine_similarity(feat1, feat2)
    clip_score = similarity

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
