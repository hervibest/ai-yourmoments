start-worker:
	celery -A internal.config.celery_config worker --loglevel=info

start-server:
	python3 -m app_main.web.main

start-worker:
	python3 -m app_main.worker.main

test-server:
	python3 -m app_main.web.test

proto-ai:
	cd internal && python3 -m grpc_tools.protoc -I./pb --python_out=. --grpc_python_out=. pb/ai.proto

proto-photo:
	cd internal && python3 -m grpc_tools.protoc -I./pb --python_out=. --grpc_python_out=. pb/photo.proto