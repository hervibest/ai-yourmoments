import grpc
from concurrent import futures
from proto import ai_service_pb2_grpc
from handlers.ai_handler import AIHandler
from usecases.ai_usecase import AIUseCase
from repositories.ai_repository import AIRepository
from services.downloader import FileDownloader
from services.face_detector import FaceDetector
from services.face_embedder import FaceEmbedder

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Dependency Injection
    downloader = FileDownloader()
    detector = FaceDetector()
    embedder = FaceEmbedder()
    repository = AIRepository()
    usecase = AIUseCase(downloader, detector, embedder, repository)
    handler = AIHandler(usecase)

    ai_service_pb2_grpc.add_AIServiceServicer_to_server(handler, server)
    
    server.add_insecure_port("[::]:50051")
    server.start()
    print("AI Server running on port 50051...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
