import os
import socket
import grpc
import consul
import threading
import time
from pathlib import Path
from concurrent import futures
from dotenv import load_dotenv

from internal.pb import ai_pb2_grpc, ai_pb2
from internal.delivery.grpc.ai_handler import AIHandler
from internal.usecase.ai_usecase import AIUseCase
from grpc_reflection.v1alpha import reflection
from grpc_health.v1 import health, health_pb2_grpc, health_pb2


# Load .env secara absolut
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)

# Ambil variabel dari environment
GRPC_HOST = os.getenv("GRPC_HOST", "0.0.0.0")
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))

CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", "8500"))
CONSUL_TTL = os.getenv("CONSUL_TTL", "10s")
CONSUL_DEREGISTER_AFTER = os.getenv("CONSUL_DEREGISTER_AFTER", "1m")

SERVICE_NAME = os.getenv("SERVICE_NAME", "ai-svc-grpc")


def get_local_ip():
    """Kembalikan IP lokal non-loopback."""
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
    """Daftarkan service ke Consul dengan TTL check."""
    c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)

    try:
        c.agent.service.deregister(service_id)
        print(f"♻️  Deregister service '{service_id}' (jika ada sebelumnya)")
    except Exception as e:
        print("⚠️  Gagal deregister:", e)

    check = {
        "TTL": CONSUL_TTL,
        "DeregisterCriticalServiceAfter": CONSUL_DEREGISTER_AFTER,
    }

    c.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=address,
        port=port,
        tags=tags or [],
        check=check
    )
    print(f"✅ Service '{service_name}' registered at {address}:{port}")
    return c


def ttl_heartbeat(consul_client, service_id, interval=5):
    """Kirim heartbeat TTL secara periodik ke Consul."""
    check_id = f"service:{service_id}"
    while True:
        try:
            consul_client.agent.check.ttl_pass(check_id)
            print(f"❤️  TTL heartbeat sent for {check_id}")
        except Exception as e:
            print("❌ Heartbeat error:", e)
        time.sleep(interval)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))

    # Dependency injection
    usecase = AIUseCase()
    handler = AIHandler(usecase)
    ai_pb2_grpc.add_AiServiceServicer_to_server(handler, server)

    # gRPC Health check internal
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    # Enable server reflection
    SERVICE_NAMES = (
        ai_pb2.DESCRIPTOR.services_by_name['AiService'].full_name,
        health_pb2.DESCRIPTOR.services_by_name['Health'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    # Set gRPC health status
    health_servicer.set(SERVICE_NAME, health_pb2.HealthCheckResponse.SERVING)

    # Start server
    server.add_insecure_port(f"{GRPC_HOST}:{GRPC_PORT}")
    server.start()
    print(f"🚀 gRPC Server started on {GRPC_HOST}:{GRPC_PORT}")

    # Get local IP dan register ke Consul
    ip_address = get_local_ip()
    service_id = f"{SERVICE_NAME}-{GRPC_PORT}"
    consul_client = register_with_consul(SERVICE_NAME, service_id, ip_address, GRPC_PORT, tags=["grpc", "ai"])

    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=ttl_heartbeat, args=(consul_client, service_id), daemon=True)
    heartbeat_thread.start()

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
