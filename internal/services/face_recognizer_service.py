import cv2
import time
import onnxruntime as ort
from insightface.app import FaceAnalysis

class FaceRecognizer:
    def __init__(self, model_name='buffalo_l'):
        print("🧠 Inisialisasi FaceRecognizer...")

        available_providers = ort.get_available_providers()
        print(f"✅ Available ONNX providers: {available_providers}")

        if 'CUDAExecutionProvider' in available_providers:
            providers = ['CUDAExecutionProvider']
            ctx_id = 0
            print("🚀 Menggunakan GPU (CUDA)")
        else:
            providers = ['CPUExecutionProvider']
            ctx_id = -1
            print("⚙️ Menggunakan CPU")

        self.app = FaceAnalysis(
            name=model_name,
            providers=providers
        )
        self.app.prepare(ctx_id=ctx_id)
        print("✅ FaceRecognizer siap digunakan")
        

    def process_faces(self, image_path, photo_id):
        print("memproses wajah")
        
        """
        Mendeteksi wajah, mengambil bounding box, dan embedding.
        """
        try:
            t1 = time.perf_counter()
            img = cv2.imread(image_path)
            t2 = time.perf_counter()
            print(f"[Time] Read image: {t2 - t1:.6f}s")

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            t3 = time.perf_counter()
            print(f"[Time] CV2 color: {t3 - t2:.6f}s")

            faces = self.app.get(img_rgb)
            t4 = time.perf_counter()
            print(f"[Time] processing image: {t4 - t3:.6f}s")

            bounding_boxes = []
            embeddings = []

            # proses embedding
            for face_idx, face in enumerate(faces):
                bounding_boxes.append(face.bbox.tolist())
                embeddings.append((photo_id, face_idx, face.embedding.tolist()))
            t5 = time.perf_counter()
            print(f"[Time] make embedding image: {t5 - t4:.6f}s")

            return bounding_boxes, embeddings, img  # Mengembalikan bounding box & embedding

        except Exception as e:
            print(f"Error saat memproses wajah: {e}")
            return [], []  # Return list kosong jika terjadi error