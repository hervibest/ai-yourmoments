# publisher.py
import json
from nats.aio.client import Client as NATS
from nats.js.api import StreamConfig

NATS_URL = "nats://localhost:4222"
SINGLE_PHOTO_TOPIC = "ai.single.photo"
SINGLE_FACECAM_TOPIC = "ai.single.facecam"
BULK_PHOTO_TOPIC = "ai.bulk.photo"

async def publish_json_to_jetstream_single(data: dict, subject: str = SINGLE_PHOTO_TOPIC):
    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    js = nc.jetstream()

    msg = json.dumps(data).encode("utf-8")
    await js.publish(subject, msg)

    await nc.drain()
    
async def publish_json_to_jetstream_bulk(data: dict, subject: str = BULK_PHOTO_TOPIC):
    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    js = nc.jetstream()

    msg = json.dumps(data).encode("utf-8")
    await js.publish(subject, msg)

    await nc.drain()
    
async def publish_json_to_jetstream_facecam(data: dict, subject: str = SINGLE_FACECAM_TOPIC):
    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    js = nc.jetstream()

    msg = json.dumps(data).encode("utf-8")
    await js.publish(subject, msg)

    await nc.drain()
