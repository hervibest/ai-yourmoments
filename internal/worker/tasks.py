import requests
import os
from celery_config import celery_app
from application.usecase import AIUseCase
from infrastructure.file_downloader import FileDownloader
from infrastructure.face_detector import FaceDetector
from infrastructure.face_embedder import FaceEmbedder
from infrastructure.ai_repository_impl import AIRepositoryImpl
from infrastructure.minio_client import MinIOClient

@celery_app.task
def download_file_task(file_id: str, file_url: str):
    """Download file dan simpan ke disk sementara, lalu masukkan ke queue AI worker."""
    try:
        save_path = f"/tmp/{file_id}.jpg"
        response = requests.get(file_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

        # Kirim ke worker AI setelah download selesai
        process_file_task.delay(file_id, save_path)

    except Exception as e:
        print(f"Error downloading file {file_id}: {str(e)}")

@celery_app.task
def process_file_task(file_id: str, file_path: str):
    """Process AI setelah file didownload"""
    detector = FaceDetector()
    embedder = FaceEmbedder()
    repository = AIRepositoryImpl()
    minio_client = MinIOClient()

    usecase = AIUseCase(detector, embedder, repository, minio_client)
    success, message = usecase.process_file(file_id, file_path)

    print(f"Processing {file_id}: {message}")
