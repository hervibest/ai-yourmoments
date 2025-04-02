import os
import cv2
import requests
import json
import datetime
import ulid
import time


from internal.config.celery_config import celery_app
from internal.config.minio_config import minio_client, BUCKET_NAME
from internal.services.face_recognizer_service import FaceRecognizer
from internal.repository.ai_repository import VectorRepository
from internal.adapter.photo_service import create_user_similar, create_user_similar_facecam
from internal.dependency import get_face_recognizer, get_vector_repository


class AIUseCase:
    # def __init__(self, detector: FaceRecognizer, repository: VectorRepository):
    #     self.detector = detector
    #     self.repository = repository

    def process_photo(self, photo_id: str, file_url: str):
        """Push processing task to Celery worker"""
        # download_and_process_photo_task.delay(photo_id, file_url)
        download_and_process_photo_task(photo_id, file_url)

        return True, ""
    
    def process_facecam(self, user_id: str, file_url: str):
        """Push processing task to Celery worker"""
        # download_and_process_photo_task.delay(photo_id, file_url)
        download_and_process_facecam_task(user_id, file_url)

        return True, ""


# @celery_app.task


def download_and_process_photo_task(photo_id: str, file_url: str):
    print("test")
    """Download file dan simpan ke disk sementara, lalu masukkan ke queue AI worker."""
    try:
        save_path = f"/tmp/{photo_id}.jpg"
        response = requests.get(file_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

        process_photo_task(photo_id, save_path)

    except Exception as e:
        print(f"Error downloading file {photo_id}: {str(e)}")
        
def download_and_process_facecam_task(user_id: str, file_url: str):
    print("test facecam")
    """Download file dan simpan ke disk sementara, lalu masukkan ke queue AI worker."""
    try:
        save_path = f"/tmp/{user_id}.jpg"
        response = requests.get(file_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

        process_facecam_task(user_id, save_path)

    except Exception as e:
        print(f"Error downloading file {user_id}: {str(e)}")


# @celery_app.task
def process_photo_task(photo_id: str, file_path: str):
    SIMILARITY_THRESHOLD = 0.3
    try:
        start_total = time.perf_counter()

        t0 = time.perf_counter()
        recognizer = get_face_recognizer()
        repository = get_vector_repository()
        print(
            f"[Time] Load recognizer & repository: {time.perf_counter() - t0:.4f}s")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        response = {"photo_id": photo_id, "user_similar": []}

        t1 = time.perf_counter()
        bounding_boxes, embeddings, original_image = recognizer.process_faces(
            file_path, photo_id)
        print(
            f"[Time] Face detection + embedding: {time.perf_counter() - t1:.4f}s")

        t2 = time.perf_counter()
        if embeddings:
            for emb_photo_id, face_id, embedding in embeddings:
                repository.store_kameramen_embedding(
                    emb_photo_id, face_id, embedding)
                matched_user_id, similarity = repository.search_similar_faces(
                    embedding)
                if matched_user_id and similarity >= SIMILARITY_THRESHOLD:
                    similarity_level = get_similarity_level(similarity)
                    new_ulid = ulid.ulid()
                    response["user_similar"].append({
                        "id": new_ulid,
                        "photo_id": emb_photo_id,
                        "user_id": matched_user_id,
                        "similarity": similarity,
                        "similarity_level": similarity_level,
                        "created_at": now,
                        "updated_at": now
                    })
        print(
            f"[Time] Store embedding + similarity search: {time.perf_counter() - t2:.4f}s")

        t3 = time.perf_counter()
        for (x1, y1, x2, y2) in bounding_boxes:
            cv2.rectangle(original_image, (int(x1), int(y1)),
                          (int(x2), int(y2)), (0, 255, 0), 2)
        processed_file_path = f"/tmp/{photo_id}_processed.jpg"
        cv2.imwrite(processed_file_path, original_image)
        print(
            f"[Time] Draw bounding box + save image: {time.perf_counter() - t3:.4f}s")

        t4 = time.perf_counter()
        minio_filename = f"{photo_id}_processed.jpg"
        upload_result = minio_client.fput_object(
            BUCKET_NAME, minio_filename, processed_file_path)
        file_with_bounding_url = f"{BUCKET_NAME}/{minio_filename}"
        file_size = os.path.getsize(processed_file_path)
        print(f"[Time] Upload to MinIO: {time.perf_counter() - t4:.4f}s")

        processed_photo_ulid = ulid.ulid()
        processed_photo_detail = {
            "id": processed_photo_ulid,
            "photo_id": photo_id,
            "file_name": minio_filename,
            "file_key": minio_filename,
            "size": file_size,
            "url": file_with_bounding_url,
            "your_moments_type": "YOU",
            "created_at": now,
            "updated_at": now
        }
        response["processed_photo_detail"] = processed_photo_detail

        t5 = time.perf_counter()
        os.remove(file_path)
        os.remove(processed_file_path)
        print(f"[Time] Remove temp files: {time.perf_counter() - t5:.4f}s")

        t6 = time.perf_counter()
        grpc_response = create_user_similar(response)
        print(f"[Time] gRPC call: {time.perf_counter() - t6:.4f}s")

        print("[Time] Total time:", time.perf_counter() - start_total, "seconds")
        return True, response

    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}


# @celery_app.task
def process_facecam_task(user_id: str, file_path: str):
    # what to do, tanpa box,
    SIMILARITY_THRESHOLD = 0.5
    """Process file yang sudah didownload: deteksi wajah, komparasi embedding, upload hasil."""
    try:
        start_total = time.perf_counter()

        t0 = time.perf_counter()
        recognizer = get_face_recognizer()
        repository = get_vector_repository()
        print(
            f"[Time] Load recognizer & repository: {time.perf_counter() - t0:.4f}s")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        t1 = time.perf_counter()

        response = {
            "user_id": user_id,
            "user_similar": []
        }

        bounding_boxes, embeddings, original_image = recognizer.process_faces(
            file_path, user_id)
        t2 = time.perf_counter()
        if embeddings:
            for user_id, face_id, embedding in embeddings:
                try:
                    repository.store_profile_embedding(user_id, embedding)
                    print(f"Process: user_id={user_id}")

                    results = repository.search_similar_photo(embedding)

                    if results:
                        for matched_photo_id, matched_face_id, similarity in results[:5]:
                            if similarity >= SIMILARITY_THRESHOLD:
                                similarity_level = get_similarity_level(similarity)
                                new_ulid = ulid.ulid()
                                response["user_similar"].append({
                                    "id": new_ulid,
                                    "photo_id": matched_photo_id,
                                    "user_id": user_id,
                                    "similarity": similarity,
                                    "similarity_level": similarity_level,
                                    "created_at": now,
                                    "updated_at": now
                                })
                except Exception as e:
                    print(f"❌ Error processing user_id {user_id}: {e}")
        # print(response["user_similar"])
        # repository.save_comparison_result(user_id, response["photo_matched"])
        print(f"[Time] Store embedding + similarity search: {time.perf_counter() - t2:.4f}s")
        
        processed_facecam_ulid = ulid.ulid()
        processed_facecam = {
            "id": processed_facecam_ulid,
            "user_id": user_id,
            "is_processed": True,
            "updated_at": now
        }
        response["processed_facecam"] = processed_facecam
        
                
        t3 = time.perf_counter()
        os.remove(file_path)
        print(f"[Time] Remove temp files: {time.perf_counter() - t3:.4f}s")
        
        t4 = time.perf_counter()
        grpc_response = create_user_similar_facecam(response)
        print(f"[Time] gRPC call: {time.perf_counter() - t4:.4f}s")

        print("[Time] Total time:", time.perf_counter() - start_total, "seconds")
        return True, response



    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}

def get_similarity_level(similarity):
    if 0.35 <= similarity < 0.38: return 1
    elif 0.38 <= similarity < 0.41: return 2
    elif 0.41 <= similarity < 0.44: return 3
    elif 0.44 <= similarity < 0.47: return 4
    elif 0.47 <= similarity < 0.50: return 5
    elif similarity >= 0.50: return 6
    else: return ""       