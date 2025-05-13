from insightface.app import FaceAnalysis

# Inisialisasi face analysis dan siapkan model
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=-1)

# Tampilkan model path yang berhasil dimuat
for key, model in app.models.items():
    print(f"{key}: {model.model_file}")
