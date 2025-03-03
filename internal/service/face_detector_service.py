import cv2
from retinaface import RetinaFace

class FaceDetector:
    def detect_faces(self, image_path):
        img = cv2.imread(image_path)
        faces = RetinaFace.detect_faces(img)
        return [faces[key]['facial_area'] for key in faces] if faces else []
