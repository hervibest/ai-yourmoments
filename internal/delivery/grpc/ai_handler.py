import grpc
from internal.pb import ai_pb2, ai_pb2_grpc
from internal.usecase.ai_usecase import AIUseCase

class AIHandler(ai_pb2_grpc.AiServiceServicer):
    def __init__(self, ai_usecase: AIUseCase):
        self.ai_usecase = ai_usecase

    def ProcessPhoto(self, request, context):
        """Client hanya menerima status sukses, sementara pemrosesan berjalan async"""
        success, error_message = self.ai_usecase.process_photo(request.id, request.url)
        # Misalnya: status 1 untuk sukses, 0 untuk gagal
        status = 200 if success else 500
        return ai_pb2.ProcessPhotoResponse(status=status, error=error_message)

    def ProcessFacecam(self, request, context):
        """Client hanya menerima status sukses, sementara pemrosesan berjalan async"""
        success, error_message = self.ai_usecase.process_facecam(request.id, request.url)
        status = 200 if success else 500
        return ai_pb2.ProcessFacecamResponse(status=status, error=error_message)
