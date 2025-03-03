import os
import cv2
import numpy as np
from celery_config import celery_app
from services.downloader import FileDownloader
from services.face_detector import FaceDetector
from services.face_embedder import FaceEmbedder
from repositories.ai_repository import AIRepository
from minio_config import minio_client, BUCKET_NAME
from sklearn.metrics.pairwise import cosine_similarity

class AIUseCase:
    def __init__(self, downloader: FileDownloader, detector: FaceDetector, embedder: FaceEmbedder, repository: AIRepository):
        self.downloader = downloader
        self.detector = detector
        self.embedder = embedder
        self.repository = repository

    def process_file(self, file_id: str, file_url: str):
        """Push processing task to Celery worker"""
        process_file_task.delay(file_id, file_url)
        return True, "File processing started"

@celery_app.task
def process_file_task(file_id: str, file_url: str):
    """Actual file processing (executed by Celery worker)"""
    try:
        downloader = FileDownloader()
        detector = FaceDetector()
        embedder = FaceEmbedder()
        repository = AIRepository()

        file_path = downloader.download(file_url)
        faces = detector.detect_faces(file_path)
        
        if not faces:
            return False, "No faces detected"

        embeddings = [embedder.extract_embedding(face) for face in faces]
        repository.store_embeddings(file_id, embeddings)
        
        os.remove(file_path)  # Clean up
        return True, "File processed successfully"

    except Exception as e:
        return False, f"Error processing file: {str(e)}"
