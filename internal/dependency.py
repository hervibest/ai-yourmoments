from internal.config.minio_config import minio_client
from internal.pb import photo_pb2_grpc  # pastikan ini path yang sesuai
from internal.repository.ai_repository import VectorRepository
from internal.services.face_recognizer_service import FaceRecognizer

import os
import grpc
from google.protobuf.timestamp_pb2 import Timestamp
import consul


_face_recognizer = None
_vector_repository = None
_grpc_stub = None

def get_face_recognizer():
    global _face_recognizer
    if _face_recognizer is None:
        _face_recognizer = FaceRecognizer()
    return _face_recognizer

def get_vector_repository():
    global _vector_repository
    if _vector_repository is None:
        _vector_repository = VectorRepository()
    return _vector_repository

def get_photo_service_stub():
    global _grpc_stub
    if _grpc_stub is not None:
        return _grpc_stub

    try:
        # Ambil konfigurasi Consul dan nama service dari environment
        consul_host = os.getenv("CONSUL_HOST", "localhost")
        consul_port = int(os.getenv("CONSUL_PORT", 8500))
        photo_svc_name = os.getenv("PHOTO_SVC_NAME", "photo-svc")

        print(f"🔍 Query ke Consul: {photo_svc_name} di {consul_host}:{consul_port}")
        c = consul.Consul(host=consul_host, port=consul_port)

        services = c.agent.services()
        photo_service = next(
            (svc for svc in services.values() if svc["Service"] == photo_svc_name),
            None
        )

        if not photo_service:
            raise RuntimeError(f"❌ Service '{photo_svc_name}' tidak ditemukan di Consul.")

        address = photo_service["Address"]
        port = photo_service["Port"]
        target = f"{address}:{port}"
        print(f"🔌 Membuat gRPC channel ke {target}")

        channel = grpc.insecure_channel(target)
        grpc.channel_ready_future(channel).result(timeout=3)
        print("✅ gRPC channel siap")

        _grpc_stub = photo_pb2_grpc.PhotoServiceStub(channel)
        return _grpc_stub

    except Exception as e:
        print(f"❌ Gagal membuat stub gRPC dari Consul: {e}")
        raise