# 🧠 AI Face Recognition Service

GPU-accelerated AI service for **face recognition**, **embedding storage**, and **similarity search**, built using `InsightFace`, `Milvus`, and `gRPC`. This service is designed to match faces between **facecam** and **action-shot** photos in real-time using cosine similarity.

---

## 📌 Features

- 🔍 Detect faces and extract 512-d embeddings using `insightface` (with CUDA/GPU support)
- 💾 Store embeddings into Milvus vector database
- 🧠 Perform cosine similarity search to find matched faces
- 🖼️ Draw bounding boxes and upload processed images to object storage (MinIO)
- ⚡ Triggered via gRPC with image URL and file ID

---

## 🧩 Architecture Flow

1. `photo-svc` sends a gRPC request with a photo URL and ID
2. AI service downloads the image
3. Face detection + embedding extraction using InsightFace
4. Embedding is stored into Milvus
5. Milvus performs similarity search using cosine distance
6. Bounding box is drawn and saved
7. Result uploaded to MinIO and returned as metadata

---

## 📂 Example Use Case

```python
# Celery Task Entry Point
def process_photo_task(photo_id: str, file_path: str):
    recognizer = get_face_recognizer()
    repository = get_vector_repository()
    
    bounding_boxes, embeddings, original_image = recognizer.process_faces(file_path, photo_id)

    if embeddings:
        for emb_photo_id, face_id, embedding in embeddings:
            repository.store_kameramen_embedding(emb_photo_id, face_id, embedding)
            matched_user_id, similarity = repository.search_similar_faces(embedding)

            if matched_user_id and similarity >= 0.3:
                # handle matched user
                pass
```
##  🔭 Roadmap
- Optimize CPU-bound steps (e.g., cv2.imwrite, drawing bounding boxes)

- Move image read/save operations to GPU if feasible

- Add database persistence for matched similarity data (MongoDB or other)

- Dockerize the service for portability

- Implement CI/CD (e.g., GitHub Actions)

- Add unit & integration tests

- REST fallback or HTTP healthcheck endpoint


