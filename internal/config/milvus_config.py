import os
from pathlib import Path
from dotenv import load_dotenv
from pymilvus import connections

# Muat .env dari root folder (my_app/.env)
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

# Ambil konfigurasi Milvus
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

try:
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    print(f"✅ Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
except Exception as e:
    print(f"❌ Failed to connect to Milvus: {e}")
