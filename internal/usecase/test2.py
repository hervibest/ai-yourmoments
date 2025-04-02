import os
import cv2
import json
import numpy as np
from internal.config.minio_config import minio_client, BUCKET_NAME
from internal.services.face_recognizer_service import FaceRecognizer
from internal.repository.ai_repository import VectorRepository
from internal.dependency import get_face_recognizer, get_vector_repository
# class AIUseCase:
#     def __init__(self, detector: FaceRecognizer, repository: AiRepository):
#         self.detector = detector
#         self.repository = repository

#     def process_file(self, file_id: str, file_url: str):
#         """Push processing task to Celery worker"""
#         download_file_task.delay(file_id, file_url)
#         return True, "File processing started"


def process_file_profile_task(user_id: str, file_path: str):
    SIMILARITY_THRESHOLD = 0.01
    """Process file yang sudah didownload: deteksi wajah, komparasi embedding, upload hasil."""
    try:
        recognizer = get_face_recognizer()
        repository = get_vector_repository()

        response = {
            "user_id": user_id,
            "photo_matched": []
        }

        bounding_boxes, embeddings = recognizer.process_faces(
            file_path, user_id)

        if not embeddings:
            print(json.dumps(response))
        else:
            for photo_id, face_id, embedding in embeddings:
                repository.store_profile_embedding(user_id, embedding)

                results = repository.search_similar_photo(embedding)
                if results:
                    for photo_id, face_id, distance in results:
                        response["photo_matched"].append(photo_id)
                        print(
                            f"Ini adalah matched foto {photo_id}, face ID {face_id}, distance {distance}")
                    else:
                        print("Tidak ada wajah yang cocok dengan threshold > 0.5")

        # repository.save_comparison_result(user_id, response["photo_matched"])

        # os.remove(file_path)

        return True, response

    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}


file_id = "1"

script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, "photo/tam.jpg")
result, response = process_file_profile_task(file_id, image_path)

print("Success:", result)
print("Response:", response)
