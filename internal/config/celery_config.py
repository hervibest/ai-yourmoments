# from celery import Celery
# import internal.config.minio_config 
# import internal.services.face_recognizer_service 
# import internal.repository.ai_repository
# import internal.adapter.photo_service 
# from internal.dependency import get_face_recognizer, get_vector_repository,get_photo_service_stub

# # import internal.usecase.ai_usecase
# celery_app = Celery(
#     "ai_tasks",
#     broker="redis://localhost:6379/0",  # Redis sebagai message broker
#     backend="redis://localhost:6379/0",  # Redis sebagai result backend (opsional)
#     include=['internal.usecase.ai_usecase'])

# response = celery_app.control.ping(timeout=1.0)
# if response:
#     print("Celery worker terhubung:", response)
# else:
#     print("Tidak ada Celery worker yang merespon.")