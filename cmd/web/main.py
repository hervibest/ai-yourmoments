import socket
import grpc
import consul
import threading
import time
from concurrent import futures
from internal.pb import ai_pb2_grpc, ai_pb2
from internal.delivery.grpc.ai_handler import AIHandler
from internal.usecase.ai_usecase import AIUseCase
from internal.repository.ai_repository import VectorRepository
from internal.services.face_recognizer_service import FaceRecognizer
from grpc_reflection.v1alpha import reflection
from grpc_health.v1 import health, health_pb2_grpc, health_pb2

def get_local_ip():
    """
    Mengembalikan alamat IP lokal yang bukan loopback.
    Jika koneksi ke 8.8.8.8 tidak berhasil, maka akan mengembalikan 127.0.0.1.
    Pastikan mesin Anda terhubung ke jaringan sehingga alamat yang dikembalikan bukan loopback.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = "127.0.0.1"
    finally:
        s.close()
    return ip_address

def register_with_consul(service_name, service_id, address, port, tags=None):
    """
    Mendaftarkan service ke Consul dengan TTL check.
    Jika ada service dengan service_id yang sama, lakukan deregistrasi terlebih dahulu.
    Perlu diingat bahwa dengan TTL check Anda harus secara periodik mengirim heartbeat agar status service tetap 'passing'.
    """
    c = consul.Consul(host='localhost', port=8500)
    
    # Deregister service sebelumnya jika ada
    try:
        c.agent.service.deregister(service_id)
        print(f"Service dengan ID '{service_id}' telah di-deregister (jika sebelumnya terdaftar).")
    except Exception as e:
        print("Gagal melakukan deregistrasi (mungkin belum terdaftar):", e)
    
    check = {
        "TTL": "10s",
        "DeregisterCriticalServiceAfter": "1m"
    }
    c.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=address,
        port=port,
        tags=tags or [],
        check=check
    )
    print(f"Service '{service_name}' dengan ID '{service_id}' telah terdaftar di Consul pada {address}:{port}")
    return c

def ttl_heartbeat(consul_client, service_id, interval=5):
    """
    Mengirim heartbeat secara periodik untuk TTL check.
    Pastikan heartbeat dikirim lebih cepat dari TTL (misalnya setiap 5 detik).
    """
    # Check ID default untuk service TTL check adalah "service:<service_id>"
    check_id = f"service:{service_id}"
    while True:
        try:
            consul_client.agent.check.ttl_pass(check_id)
            print(f"TTL heartbeat sent for check_id: {check_id}")
        except Exception as e:
            print("Error sending TTL heartbeat:", e)
        time.sleep(interval)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))

    # Dependency Injection
    # recognizer = FaceRecognizer()
    # repository = VectorRepository()
    # usecase = AIUseCase(recognizer, repository)
    usecase = AIUseCase()
    handler = AIHandler(usecase)

    # Daftarkan service AI gRPC
    ai_pb2_grpc.add_AiServiceServicer_to_server(handler, server)

    # Tambahkan Health Check Service gRPC (internal gRPC health, tidak dipakai oleh Consul TTL check)
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    service_name = "grpc-ai-service"
    
    host = "0.0.0.0"
    port = 50051
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    print(f"AI Server running on port {port}...")

    # Dapatkan IP lokal yang valid (gunakan get_local_ip())
    ip_address = get_local_ip()
    print("Local IP yang digunakan:", ip_address)
    
    # Aktifkan reflection
    SERVICE_NAMES = (
        ai_pb2.DESCRIPTOR.services_by_name['AiService'].full_name,
        health_pb2.DESCRIPTOR.services_by_name['Health'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    # Set status health gRPC menjadi SERVING (ini untuk internal gRPC health check)
    health_servicer.set(service_name, health_pb2.HealthCheckResponse.SERVING)

    # Pendaftaran service ke Consul dengan TTL check
    service_id = f"{service_name}-{port}"
    consul_client = register_with_consul(service_name, service_id, ip_address, port, tags=["grpc", "ai"])

    # Mulai thread untuk mengirim heartbeat TTL secara periodik
    heartbeat_thread = threading.Thread(target=ttl_heartbeat, args=(consul_client, service_id), daemon=True)
    heartbeat_thread.start()

    server.wait_for_termination()

if __name__ == "__main__":
    serve()
