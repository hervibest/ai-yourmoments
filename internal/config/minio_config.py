from minio import Minio
import os

# Konfigurasi MinIO
MINIO_ENDPOINT = "127.0.0.1:9000"
MINIO_ACCESS_KEY = "2XUR7xvdJXRjb6TJZIPf"
MINIO_SECRET_KEY = "nsbOGZ1SbH54dIKzRJyNlF3ni1EQIeVWd6pPLHru"
BUCKET_NAME = "yourmoments"
REGION = "ind-yogyakarta"

try:
    # Inisialisasi MinIO client
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,  # Set True jika menggunakan HTTPS
        region=REGION
    )

    # Tes koneksi dengan mencoba mendapatkan daftar bucket
    minio_client.list_buckets()
    print("✅ MinIO Connected!")

    # Pastikan bucket tersedia
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)
        print(f"✅ Bucket '{BUCKET_NAME}' dibuat.")
    else:
        print(f"✅ Bucket '{BUCKET_NAME}' sudah ada.")

except Exception as e:
    print(f"Gagal terhubung ke MinIO: {e}")
