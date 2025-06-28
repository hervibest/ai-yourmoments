import os
import cv2
import requests
import json
import datetime
from ulid import ULID
import time
from typing import List
from minio.error import S3Error
import asyncio
# from internal.config.celery_config import celery_app
from internal.config.minio_config import minio_client, BUCKET_NAME
from internal.publisher.jetstream import publish_json_to_jetstream_single,publish_json_to_jetstream_bulk, publish_json_to_jetstream_facecam
from internal.services.face_recognizer_service import FaceRecognizer
from internal.repository.ai_repository import VectorRepository
from internal.adapter.photo_service import create_user_similar, create_user_similar_facecam, build_bulk_user_similar_request
from internal.dependency import get_face_recognizer, get_vector_repository

from internal.model.ai_model import AIBulkPhoto, AIPhoto

import numpy as np



class AIUseCase:
    # def __init__(self, detector: FaceRecognizer, repository: VectorRepository):
    #     self.detector = detector
    #     self.repository = repository

    async def process_photo(self, photo_id: str, creator_id: str, file_url: str, original_filename: str):
        """Push processing task to Celery worker"""
        # download_and_process_photo_task.delay(photo_id, file_url)
        await download_and_process_photo_task(photo_id, creator_id, file_url, original_filename)

        return True, ""
    
    async def process_facecam(self, user_id: str, creator_id: str, file_url: str):
        """Push processing task to Celery worker"""
        # download_and_process_photo_task.delay(photo_id, file_url)
        await download_and_process_facecam_task(user_id, creator_id, file_url)

        return True, ""
    
    async def process_photo_bulk(self, process_bulk_photo: AIBulkPhoto, process_photo_list: List[AIPhoto]):
        print("Accesed process_photo_bulk")
        print(process_photo_list)
        """Push processing task to Celery worker"""
        # download_and_process_photo_task.delay(photo_id, file_url)
        await  process_photo_bulk_usecase(process_bulk_photo, process_photo_list)
        return True, ""

def build_bulk_user_similar_payload(process_bulk_photo, bulk_results: List[dict]) -> dict:
    bulk_user_similar_photos = []

    for result in bulk_results:
        photo_detail = result["photo_detail"]
        user_similar_list = result["user_similar_photo"]

        photo_detail_json = {
            "id": photo_detail.get("id", ""),
            "photo_id": photo_detail.get("photo_id", ""),
            "file_name": photo_detail.get("file_name", ""),
            "file_key": photo_detail.get("file_key", ""),
            "size": photo_detail.get("size", 0),
            "type": photo_detail.get("type", ""),
            "checksum": photo_detail.get("checksum", ""),
            "width": photo_detail.get("width", 0),
            "height": photo_detail.get("height", 0),
            "url": photo_detail.get("url", ""),
            "your_moments_type": photo_detail.get("your_moments_type", ""),
            "created_at": iso_format_or_now(photo_detail.get("created_at")),
            "updated_at": iso_format_or_now(photo_detail.get("updated_at")),
        }

        user_similar_photos = []
        for user_sim in user_similar_list:
            user_similar_photos.append({
                "id": user_sim.get("id", ""),
                "photo_id": user_sim.get("photo_id", ""),
                "user_id": user_sim.get("user_id", ""),
                "similarity": user_sim.get("similarity_level", 0),
                "is_wishlist": user_sim.get("is_wishlist", False),
                "is_resend": user_sim.get("is_resend", False),
                "is_cart": user_sim.get("is_cart", False),
                "is_favorite": user_sim.get("is_favorite", False),
                "created_at": iso_format_or_now(user_sim.get("created_at")),
                "updated_at": iso_format_or_now(user_sim.get("updated_at")),
            })

        bulk_user_similar_photos.append({
            "photo_detail": photo_detail_json,
            "user_similar_photo": user_similar_photos
        })

    payload = {
        "bulk_photo": {
            "id": process_bulk_photo.id,
            "creator_id": process_bulk_photo.creator_id,
            "bulk_photo_status": "SUCCESS"
        },
        "bulk_user_similar_photo": bulk_user_similar_photos
    }

    return payload

