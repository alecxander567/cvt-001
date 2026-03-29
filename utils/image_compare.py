import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from tensorflow.keras.preprocessing import image
from PIL import Image
import requests
from io import BytesIO

# Load model once (IMPORTANT: outside functions)
model = MobileNetV2(weights="imagenet", include_top=False, pooling="avg")


def load_image_from_url(url):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert("RGB")
    return img


def load_image_from_bytes(file_bytes):
    img = Image.open(BytesIO(file_bytes)).convert("RGB")
    return img


def preprocess(img):
    img = img.resize((224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    return preprocess_input(img_array)


def extract_features(img):
    processed = preprocess(img)
    features = model.predict(processed)
    return features.flatten()


def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
