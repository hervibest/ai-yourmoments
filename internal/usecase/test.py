import os
import cv2
import json
import numpy as np
from internal.config.minio_config import minio_client, BUCKET_NAME
from internal.services.face_recognizer_service import FaceRecognizer
from internal.repository.ai_repository import VectorRepository

# class AIUseCase:
#     def __init__(self, detector: FaceRecognizer, repository: AiRepository):
#         self.detector = detector
#         self.repository = repository

#     def process_file(self, file_id: str, file_url: str):
#         """Push processing task to Celery worker"""
#         download_file_task.delay(file_id, file_url)
#         return True, "File processing started"
    

def process_photo_task(file_id: str, file_path: str):
    print("Memproses photo dari kameramen atau creator")
    
    SIMILARITY_THRESHOLD = 0.35  
    
    """Process file yang sudah didownload: deteksi wajah, komparasi embedding, upload hasil."""
    try:
        recognizer = FaceRecognizer()
        repository = VectorRepository()

        response = {
            "file_id": file_id,
            "user_similar": []
        }

        bounding_boxes, embeddings = recognizer.process_faces(file_path, file_id)
        print("Bounding Boxes:", bounding_boxes)

        def get_similarity_level(similarity):
            if 0.35 <= similarity < 0.38:
                return 1
            elif 0.38 <= similarity < 0.41:
                return 2
            elif 0.41 <= similarity < 0.44:
                return 3
            elif 0.44 <= similarity < 0.47:
                return 4
            elif 0.47 <= similarity < 0.50:
                return 5
            elif similarity >= 0.50:
                return 6
            else:
                return ""

        if not embeddings:
            print(json.dumps(response))
        else:
            for photo_id, face_id, embedding in embeddings:
                repository.store_kameramen_embedding(photo_id, face_id, embedding)
                matched_user_id, similarity = repository.search_similar_faces(embedding)
                print(f"{matched_user_id} {similarity}")
                if matched_user_id and similarity >= SIMILARITY_THRESHOLD:
                    similarity_level = get_similarity_level(similarity)
                    response["user_similar"].append({
                        "user_id": matched_user_id,
                        # Jika ingin menampilkan id file yang diproses atau id foto, sesuaikan nilai berikut:
                        "file_id": file_id,
                        "similarity": similarity,
                        "similarity_level": similarity_level
                    })

        # Menggambar bounding boxes pada gambar
        image = cv2.imread(file_path)
        for (x1, y1, x2, y2) in bounding_boxes:
            cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        processed_file_path = f"/tmp/{file_id}_processed.jpg"
        cv2.imwrite(processed_file_path, image)

        minio_filename = f"{file_id}_processed.jpg"
        minio_client.fput_object(BUCKET_NAME, minio_filename, processed_file_path)
        file_with_bounding_url = f"{BUCKET_NAME}/{minio_filename}"

        return True, response

    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}

    
    
file_id = "5"

script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, "photo/Aray5.jpeg")
result, response = process_photo_task(file_id, image_path)

print("Success:", result)
print("Response:", response)