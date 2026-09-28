from __future__ import annotations
from pathlib import Path
from ..config import settings
import re


class RFAKnowledgeService:
    """Loads the nine reference RFA/MOU examples as retrieval context.

    This is intentionally RAG-style context injection, not model fine-tuning.
    The reference files guide the Azure OpenAI reasoning call without becoming
    hard-coded facts about a live procurement case.
    """

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else self._default_root()
        self.documents = self._load()

    @staticmethod
    def _default_root() -> Path:
        configured = Path(settings.rfa_reference_dir)
        if configured.is_absolute():
            return configured
        return Path(__file__).resolve().parents[2] / "data" / "rfa_reference"

    def _load(self) -> list[dict]:
        docs = []
        for path in sorted(self.root.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            docs.append({"name": path.name, "text": text, "category": self._category(text, path.name)})
        return docs

    @staticmethod
    def _category(text: str, filename: str) -> str:
        m = re.search(r"^#\s+([A-Z]+(?:-[A-Za-z /]+)?)", text, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return filename.split("_")[1] if "_" in filename else filename

    def all(self) -> list[dict]:
        return list(self.documents)

    def retrieve(self, case: dict, limit: int = 3) -> list[dict]:
        category = (case.get("category") or "").upper()
        subject = (case.get("subject") or "").lower()
        body = (case.get("body") or (case.get("extracted") or {}).get("body") or "").lower()
        query = f"{category} {subject} {body}"
        scored = []
        for doc in self.documents:
            score = 0
            name = doc["name"].lower()
            if category and category in name:
                score += 100
            if category and category in doc["text"].upper():
                score += 50
            for token in re.findall(r"[a-z0-9]{4,}", query):
                if token in name or token in doc["text"].lower():
                    score += 1
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:max(1, limit)]]
