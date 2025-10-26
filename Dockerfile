FROM python:3.11-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1  
WORKDIR /app

# Install dependencies sistem + build tools
RUN apt-get update && apt-get install -y \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    cmake \
 && rm -rf /var/lib/apt/lists/*

# Salin dan install semua dependensi Python dari requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Salin model buffalo_l InsightFace ke direktori default
COPY models/buffalo_l /root/.insightface/models/buffalo_l

# Salin seluruh source code proyek
COPY . .
ENV PYTHONPATH=/app
# Jalankan aplikasi
CMD ["python", "app_main/worker/main.py"]
