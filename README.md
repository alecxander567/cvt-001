# Custom Vision Tagger

A full-stack web application for intelligent image recognition, organization, and comparison.

---

## 🌐 Live Demo
Try it here:

* URL: [https://your-frontend-url.vercel.app](https://cvt-client.vercel.app)

---

🚀 Features

🔐 Authentication system (JWT-based)

🖼️ Image upload and storage (Cloudinary)

📂 Album management (create, delete, organize)

🔍 Image-to-image comparison

🆚 Image-to-album comparison 

🗂️ Archive system (soft delete & restore)

📊 Activity tracking

---

## 🏗️ Tech Stack

### Frontend

* React.js
* JavaScript
* Tailwind CSS

### Backend

* FastAPI (Python)
* Supabase (Database & Auth)

### Machine Learning

* PyTorch
* Torchvision (MobileNetV2 - pretrained)
* Feature Embeddings (1280-dim vectors)
* Cosine Similarity for image comparison
* Lazy model loading for optimized deployment (Render-friendly)

---

## 📁 Project Structure

```
frontend/
  ├── components/
  ├── pages/
  ├── hooks/
  └── services/

backend/
  ├── routes/
  ├── models/
  ├── utils/
  └── main.py
```

## 🧠 How It Works

1. Users upload images through the frontend
2. Images are stored in Cloudinary
3. Backend processes images using TensorFlow
4. Extracted features are used for comparison
5. Results are returned and displayed in the UI

---

## 📄 License

This project is licensed under the MIT License.

