import os
from minio import Minio
from dotenv import load_dotenv
from pathlib import Path

# Muat .env dari root direktori (naik 2 folder dari file ini)
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

# Ambil dari environment
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
REGION = os.getenv("REGION")

try:
    # Inisialisasi MinIO client
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
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
    print(f"❌ Gagal terhubung ke MinIO: {e}")
