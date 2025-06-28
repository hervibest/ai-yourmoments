import os
import json
import time
import signal
import threading
import logging
import datetime
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import nats
from nats.errors import TimeoutError
from internal.usecase.ai_usecase import AIUseCase
from internal.model.ai_model import  AIBulkPhoto, AIPhoto

# Load environment variables
env_path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AISubscriber:
    def __init__(self, nc, js, ai_usecase: AIUseCase):
        self.nc = nc
        self.js = js
        self.ai_usecase = ai_usecase
        self.should_exit = False
        self.max_retries = 3
        self.retry_delay = 5  # seconds

    async def _ensure_stream_exists(self):
        """Ensure the stream exists with proper configuration"""
              
        target_subjects = [
            "AI.PHOTO.PROCESS",
            "AI.FACECAM.PROCESS",
            "AI.BULK_PHOTO.PROCESS"
        ]
                     
        retries = 0
        while retries < self.max_retries:
            try:
                # Check if stream exists
                stream = await self.js.stream_info("AI_STREAM")
                logger.info("Trying to update AI_STREAM with correct subjects")
                     
                # Hanya update jika subjects berbeda
                if set(stream.config.subjects) != set(target_subjects):
                    logger.info("Trying to update AI_STREAM with correct subjects")
                    await self.js.delete_stream("AI_STREAM")
                    await self.js.update_stream(
                        name="AI_STREAM",
                        config=nats.js.api.StreamConfig(
                            name="AI_STREAM",
                            subjects=target_subjects,
                            # retention=nats.js.api.RetentionPolicy.WORK_QUEUE,
                            max_msgs=10000,
                            max_age= 2600 * 1_000_000,
                            storage=nats.js.api.StorageType.FILE
                        )
                    )
                    logger.info("Updated AI_STREAM with correct subjects")
                return True
            except Exception as e:
                if "stream not found" in str(e).lower():
                    try:
                        # Create stream if doesn't exist
                        await self.js.add_stream(
                            name="AI_STREAM",
                            subjects=target_subjects,
                            # retention=nats.js.api.RetentionPolicy.WORK_QUEUE,
                            max_msgs=10000,
                            max_age= 2600 * 1_000_000,
                            storage=nats.js.api.StorageType.FILE
                        )
                        
                        logger.info("Successfully created AI_STREAM")
                        return True
                    except Exception as create_error:
                        logger.error(f"Failed to create stream (attempt {retries + 1}): {create_error}")
                        retries += 1
                        await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Error checking stream: {e}")
                    retries += 1
                    await asyncio.sleep(self.retry_delay)
        
        logger.error("Max retries reached for stream creation")
        return False

    async def process_photo_handler(self, msg):
        try:
            data = json.loads(msg.data.decode())
            logger.info(f"Processing photo: {data['photo_id']}")

            success, error_message = await self.ai_usecase.process_photo(
                data['photo_id'],
                data['creator_id'],
                data['url'],
                data['original_filename']
            )

            if success:
                logger.info(f"Successfully processed photo {data['photo_id']}")
                await msg.ack()
            else:
                logger.error(f"Failed to process photo {data['photo_id']}: {error_message}")
                await msg.nak(delay=30)  # Negative acknowledgment with 30s delay

        except json.JSONDecodeError as e:
            logger.error(f"Invalid message format: {e}")
            await msg.term()  # Terminate the message (won't be redelivered)
        except Exception as e:
            logger.error(f"Unexpected error processing photo: {e}")
            await msg.nak(delay=60)  # Retry after 60s

    async def process_facecam_handler(self, msg):
        try:
            data = json.loads(msg.data.decode())
            logger.info(f"Processing facecam for user: {data['user_id']}")

            success, error_message = await self.ai_usecase.process_facecam(
                data['user_id'],
                data['creator_id'],
                data['url']
            )

            if success:
                logger.info(f"Successfully processed facecam for user {data['user_id']}")
                await msg.ack()
            else:
                logger.error(f"Failed to process facecam for user {data['user_id']}: {error_message}")
                await msg.nak(delay=30)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid message format: {e}")
            await msg.term()
        except Exception as e:
            logger.error(f"Unexpected error processing facecam: {e}")
            await msg.nak(delay=60)

    async def process_bulk_photo_handler(self, msg):
        try:
            data = json.loads(msg.data.decode())
            logger.info(f"Processing bulk photo batch: {data['bulk_photo_id']}")

            bulk_photo = AIBulkPhoto(
                id = data['bulk_photo_id'],
                creator_id = data['creator_id']
            )
            

        # Sesuaikan dengan struktur dari Golang
    # Create AIPhoto objects directly
            photos = [
                AIPhoto(
                    id=p['id'],
                    collection_url=p['collection_url'],
                    original_filename=p['original_filename']
                ) for p in data['photos']
            ]


            success, error_message = await self.ai_usecase.process_photo_bulk(
                bulk_photo,
                photos
            )

            if success:
                logger.info(f"Successfully processed bulk photo batch {data['bulk_photo_id']}")
                await msg.ack()
            else:
                logger.error(f"Failed to process bulk photo batch {data['bulk_photo_id']}: {error_message}")
                await msg.nak(delay=60)  # Longer delay for bulk operations

        except json.JSONDecodeError as e:
            logger.error(f"Invalid message format: {e}")
            await msg.term()
        except Exception as e:
            logger.error(f"Unexpected error processing bulk photos: {e}")
            await msg.nak(delay=120)  # Longer delay for bulk operations

    async def _subscribe_with_retry(self, subject, queue, cb):
        """Helper method to handle subscription with retry logic"""
        retries = 0
        while retries < self.max_retries and not self.should_exit:
            try:
                sub = await self.js.subscribe(
                    subject,
                    # queue=queue,
                    cb=cb,
                    durable=f"{queue}_DURABLE_V4",
                    config=nats.js.api.ConsumerConfig(
                        deliver_policy=nats.js.api.DeliverPolicy.NEW,
                        ack_policy=nats.js.api.AckPolicy.EXPLICIT,  # 🔴 WAJIB kalau pakai `cb`
                        # ack_wait=datetime.timedelta(seconds=60),    # ✅ HARUS timedelta  # 🔴 Harus berupa `timedelta` jika kamu pakai Python NATS 2.x+
                        max_deliver=5
                    )
                )

                logger.info(f"Successfully subscribed to {subject} in queue {queue}")
                return sub
            except Exception as e:
                logger.error(f"Failed to subscribe to {subject} (attempt {retries + 1}): {e}")
                retries += 1
                await asyncio.sleep(self.retry_delay)
        
        logger.error(f"Max retries reached for {subject} subscription")
        return None

    async def start_subscribers(self):
        if not await self._ensure_stream_exists():
            raise Exception("Failed to ensure stream exists")

        # Create subscriptions with retry logic
        subs = []
        
        for config in [
            {"subject": "AI.PHOTO.PROCESS", "queue": "AI_PHOTO_CONSUMER_V1", "cb": self.process_photo_handler},
            {"subject": "AI.FACECAM.PROCESS", "queue": "AI_FACECAM_CONSUMER_V1", "cb": self.process_facecam_handler},
            {"subject": "AI.BULK_PHOTO.PROCESS", "queue": "AI_BULK_PHOTO_CONSUMER_V1", "cb": self.process_bulk_photo_handler}
        ]:
            sub = await self._subscribe_with_retry(config["subject"], config["queue"], config["cb"])
            if sub:
                subs.append(sub)

        if len(subs) < 3:
            raise Exception("Failed to initialize all subscriptions")

    async def run(self):
        try:
            await self.start_subscribers()
            
            # Keep the connection alive
            while not self.should_exit:
                await asyncio.sleep(1)
                
                # Check connection status periodically
                if not self.nc.is_connected:
                    logger.error("NATS connection lost")
                    break
                
        except Exception as e:
            logger.error(f"Error in subscriber: {e}")
            raise

async def main():
    # Initialize dependencies
    ai_usecase = AIUseCase()
    
    # Connect to NATS with retry logic
    nc = None
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            nc = await nats.connect(
                os.getenv("NATS_URL", "nats://localhost:4222"),
                max_reconnect_attempts=-1,  # Infinite reconnect attempts
                reconnect_time_wait=2  # 2 seconds between reconnects
            )
            js = nc.jetstream()
            logger.info("Successfully connected to NATS")
            break
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    
    if not nc:
        logger.error("Failed to connect to NATS after max retries")
        return

    subscriber = AISubscriber(nc, js, ai_usecase)
    
    # Graceful shutdown handler
    def signal_handler():
        logger.info("Received shutdown signal")
        subscriber.should_exit = True
    
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
    
    try:
        await subscriber.run()
    except Exception as e:
        logger.error(f"Fatal error in subscriber: {e}")
    finally:
        await nc.close()
        logger.info("NATS connection closed")

if __name__ == "__main__":
    asyncio.run(main())