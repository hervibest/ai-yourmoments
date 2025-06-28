from dataclasses import dataclass
from typing import Optional

@dataclass
class AIBulkPhoto:
    id: str
    creator_id: str

@dataclass
class AIPhoto:
    id: str
    original_filename :str
    compressed_url: Optional[str] = None
    collection_url: Optional[str] = None
