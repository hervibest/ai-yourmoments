from minio import Minio

class MinIOClient:
    def __init__(self):
        self.client = Minio(
            "localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        self.bucket_name = "ai-results"

    def upload_file(self, file_path, object_name):
        self.client.fput_object(self.bucket_name, object_name, file_path)

    def get_file_url(self, object_name):
        return f"http://localhost:9000/{self.bucket_name}/{object_name}"
