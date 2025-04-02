import grpc
import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from internal.pb import photo_pb2
from internal.pb import photo_pb2_grpc
from internal.dependency import get_photo_service_stub

def create_user_similar(response):
    """
    Fungsi untuk memanggil PhotoService menggunakan gRPC dengan data response
    dari proses photo task.
    """
    stub = get_photo_service_stub()

    # Konversi data processed_photo_detail ke message PhotoDetail
    processed_detail = response.get("processed_photo_detail", {})

    def iso_to_timestamp(iso_str):
        dt = datetime.datetime.fromisoformat(iso_str)
        ts = Timestamp()
        ts.FromDatetime(dt)
        return ts

    photo_detail = photo_pb2.PhotoDetail(
        id=processed_detail.get("id", ""),
        photo_id=processed_detail.get("photo_id", ""),
        file_name=processed_detail.get("file_name", ""),
        file_key=processed_detail.get("file_key", ""),
        size=processed_detail.get("size", 0),
        type="",       # jika tidak ada, bisa dikosongkan
        checksum="",   # jika tidak ada, bisa dikosongkan
        width=0,       # sesuaikan jika ada informasinya
        height=0,      # sesuaikan jika ada informasinya
        url=processed_detail.get("url", ""),
        your_moments_type=processed_detail.get("your_moments_type", ""),
        created_at=iso_to_timestamp(processed_detail.get(
            "created_at", datetime.datetime.utcnow().isoformat())),
        updated_at=iso_to_timestamp(processed_detail.get(
            "updated_at", datetime.datetime.utcnow().isoformat()))
    )

    user_similar_photo_messages = []
    for user_sim in response.get("user_similar", []):
        created_ts = iso_to_timestamp(user_sim.get(
            "created_at", datetime.datetime.utcnow().isoformat()))
        updated_ts = iso_to_timestamp(user_sim.get(
            "updated_at", datetime.datetime.utcnow().isoformat()))

        similarity_level = user_sim.get("similarity_level", 0)
   
        user_similar_photo = photo_pb2.UserSimilarPhoto(
            id=user_sim.get("id", ""),
            photo_id=user_sim.get("photo_id", ""),
            user_id=user_sim.get("user_id", ""),
            similarity=similarity_level,
            created_at=created_ts,
            updated_at=updated_ts
        )
        user_similar_photo_messages.append(user_similar_photo)

    request = photo_pb2.CreateUserSimilarPhotoRequest(
        photoDetail=photo_detail,
        user_similar_photo=user_similar_photo_messages
    )

    grpc_response = stub.CreateUserSimilar(request)
    return grpc_response

def create_user_similar_facecam(response):
    """
    Fungsi untuk memanggil PhotoService menggunakan gRPC dengan data response
    dari proses photo task.
    """
    stub = get_photo_service_stub()

    # Konversi data processed_photo_detail ke message PhotoDetail
    processed_detail = response.get("processed_facecam", {})

    def iso_to_timestamp(iso_str):
        dt = datetime.datetime.fromisoformat(iso_str)
        ts = Timestamp()
        ts.FromDatetime(dt)
        return ts

    facecam_pb = photo_pb2.Facecam(
        id=processed_detail.get("id", ""),
        user_id=processed_detail.get("user_id", ""),
        is_processed=processed_detail.get("is_processed", False),
        updated_at=iso_to_timestamp(processed_detail.get(
            "updated_at", datetime.datetime.utcnow().isoformat()))
    )

    user_similar_photo_messages = []
    for user_sim in response.get("user_similar", []):
        created_ts = iso_to_timestamp(user_sim.get(
            "created_at", datetime.datetime.utcnow().isoformat()))
        updated_ts = iso_to_timestamp(user_sim.get(
            "updated_at", datetime.datetime.utcnow().isoformat()))

        similarity_level = user_sim.get("similarity_level", 0)
   
        user_similar_photo = photo_pb2.UserSimilarPhoto(
            id=user_sim.get("id", ""),
            photo_id=user_sim.get("photo_id", ""),
            user_id=user_sim.get("user_id", ""),
            similarity=similarity_level,
            created_at=created_ts,
            updated_at=updated_ts
        )
        
        user_similar_photo_messages.append(user_similar_photo)

    request = photo_pb2.CreateUserSimilarFacecamRequest(
        facecam=facecam_pb,
        user_similar_photo=user_similar_photo_messages
    )

    grpc_response = stub.CreateUserSimilarFacecam(request)
    return grpc_response
