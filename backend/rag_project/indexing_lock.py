"""Process-local lock shared by retrieval and active-index promotion."""
from threading import RLock

INDEX_LOCK = RLock()
