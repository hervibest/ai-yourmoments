import numpy as np
from pymilvus import Collection

class AIRepository:
    def __init__(self):
        self.collection = Collection("face_embeddings")  # Nama koleksi di Milvus

    def store_embeddings(self, file_id, embeddings):
        """Simpan hasil embedding ke Milvus"""
        self.collection.insert([[file_id], embeddings])

    def get_profile_embeddings(self):
        """Ambil semua embedding foto profil user"""
        results = self.collection.query(
            expr="is_profile=True",  # Ambil embedding foto profil user
            output_fields=["user_id", "embedding"]
        )
        return results  # List user_id & embedding

    def save_comparison_result(self, file_id, file_url, similar_users):
        """Simpan hasil komparasi ke database"""
        result = {
            "file_id": file_id,
            "file_with_bounding_url": file_url,
            "user_similar": similar_users
        }
        # Simpan ke DB (contoh pakai MongoDB)
        db.face_results.insert_one(result)