async def process_photo_bulk_usecase(process_bulk_photo: AIBulkPhoto, process_photo_list: List[AIPhoto]):
    try:
        """Process banyak foto, kumpulkan hasil, lalu kirim 1x bulk gRPC"""
        bulk_user_similar_photos = []
        """Process banyak foto, kumpulkan hasil, lalu kirim 1x bulk gRPC"""
        print("Accessed process_photo_bulk_usecase")
        print(f"Total photos: {len(process_photo_list)}")


        
        print("process_photo_bulk_usecase")

        for photo in process_photo_list:
            photo_id = photo.id
            file_url = photo.compressed_url or photo.collection_url  # fallback kalau compressed kosong
            original_filename = photo.original_filename   # fallback kalau compressed kosong
            
            print(photo)
            print(photo_id)
            print(file_url)
            

            # Proses download dan deteksi wajah
            success, response = download_and_process_photo_task_without_grpc(photo_id, process_bulk_photo.creator_id, file_url, original_filename)

            if not success:
                print(f"Failed processing {photo_id}: {response}")
                continue  # Skip foto gagal

            bulk_user_similar_photos.append({
                "photo_detail": response["processed_photo_detail"],
                "user_similar_photo": response["user_similar"]
            })

        # Kalau sudah semua diproses
        json_payload = build_bulk_user_similar_payload(process_bulk_photo, bulk_user_similar_photos)
        print("Sending bulk user similar photos to JetStream...")
        await publish_json_to_jetstream_bulk(json_payload)
        print("Bulk user similar photos sent successfully.")

    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}

# @celery_app.task


