"""Step 5: RAG (retrieval-augmented generation). Find designs similar to a new request and give them
to the model as worked examples.

How "similar" is measured, in plain words:
1. Split each text into words, drop very common words ("the", "my"), and cut a plural "s".
2. TF-IDF: a word counts more if it appears often in this text (TF) and rarely in the others (IDF).
   "salon" says a lot about a request; "list" says little, because many requests have it.
3. Each text becomes a list of word weights (a vector). Cosine similarity compares two vectors:
   1.0 = the same words in the same proportions, 0.0 = no words in common.
Written by hand (no scikit-learn): a few hundred examples need nothing faster, and every line can be explained.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlmodel import Session as DbSession
from sqlmodel import select

from app.config import settings
from app.db import ExampleRow, get_engine
from app.models import Analysis

SEED_FILE = Path(__file__).with_name("seed_examples.json")
# Only the newest approved designs per person are searched (keeps search fast and recent)
MAX_OWN_EXAMPLES = 200

# Words that appear in almost every request and say nothing about what it is about
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "each", "for", "from", "has", "have",
    "how", "i", "if", "in", "is", "it", "its", "list", "many", "me", "much", "my", "of", "on", "or",
    "our", "so", "some", "that", "the", "their", "them", "there", "they", "this", "to", "track", "keep",
    "want", "what", "when", "where", "which", "who", "whether", "will", "with", "would", "you", "your",
    "api", "app", "build", "make", "need", "something", "thing", "things", "record", "records",
}


@dataclass(frozen=True)
class Example:
    title: str
    text: str  # what we match against
    blueprint: Analysis
    source: str  # "seed" or "yours"


# --------------------------------------------------------------------------- words and vectors


def words(text: str) -> list[str]:
    """Lower-case words, without common words, with a simple plural cut ("books" → "book")."""
    found = re.findall(r"[a-z]+", text.lower().replace("_", " "))
    result = []
    for word in found:
        if word in _STOPWORDS or len(word) < 2:
            continue
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        result.append(word)
    return result


def idf_weights(documents: list[list[str]]) -> dict[str, float]:
    """IDF: rare words get a high weight, words found in every document a low one.
    The +1s ("smoothing") avoid dividing by zero and keep every weight above zero."""
    total = len(documents)
    document_count = Counter(word for document in documents for word in set(document))
    return {word: math.log((1 + total) / (1 + count)) + 1 for word, count in document_count.items()}


def vector(document: list[str], idf: dict[str, float]) -> dict[str, float]:
    """TF-IDF vector, scaled to length 1 so long and short texts compare fairly."""
    counts = Counter(document)
    weights = {word: (count / len(document)) * idf.get(word, 0.0) for word, count in counts.items()} if document else {}
    length = math.sqrt(sum(weight * weight for weight in weights.values()))
    return {word: weight / length for word, weight in weights.items()} if length else {}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Both vectors have length 1, so cosine similarity is just the sum of matching word weights."""
    if len(a) > len(b):
        a, b = b, a  # loop over the shorter one
    return sum(weight * b.get(word, 0.0) for word, weight in a.items())


# --------------------------------------------------------------------------- the examples


def describe(blueprint: Analysis) -> str:
    """The neutral text stored for an approved design (never the person's own request)."""
    # One part per record type: its plural and its detail names (one record type gives the same text as before)
    parts = [
        f"{r.plural} " + " ".join(field.name.replace("_", " ") for field in r.fields) for r in blueprint.resources
    ]
    return f"{blueprint.title}. {blueprint.description} " + " ".join(parts)


@lru_cache(maxsize=1)
def seed_examples() -> tuple[Example, ...]:
    """The hand-written starter examples (read once, then kept in memory)."""
    raw = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    examples = []
    for entry in raw:
        blueprint = Analysis.model_validate(entry["blueprint"])
        examples.append(Example(blueprint.title, f"{entry['request']} {describe(blueprint)}", blueprint, "seed"))
    return tuple(examples)


def own_examples(user_id: int) -> list[Example]:
    """Designs this person approved. Other people's designs are never used (privacy)."""
    with DbSession(get_engine()) as db:
        query = (
            select(ExampleRow)
            .where(ExampleRow.owner_id == user_id)
            .order_by(ExampleRow.id.desc())
            .limit(MAX_OWN_EXAMPLES)
        )
        rows = db.exec(query).all()
    return [Example(row.title, row.text, Analysis.model_validate_json(row.blueprint_json), "yours") for row in rows]


