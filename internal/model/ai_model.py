from dataclasses import dataclass
from typing import Optional

@dataclass
class AIBulkPhoto:
    id: str
    creator_id: str

@dataclass
class AIPhoto:
    original_filename :str
    id: str
    compressed_url: Optional[str] = None
    collection_url: Optional[str] = None
