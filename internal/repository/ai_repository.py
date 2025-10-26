from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)
import numpy as np


import os
from pathlib import Path
import time

class VectorRepository:
    def __init__(self):
        MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
        MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

        for _ in range(10):  # Coba maksimal 10 kali
            try:
                connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
                print(f"✅ Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
                break
            except Exception as e:
                print(f"⏳ Waiting for Milvus... ({e})")
                time.sleep(5)
        else:
            raise RuntimeError("❌ Gagal connect ke Milvus setelah 10 kali percobaan")

        # self.refresh_collection("kameramen_faces")
        # self.refresh_collection("face_recognition")

        # Buat ulang koleksi
        self.kameramen_collection = self.create_collection(
            "kameramen_faces",
            [
                FieldSchema(
                    name="photo_id",
                    dtype=DataType.VARCHAR,
                    max_length=50,
                    is_primary=True,
                ),
                FieldSchema(
                    name="creator_id",           # Metadata tambahan
                    dtype=DataType.VARCHAR,
                    max_length=50,
                ),
                FieldSchema(
                    name="face_id",
                    dtype=DataType.INT64
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=512
                ),
            ],
        )

        self.face_recognition_collection = self.create_collection(
            "face_recognition",
            [
                FieldSchema(
                    name="user_id",
                    dtype=DataType.VARCHAR,
                    max_length=50,
                    is_primary=True,
                ),
                FieldSchema(
                    name="creator_id",           # Metadata tambahan
                    dtype=DataType.VARCHAR,
                    max_length=50,
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=512
                ),
            ],
        )

        # Buat indeks untuk pencarian cepat
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128}
        }

        self.kameramen_collection.create_index("embedding", index_params)
        self.face_recognition_collection.create_index(
            "embedding", index_params)

        print("Indeks berhasil dibuat.")

    def refresh_collection(self, collection_name):
        """
        Hapus koleksi jika sudah ada untuk membuat ulang dari awal.
        """
        if utility.has_collection(collection_name):
            print(f"Menghapus koleksi {collection_name}")
            utility.drop_collection(collection_name)

    def create_collection(self, name, fields):
        """
        Membuat koleksi di Milvus jika belum ada.
        """
        schema = CollectionSchema(fields, description=f"{name} collection")
        collection = Collection(name, schema)
        return collection

    def store_profile_embedding(self, user_id, creator_id, embedding):
        """
        Simpan embedding wajah dari foto kameramen.
        """
        print("INI ADALAH STORE PROFILE EMBEDING CREATOR ID: " + creator_id)
        self.face_recognition_collection.load()
        # expr = f'user_id == "{user_id}" and creator_id == "{creator_id}"'
        # old = self.face_recognition_collection.query(expr=expr, output_fields=["pk"])
        # if old:
        #     print("DELETE EXISTING FACECAME EMBEDING WITH CREATOR : " + creator_id + " USER ID: " + user_id)
        #     ids = [r["pk"] for r in old]
        #     self.face_recognition_collection.delete(expr=f'pk in {ids}')

        self.face_recognition_collection.insert([[user_id], [creator_id], [embedding]])
        print(f"Embedding profile {user_id} dengan creator id {creator_id} - disimpan.")

    def store_kameramen_embedding(self, photo_id, creator_id, face_id, embedding):
        """
        Simpan embedding wajah dari foto kameramen.
        """
        print("INI ADALAH STORE KAMERA EMBEDING CREATOR ID: " + creator_id)

        self.kameramen_collection.load()

        self.kameramen_collection.insert([[photo_id], [creator_id], [face_id], [embedding]])
        print(f"Embedding kameramen {photo_id} - {face_id} disimpan.")

    def search_similar_faces(self, embedding, creator_id_to_exclude, top_k=5, similarity_threshold=0.3):
        """
        Mencari user_id di face_recognition yang memiliki embedding paling mirip,
        dengan threshold cosine similarity minimal 0.3, dan mengabaikan embedding milik creator_id tertentu.

        Args:
            embedding (list): Embedding wajah
            creator_id_to_exclude (str): Creator ID yang ingin dikecualikan dari hasil
            top_k (int): Jumlah hasil teratas yang diambil
            similarity_threshold (float): Threshold cosine similarity (semakin tinggi semakin mirip)

        Returns:
            List of tuples: [(user_id, similarity), ...]
        """
        if not utility.has_collection("face_recognition"):
            print("Koleksi face_recognition tidak ditemukan di Milvus.")
            return []

        self.face_recognition_collection.load()

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }

        # Gunakan expr untuk menyaring berdasarkan creator_id
        print("INI ADALAH EXCLUDE CREATOR ID SERACH SIMILAR FACES : " + creator_id_to_exclude)
        expr = f'creator_id != "{creator_id_to_exclude}"'

        search_result = self.face_recognition_collection.search(
            [embedding],
            "embedding",
            search_params,
            top_k,
            expr=expr,
            output_fields=["user_id", "creator_id"]
        )

        similar_faces = []

        if search_result and len(search_result[0]) > 0:
            for match in search_result[0]:
                if match.distance >= similarity_threshold:
                    user_id = match.entity.get("user_id")
                    similar_faces.append((user_id, match.distance))

        return similar_faces


    def search_similar_photo(self, embedding, creator_id_to_exclude, top_k=50):
        """Cari wajah yang mirip berdasarkan embedding, tanpa menyamakan dengan foto dari creator yang sama"""
        print("🔍 Mulai proses pencarian kemiripan wajah")
        collection_name = "kameramen_faces"

        # Periksa apakah koleksi tersedia
        if not utility.has_collection(collection_name):
            print(f"❌ Koleksi {collection_name} tidak ditemukan di Milvus.")
            return []

        try:
            # ❌ Hapus normalisasi agar konsisten dengan search_similar_faces
            # norm = np.linalg.norm(embedding)
            # if norm == 0:
            #     print("❌ Embedding bernilai nol (tidak valid)")
            #     return []
            # embedding = embedding / norm

            self.kameramen_collection.load()
            print(f"📦 Jumlah data dalam koleksi: {self.kameramen_collection.num_entities}")

            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            print("INI ADALAH EXCLUDE CREATOR ID SERACH SIMILAR PHOTO : " + creator_id_to_exclude)

            # Gunakan expr untuk mengecualikan creator_id tertentu
            expr = f'creator_id != "{creator_id_to_exclude}"'

            search_result = self.kameramen_collection.search(
                [embedding],
                "embedding",
                search_params,
                top_k,
                expr=expr,
                output_fields=["photo_id", "face_id", "creator_id"]
            )

            print("📝 Hasil pencarian mentah:")
            results = list(search_result[0]) if hasattr(search_result[0], '__iter__') else search_result[0].to_list()

            for match in results:
                entity = match.entity
                print(
                    f"  → photo_id={entity.get('photo_id')}, face_id={entity.get('face_id')}, creator_id={entity.get('creator_id')}, distance={match.distance}"
                )

            # Gunakan threshold serupa dengan search_similar_faces
            filtered_results = [
                (match.entity.get('photo_id'), match.entity.get('face_id'), match.distance)
                for match in results
                if match.distance >= 0.3
            ]

            print(f"✅ Ditemukan {len(filtered_results)} hasil mirip (distance >= 0.3)")
            return filtered_results

        except Exception as e:
            print(f"❌ Error saat mencari embedding: {e}")
            return []


    def get_profile_embedding(self, user_id):
        """
        Ambil kembali embedding berdasarkan user_id.
        """
        # Pastikan koleksi telah dimuat sebelum melakukan query
        self.face_recognition_collection.load()

        query_result = self.face_recognition_collection.query(
            expr=f"user_id == '{user_id}'",  # Tambahkan tanda kutip
            output_fields=["embedding"]
        )
        print(f"Debug: Query hasil untuk user_id {user_id}: {query_result}")
        return query_result