def search(request: str, candidates: list[Example], top_k: int, min_score: float) -> list[tuple[Example, float]]:
    """The top_k candidates most like the request, best first, leaving out any below min_score."""
    if not candidates:
        return []
    documents = [words(candidate.text) for candidate in candidates]
    query = words(request)
    # The query is counted as a document too, so its words get an IDF weight
    idf = idf_weights([*documents, query])
    query_vector = vector(query, idf)
    scored = [(candidate, cosine(query_vector, vector(document, idf))) for candidate, document in zip(candidates, documents)]
    good = [(candidate, score) for candidate, score in scored if score >= min_score]
    good.sort(key=lambda pair: pair[1], reverse=True)
    return good[:top_k]


# --------------------------------------------------------------------------- meaning-based search


@lru_cache(maxsize=1)
def embedding_model():
    """The small meaning-based model (model2vec potion-base-8M, about 30 MB, runs on the CPU).
    Returns None if it is not installed, so retrieval falls back to TF-IDF instead of failing.
    Embedding: a text turned into 256 numbers so that texts with similar meaning get similar numbers
    ("pupils" lands near "students", unlike TF-IDF which only sees shared words)."""
    folder = Path(settings.embedding_model_path)
    if not folder.exists():
        return None
    try:
        from model2vec import StaticModel  # imported here: the builder works without this package

        return StaticModel.from_pretrained(str(folder))
    except Exception:
        return None


def _unit_vectors(texts: list[str]):
    """One length-1 vector per text, so a dot product is the cosine similarity."""
    import numpy

    vectors = embedding_model().encode(texts)
    return vectors / numpy.linalg.norm(vectors, axis=1, keepdims=True)


def search_by_meaning(
    request: str, candidates: list[Example], top_k: int, min_score: float
) -> list[tuple[Example, float]]:
    """Like search(), but compares meaning instead of shared words."""
    if not candidates:
        return []
    scores = _unit_vectors([c.text for c in candidates]) @ _unit_vectors([request])[0]
    good = [(c, float(s)) for c, s in zip(candidates, scores) if s >= min_score]
    good.sort(key=lambda pair: pair[1], reverse=True)
    return good[:top_k]


def active_method() -> str:
    """Which search runs: embeddings when chosen and installed, otherwise TF-IDF."""
    if settings.rag_method == "embedding" and embedding_model() is not None:
        return "embedding"
    return "tfidf"


def similar_examples(request: str, user_id: int) -> list[tuple[Example, float]]:
    candidates = [*own_examples(user_id), *seed_examples()]
    if active_method() == "embedding":
        return search_by_meaning(request, candidates, settings.rag_top_k, settings.rag_embedding_min_score)
    return search(request, candidates, settings.rag_top_k, settings.rag_min_score)


# --------------------------------------------------------------------------- learning


def _same_design(a: Analysis, b: Analysis) -> bool:
    def shape(design: Analysis) -> set[tuple[str, frozenset[str]]]:
        return {(r.plural, frozenset(f.name for f in r.fields)) for r in design.resources}

    return shape(a) == shape(b)


def add_approved(user_id: int, blueprint: Analysis) -> bool:
    """Keeps an approved design for this person's later requests. Returns False if it is a repeat."""
    if any(_same_design(blueprint, example.blueprint) for example in own_examples(user_id)):
        return False
    with DbSession(get_engine()) as db:
        db.add(
            ExampleRow(
                owner_id=user_id,
                title=blueprint.title,
                text=describe(blueprint),
                blueprint_json=blueprint.model_dump_json(),
            )
        )
        db.commit()
    return True


# --------------------------------------------------------------------------- for the prompt


def example_line(example: Example) -> str:
    """One compact line per example, e.g. Salon Bookings API: bookings with customer_name (str, required), ..."""
    parts = []
    for resource in example.blueprint.resources:
        details = ", ".join(
            f"{field.name} ({field.links_to + ' link' if field.type == 'link' else field.type}"
            f"{', required' if field.required else ''})"
            for field in resource.fields
        )
        parts.append(f"{resource.plural} with {details}")
    return f'"{example.title}": ' + "; ".join(parts)
