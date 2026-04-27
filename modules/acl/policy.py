
from pydantic import BaseModel
from typing import List

class Policy(BaseModel):
    user: str
    allow: List[str]  # e.g., ["10.0.0.0/24:22", "github.com:443"]
    deny: List[str]   # e.g., ["*"]
