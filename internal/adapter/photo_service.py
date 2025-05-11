import grpc
import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from internal.pb import photo_pb2
from internal.pb import photo_pb2_grpc
from internal.dependency import get_photo_service_stub
from google.protobuf.timestamp_pb2 import Timestamp
from internal.model.ai_model import AIBulkPhoto, AIPhoto
from typing import List

def create_user_similar(response):
    """
    Fungsi untuk memanggil PhotoService menggunakan gRPC dengan data response
    dari proses photo task.
    """
    
    print("CREAT USER SIMILAR GET STUB")
    stub = get_photo_service_stub()
    
    print("GONNA GET FROM DATAS")
    # Konversi data processed_photo_detail ke message PhotoDetail
    processed_detail = response.get("processed_photo_detail", {})
    print("CREAT USER SIMILAR")

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

    print("GONNA SENDD ...")

    grpc_response = stub.CreateUserSimilar(request)
    
    print("GRPC SEND ...")
    return grpc_response

def create_user_similar_facecam(response):
    print("\n🚀 [gRPC] Create User Similar Facecam")
    print("📦 Raw Response:", response)

    stub = get_photo_service_stub()

    def iso_to_timestamp(iso_str):
        try:
            dt = datetime.datetime.fromisoformat(iso_str)
            ts = Timestamp()
            ts.FromDatetime(dt)
            print("SUCCSESS ISO TO TIMESTAMP")
            return ts
        except Exception as e:
            print(f"❌ Error convert ISO to Timestamp: {e}")
            raise

    processed_detail = response.get("processed_facecam", {})
    print("🧩 Processed Facecam Detail:", processed_detail)

    try:
        facecam_pb = photo_pb2.Facecam(
            id=processed_detail.get("id", ""),
            user_id=processed_detail.get("user_id", ""),
            is_processed=processed_detail.get("is_processed", False),
            updated_at=iso_to_timestamp(processed_detail.get(
                "updated_at", datetime.datetime.utcnow().isoformat()))
        )
    except Exception as e:
        print(f"❌ Error saat konversi Facecam ke protobuf: {e}")
        return None

    user_similar_photo_messages = []
    for i, user_sim in enumerate(response.get("user_similar", [])):
        try:
            created_ts = iso_to_timestamp(user_sim.get("created_at"))
            updated_ts = iso_to_timestamp(user_sim.get("updated_at"))

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

            print(f"✅ UserSimilarPhoto #{i}:")
            print(f"   photo_id={user_sim.get('photo_id')} | similarity={similarity_level}")

        except Exception as e:
            print(f"❌ Error saat konversi UserSimilarPhoto #{i}: {e}")

    try:
        request = photo_pb2.CreateUserSimilarFacecamRequest(
            facecam=facecam_pb,
            user_similar_photo=user_similar_photo_messages
        )

        print("📤 Sending gRPC request to PhotoService...")
        grpc_response = stub.CreateUserSimilarFacecam(request)
        print("✅ gRPC Response received:", grpc_response)
        return grpc_response

    except Exception as e:
        print(f"❌ Error saat kirim gRPC ke PhotoService: {e}")
        return None


def build_bulk_user_similar_request(process_bulk_photo: AIBulkPhoto, bulk_results: List[dict]):
    def iso_to_timestamp(iso_str):
        dt = datetime.datetime.fromisoformat(iso_str)
        ts = Timestamp()
        ts.FromDatetime(dt)
        return ts

    bulk_user_similar_photos = []
    for result in bulk_results:
        photo_detail = result["photo_detail"]
        user_similar_list = result["user_similar_photo"]

        photo_detail_msg = photo_pb2.PhotoDetail(
            id=photo_detail.get("id", ""),
            photo_id=photo_detail.get("photo_id", ""),
            file_name=photo_detail.get("file_name", ""),
            file_key=photo_detail.get("file_key", ""),
            size=photo_detail.get("size", 0),
            type=photo_detail.get("type", ""),
            checksum=photo_detail.get("checksum", ""),
            width=photo_detail.get("width", 0),
            height=photo_detail.get("height", 0),
            url=photo_detail.get("url", ""),
            your_moments_type=photo_detail.get("your_moments_type", ""),
            created_at=iso_to_timestamp(photo_detail.get("created_at")),
            updated_at=iso_to_timestamp(photo_detail.get("updated_at")),
        )

        user_similar_photos = []
        for user_sim in user_similar_list:
            user_similar_photos.append(photo_pb2.UserSimilarPhoto(
                id=user_sim.get("id", ""),
                photo_id=user_sim.get("photo_id", ""),
                user_id=user_sim.get("user_id", ""),
                similarity=user_sim.get("similarity_level", 0),
                is_wishlist=False,
                is_resend=False,
                is_cart=False,
                is_favorite=False,
                created_at=iso_to_timestamp(user_sim.get("created_at")),
                updated_at=iso_to_timestamp(user_sim.get("updated_at")),
            ))

        bulk_user_similar_photos.append(photo_pb2.BulkUserSimilarPhoto(
            photoDetail=photo_detail_msg,
            user_similar_photo=user_similar_photos
        ))

    request = photo_pb2.CreateBulkUserSimilarPhotoRequest(
        bulk_photo=photo_pb2.BulkPhoto(
            id=process_bulk_photo.id,
            creator_id=process_bulk_photo.creator_id,
            bulk_photo_status =  "SUCCESS"
        ),
        bulk_user_similar_photo=bulk_user_similar_photos
    )

    stub = get_photo_service_stub()
    grpc_response = stub.CreateBulkUserSimilarPhotos(request)
    
    return grpc_response
