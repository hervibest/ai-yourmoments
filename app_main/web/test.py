import onnxruntime as ort
print("Available providers:", ort.get_available_providers())
print("Device:", ort.get_device())
