from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)


class VectorRepository:
    def __init__(self):
        """
        Repository untuk menyimpan embedding wajah ke dua koleksi di Milvus.
        """
        print("AI Init - Refresh Collections")

        # Koneksi ke Milvus
        connections.connect("default", host="localhost", port="19530")

        # Hapus koleksi jika sudah ada
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
        self.face_recognition_collection.create_index("embedding", index_params)

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

    def store_profile_embedding(self, user_id, embedding):
        """
        Simpan embedding wajah dari foto kameramen.
        """
        self.face_recognition_collection.load()
        self.face_recognition_collection.insert([[user_id], [embedding]])
        print(f"Embedding profile {user_id} - disimpan.")

    def store_kameramen_embedding(self, photo_id, face_id, embedding):
        """
        Simpan embedding wajah dari foto kameramen.
        """
        self.kameramen_collection.load()
        
        self.kameramen_collection.insert([[photo_id], [face_id], [embedding]])
        print(f"Embedding kameramen {photo_id} - {face_id} disimpan.")    

    def search_similar_faces(self, embedding, top_k=1):
        """
        Mencari user_id di face_recognition yang memiliki embedding paling mirip dengan yang diberikan.
        """
        if not utility.has_collection("face_recognition"):
            print("Koleksi face_recognition tidak ditemukan di Milvus.")
            return None
        
        self.face_recognition_collection.load()
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        search_result = self.face_recognition_collection.search(
            [embedding], "embedding", search_params, top_k, output_fields=["user_id"]
        )

        if search_result and len(search_result[0]) > 0:
            best_match = search_result[0][0]
            return best_match.entity.get("user_id"), best_match.distance
        return None, None
    
    def search_similar_photo(self, embedding, top_k=10):
        """Cari wajah yang mirip berdasarkan embedding"""
        print("Hitung similarity")
        collection_name = "kameramen_faces"

        # Periksa apakah koleksi tersedia
        if not utility.has_collection(collection_name):
            print(f"Koleksi {collection_name} tidak ditemukan di Milvus.")
            return []

        try:
            # Ambil koleksi dan lakukan pencarian
            self.kameramen_collection.load()

            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
            search_result = self.kameramen_collection.search(
                [embedding], 
                "embedding", 
                search_params, 
                top_k, 
                output_fields=["photo_id", "face_id"]
            )

            # Ambil hasil yang memiliki distance > 0.35
            filtered_results = [
                (match.entity.photo_id, match.entity.face_id, match.distance)
                for match in search_result[0]
                if match.distance > 0.35
            ]

            return filtered_results  # List of tuples (photo_id, face_id, distance)

        except Exception as e:
            print(f"Error: {e}")
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