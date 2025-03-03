import torch
from facenet_pytorch import InceptionResnetV1

class FaceEmbedder:
    def __init__(self):
        self.model = InceptionResnetV1(pretrained='vggface2').eval()

    def extract_embedding(self, face_image):
        face_tensor = torch.tensor(face_image).float().unsqueeze(0)
        return self.model(face_tensor).detach().numpy().tolist()