async def download_and_process_photo_task(photo_id: str, creator_id: str, file_url: str, original_filename: str):
    print("test")
    """Download file dan simpan ke disk sementara, lalu masukkan ke queue AI worker."""
    try:
        save_path = f"/tmp/{photo_id}.jpg"
        response = requests.get(file_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

        await process_photo_task(photo_id, creator_id, save_path, original_filename)

    except Exception as e:
        print(f"Error downloading file {photo_id}: {str(e)}")
        
async def download_and_process_facecam_task(user_id: str, creator_id: str, file_url: str):
    print("test facecam")
    """Download file dan simpan ke disk sementara, lalu masukkan ke queue AI worker."""
    try:
        save_path = f"/tmp/{user_id}.jpg"
        response = requests.get(file_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

        await process_facecam_task(user_id, creator_id, save_path)

    except Exception as e:
        print(f"Error downloading file {user_id}: {str(e)}")


def download_and_process_photo_task_without_grpc(photo_id: str, creator_id: str, file_url: str, original_filename: str):
    print("test")
    """Download file dan simpan ke disk sementara, lalu masukkan ke queue AI worker."""
    try:
        save_path = f"/tmp/{photo_id}.jpg"
        response = requests.get(file_url, stream=True)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

        success, response = process_photo_without_grpc_task(photo_id, creator_id, save_path, original_filename)
        return success, response

    except Exception as e:
        return False, {"Error downloading file {photo_id}: {str(e)}"}
  

def process_photo_usecase(photo_id: str,  creator_id: str, file_path: str, original_filename: str) : 
    print("process_photo_usecase")
    
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
                repository.store_kameramen_embedding(emb_photo_id, creator_id, face_id, embedding)
                
                matched_results = repository.search_similar_faces(embedding, creator_id)
                
                for matched_user_id, similarity in matched_results:
                    if matched_user_id and similarity >= SIMILARITY_THRESHOLD:
                        similarity_level = get_similarity_level(similarity)
                        new_ulid =str(ULID())
                        response["user_similar"].append({
                            "id": new_ulid,
                            "photo_id": emb_photo_id,
                            "user_id": matched_user_id,
                            "similarity": similarity,
                            "similarity_level": similarity_level,
                            "created_at": now,
                            "updated_at": now
                        })
                        print(f"[Match] {matched_user_id=} {similarity=:.4f}")

        print(f"[Time] Store embedding + similarity search: {time.perf_counter() - t2:.4f}s")

        t3 = time.perf_counter()
        for (x1, y1, x2, y2) in bounding_boxes:
            cv2.rectangle(original_image, (int(x1), int(y1)),
                          (int(x2), int(y2)), (0, 255, 0), 2)
        processed_file_path = f"/tmp/{photo_id}_processed.jpg"
        cv2.imwrite(processed_file_path, original_image)
        print(
            f"[Time] Draw bounding box + save image: {time.perf_counter() - t3:.4f}s")

        t4 = time.perf_counter()
        if not os.path.exists(processed_file_path):
            raise FileNotFoundError(f"Processed file not found: {processed_file_path}")

        print("[DEBUG] Processed file path:", processed_file_path)
        print("[DEBUG] File exists:", os.path.exists(processed_file_path))

        print("[DEBUG] file_path (original file):", file_path)
        print("[DEBUG] os.path.basename(file_path):", os.path.basename(file_path))

        try:
            processed_file_name, processed_file_key = generate_file_key(
                photo_id, file_path, "processed", original_filename)
        except ValueError as e:
            print(f"[ERROR] ValueError saat generate_file_key: {e}")
            processed_file_name, processed_file_key = None, None
        except TypeError as e:
            print(f"[ERROR] TypeError saat generate_file_key: {e}")
            processed_file_name, processed_file_key = None, None
        except Exception as e:
            print(f"[ERROR] Unexpected error saat generate_file_key: {e}")
            processed_file_name, processed_file_key = None, None

        try:
            upload_result = minio_client.fput_object(
                BUCKET_NAME, processed_file_key, processed_file_path)
            file_with_bounding_url = f"{BUCKET_NAME}/{processed_file_key}"
            print("FILE URL : " + file_with_bounding_url)

            file_size = os.path.getsize(processed_file_path)
            print(f"[Time] Upload to MinIO: {time.perf_counter() - t4:.4f}s")
        except S3Error as e:
            print(f"[ERROR] Failed to upload to MinIO: {e}")
        except FileNotFoundError:
            print(f"[ERROR] Processed file not found: {processed_file_path}")
        except Exception as e:
            print(f"[ERROR] Unexpected error during upload to MinIO: {e}")

        processed_photo_ulid =str(ULID())
        processed_photo_detail = {
            "id": processed_photo_ulid,
            "photo_id": photo_id,
            "file_name": processed_file_name,
            "file_key": processed_file_key,
            "size": file_size,
            "url": file_with_bounding_url,
            "your_moments_type": "YOU",
            "created_at": now,
            "updated_at": now
        }
        print("🧪 processed_photo_detail =", processed_photo_detail)
        print("🧪 type =", type(processed_photo_detail))

        response["processed_photo_detail"] = processed_photo_detail

        t5 = time.perf_counter()
        os.remove(file_path)
        os.remove(processed_file_path)
        print(f"[Time] Remove temp files: {time.perf_counter() - t5:.4f}s")

        t6 = time.perf_counter()
        print(f"[Time] gRPC call: {time.perf_counter() - t6:.4f}s")

        print("[Time] Total time:", time.perf_counter() - start_total, "seconds")
        return response
    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}

def iso_format_or_now(value):
    return value if value else datetime.datetime.utcnow().isoformat()


# @celery_app.task
async def process_photo_task(photo_id: str, creator_id: str, file_path: str, original_filename: str):
    try:
        response = process_photo_usecase(photo_id, creator_id, file_path, original_filename)
        print("Gonna send to GRPC")

        payload = {
            "photo_detail": {
                "id": response["processed_photo_detail"].get("id", ""),
                "photo_id": response["processed_photo_detail"].get("photo_id", ""),
                "file_name": response["processed_photo_detail"].get("file_name", ""),
                "file_key": response["processed_photo_detail"].get("file_key", ""),
                "size": response["processed_photo_detail"].get("size", 0),
                "type": "",
                "checksum": "",
                "width": 0,
                "height": 0,
                "url": response["processed_photo_detail"].get("url", ""),
                "your_moments_type": response["processed_photo_detail"].get("your_moments_type", ""),
                "created_at": iso_format_or_now(response["processed_photo_detail"].get("created_at")),
                "updated_at": iso_format_or_now(response["processed_photo_detail"].get("updated_at")),
            },
            "user_similar_photo": []
        }

        for user_sim in response.get("user_similar", []):
            payload["user_similar_photo"].append({
                "id": user_sim.get("id", ""),
                "photo_id": user_sim.get("photo_id", ""),
                "user_id": user_sim.get("user_id", ""),
                "similarity": user_sim.get("similarity_level", 0),
                "created_at": iso_format_or_now(user_sim.get("created_at")),
                "updated_at": iso_format_or_now(user_sim.get("updated_at")),
            })

        print("Publishing to NATS JetStream...")
        
        await publish_json_to_jetstream_single(payload)
        return True, response

    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}


