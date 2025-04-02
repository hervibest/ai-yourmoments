import os
import cv2
import json
import numpy as np
from internal.config.minio_config import minio_client, BUCKET_NAME
from internal.services.face_recognizer_service import FaceRecognizer
from internal.repository.ai_repository import AiRepository

# class AIUseCase:
#     def __init__(self, detector: FaceRecognizer, repository: AiRepository):
#         self.detector = detector
#         self.repository = repository

#     def process_file(self, file_id: str, file_url: str):
#         """Push processing task to Celery worker"""
#         download_file_task.delay(file_id, file_url)
#         return True, "File processing started"


def process_file_profile_task(user_id: str):
    repository = AiRepository()
    repository.get_profile_embedding(user_id)


script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, "running.jpg")
result, response = process_file_profile_task("1")

print("Success:", result)
print("Response:", response)
