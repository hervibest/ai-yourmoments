start-worker:
	celery -A internal.config.celery_config worker --loglevel=info

start-server:
	python3 -m cmd.web.main

proto-ai:
	cd internal && python -m grpc_tools.protoc -I./pb --python_out=. --grpc_python_out=. pb/ai.proto

proto-photo:
	cd internal && python -m grpc_tools.protoc -I./pb --python_out=. --grpc_python_out=. pb/photo.proto