# @celery_app.task
def process_facecam_usecase(user_id: str, creator_id: str, file_path: str):
    print("processing face cam")
    
    # what to do, tanpa box,
    SIMILARITY_THRESHOLD = 0.3
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
        bounding_boxes, embeddings, original_image = recognizer.process_faces(file_path, user_id)
        t2 = time.perf_counter()

        if embeddings:
            for user_id, face_id, embedding in embeddings:
                try:
                    print(f"\n📌 Start process face_id={face_id}, user_id={user_id}")
                    
                    norm_before = np.linalg.norm(embedding)
                    print(f"🔍 Norm sebelum simpan: {norm_before}")
                    print(f"📷 Embedding preview: {embedding[:5]}")

                    repository.store_profile_embedding(user_id, creator_id, embedding )

                    print(f"✅ Simpan embedding ke koleksi")

                    # Test manual similarity terhadap salah satu entry dulu (bisa kamu hardcode sementara)
                    print("⏳ Cari wajah serupa...")
                    results = repository.search_similar_photo(embedding, creator_id)

                    if not results:
                        print("⚠️ Tidak ada hasil serupa")
                    else:
                        print(f"✅ {len(results)} hasil ditemukan")
                        for matched_photo_id, matched_face_id, similarity in results[:5]:
                            print(f"  → Matched photo_id={matched_photo_id}, face_id={matched_face_id}, similarity={similarity}")

                            if similarity >= SIMILARITY_THRESHOLD:
                                similarity_level = get_similarity_level(similarity)
                                new_ulid =str(ULID())
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

        print(f"[Time] Store embedding + similarity search: {time.perf_counter() - t2:.4f}s")
        print("processing face cam 2")
        
        processed_facecam_ulid =str(ULID())
        processed_facecam = {
            "id": processed_facecam_ulid,
            "user_id": user_id,
            "is_processed": True,
            "updated_at": now
        }
        response["processed_facecam"] = processed_facecam
        
        print(response)
        
                
        t3 = time.perf_counter()
        os.remove(file_path)
        print(f"[Time] Remove temp files: {time.perf_counter() - t3:.4f}s")
        
        print("processing face cam 3")

        print("[Time] Total time:", time.perf_counter() - start_total, "seconds")
        return True, response

    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}
    


def build_facecam_payload(response: dict) -> dict:
    processed_detail = response.get("processed_facecam", {})

    payload = {
        "facecam": {
            "id": processed_detail.get("id", ""),
            "user_id": processed_detail.get("user_id", ""),
            "is_processed": processed_detail.get("is_processed", False),
            "updated_at": iso_format_or_now(processed_detail.get("updated_at")),
        },
        "user_similar_photo": []
    }

    for user_sim in response.get("user_similar", []):
        payload["user_similar_photo"].append({
            "id": user_sim.get("id", ""),
            "photo_id": user_sim.get("photo_id", ""),
            "user_id": user_sim.get("user_id", ""),
            "similarity": user_sim.get("similarity_level", 0),
            "created_at": iso_format_or_now(user_sim.get("created_at")),
            "updated_at": iso_format_or_now(user_sim.get("updated_at")),
        })

    return payload

# @celery_app.task
async def process_facecam_task(user_id: str, creator_id: str, file_path: str):
    try:
        success, response_data = process_facecam_usecase(user_id, creator_id, file_path)
        print("PROCESS FACECAM TASK")

        if success:
            print(response_data)
            json_payload = build_facecam_payload(response_data)
            await publish_json_to_jetstream_facecam(json_payload)

        else:
            print("❌ Facecam processing gagal:", response_data.get("error"))


    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}
    

# @celery_app.task
def process_photo_without_grpc_task(photo_id: str, creator_id: str, file_path: str, original_filename: str):
    print("process_photo_without_grpc_task")
    
    try:
        response = process_photo_usecase(photo_id, creator_id, file_path, original_filename)
        return True, response

    except Exception as e:
        return False, {"error": f"Error processing file: {str(e)}"}


def generate_file_key(photo_id: str, file_path: str, file_type: str, original_filename: str) -> tuple[str, str]:
    """
    Generate standardized file_name and file_key for original/compressed/processed photos.

    Returns: (file_name, file_key)
    """
    print("FILE original name : " + original_filename)
    name, ext = os.path.splitext(original_filename)  # ("DSC_3661", ".jpg")

    new_ulid = str(ULID())
    file_name = f"{name}_{new_ulid}{ext}"
    file_key = f"photo/{photo_id}/{file_type}/{file_name}"
    print("FILE original name : " + file_name)
    return file_name, file_key



def get_similarity_level(similarity):
    if 0.30 <= similarity < 0.32: return 1
    elif 0.32 <= similarity < 0.34: return 2
    elif 0.34 <= similarity < 0.36: return 3
    elif 0.36 <= similarity < 0.38: return 4
    elif 0.38 <= similarity < 0.40: return 5
    elif 0.40 <= similarity < 0.43: return 6
    elif 0.43 <= similarity < 0.46: return 7
    elif 0.46 <= similarity < 0.50: return 8
    elif similarity >= 0.50: return 9
    else: return ""