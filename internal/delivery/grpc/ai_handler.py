import grpc
from proto import ai_service_pb2, ai_service_pb2_grpc
from usecases.ai_usecase import AIUseCase

class AIHandler(ai_service_pb2_grpc.AIServiceServicer):
    def __init__(self, ai_usecase: AIUseCase):
        self.ai_usecase = ai_usecase

    def ProcessProfilePhotoFile(self, request, context):
        """Client hanya menerima status sukses, sementara pemrosesan berjalan async"""
        success, message = self.ai_usecase.process_file(request.file_id, request.file_url)
        return ai_service_pb2.ProcessResponse(success=success, message=message)
    
    def ProcessFile(self, request, context):
        """Client hanya menerima status sukses, sementara pemrosesan berjalan async"""
        success, message = self.ai_usecase.process_file(request.file_id, request.file_url)
        return ai_service_pb2.ProcessResponse(success=success, message=message)