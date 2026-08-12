from collections import defaultdict
import threading
from uuid import uuid4


class ConversationStore:
    """In-memory history for prototype scope.

    A production version should use a managed durable store with retention and
    access controls (for example, Firestore/Spanner depending on requirements).
    """

    def __init__(self):
        self._messages: dict[str, list[dict]] = defaultdict(list)
        self._owners: dict[str, str] = {}
        self._lock = threading.Lock()

    def ensure(self, conversation_id: str | None, owner: str) -> str:
        with self._lock:
            cid = conversation_id or str(uuid4())
            existing = self._owners.get(cid)
            if existing and existing != owner:
                raise PermissionError("Conversation belongs to another user")
            self._owners[cid] = owner
            return cid

    def get(self, conversation_id: str, owner: str) -> list[dict]:
        if self._owners.get(conversation_id) not in (None, owner):
            raise PermissionError("Conversation belongs to another user")
        return list(self._messages.get(conversation_id, []))

    def append(self, conversation_id: str, role: str, content: str, sources: list[dict] | None = None) -> None:
        with self._lock:
            self._messages[conversation_id].append(
                {"role": role, "content": content, "sources": sources or []}
            )
