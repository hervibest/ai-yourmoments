from internal.services.face_recognizer_service import FaceRecognizer
from internal.repository.ai_repository import VectorRepository
from internal.config.minio_config import minio_client
import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from internal.pb import photo_pb2_grpc  # pastikan ini path yang sesuai

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
    try:
        global _grpc_stub
        if _grpc_stub is None:
            target = "localhost:50052"  # Ganti sesuai alamat dan port service kamu
            print(f"🔌 Membuat gRPC channel ke {target}")
            channel = grpc.insecure_channel(target)

            grpc.channel_ready_future(channel).result(timeout=3)  # akan raise jika timeout
            print("✅ gRPC channel siap")
            _grpc_stub = photo_pb2_grpc.PhotoServiceStub(channel)
        return _grpc_stub
        

    except Exception as e:
        print(f"❌ Gagal membuat stub gRPC: {e}")
        raise
