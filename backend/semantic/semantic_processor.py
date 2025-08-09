import os
import re
import json
import logging
import unicodedata
import html
from typing import List, Tuple, Dict, Any
import spacy
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import numpy as np
import pymysql


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_SPACY_MODEL = os.environ.get("ECHO_SPACY_MODEL", "en_core_web_sm")
DEFAULT_EMBEDDER = os.environ.get("ECHO_EMBEDDER", "all-MiniLM-L6-v2")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    if not text:
        return []
    text = clean_text(text)
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.!?]) +", text)
    chunks: List[str] = []
    current_chunk = []
    current_len = 0
    for sentence in sentences:
        if current_len + len(sentence) + 1 <= max_chars:
            current_chunk.append(sentence)
            current_len += len(sentence) + 1
        else:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_len = len(sentence) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        return chunks


def load_spacy_model(model_name: str = DEFAULT_SPACY_MODEL):
    try:
        nlp = spacy.load(model_name)
    except OSError:
        raise RuntimeError(f"Failed to load spaCy model '{model_name}")
    return nlp


def load_embedder(model_name: str = DEFAULT_EMBEDDER):
    try:
        embedder = SentenceTransformer(model_name)
    except:
        raise RuntimeError(f"Failed to load embedder '{model_name}'")
    return embedder


def load_keybert(embedding_model: Any = None):
    if embedding_model is None:
        kw = KeyBERT()
    else:
        kw = KeyBERT(model=embedding_model)
    return kw


def extract_keywords_keybert(
    text: str, keybert_model: KeyBERT, top_n: int = 10, use_mmr: bool = True
) -> List[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    try:
        keywords_with_scores = keybert_model.extract_keywords(
            cleaned, top_n=top_n, use_mmr=use_mmr
        )
    except Exception:
        keywords_with_scores = keybert_model.extract_keywords(cleaned, top_n=top_n)
    keywords = [k for k, _score in keywords_with_scores]
    return keywords


def get_embeddings(texts: List[str], embedder: SentenceTransformer) -> np.ndarray:
    if not texts:
        return np.array([])
    embeddings = embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings


def create_vector_record(
    doc_id: str,
    text: str,
    keywords: List[str],
    embedding: np.ndarray,
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    if metadata is None:
        metadata = {}
    record = {
        "id": doc_id,
        "text": text,
        "keywords": keywords,
        "embedding": (
            embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
        ),
        "metadata": metadata,
    }
    return record


def push_to_tidb(record: Dict[str, Any], tidb_config: Dict[str, Any]):
    if pymysql is None:
        raise RuntimeError(
            "pymysql is not installed. Install it with `pip install pymysql` to push to TiDB."
        )
    host = tidb_config.get("host", "127.0.0.1")
    port = int(tidb_config.get("port", 4000))
    user = tidb_config.get("user", "root")
    password = tidb_config.get("password", "")
    database = tidb_config.get("database", "echo")
    keywords_json = json.dumps(record.get("keywords", []))
    embedding_json = json.dumps(record.get("embedding", []))
    metadata_json = json.dumps(record.get("metadata", {}))
    sql = (
        "REPLACE INTO semantic_vectors (id, text, keywords, embedding, metadata) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    conn = None
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
        )
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    record.get("id"),
                    record.get("text"),
                    keywords_json,
                    embedding_json,
                    metadata_json,
                ),
            )
        conn.commit()
    except Exception as e:
        logger.exception("Failed to push record to TiDB: %s", e)
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    logger.info("Starting semantic_processor sample run...")
    nlp = load_spacy_model()
    embedder = load_embedder()
    kb = load_keybert(embedding_model=embedder)
    sample_texts = [
        "OpenAI released GPT-5 and the community is excited about the improvements in reasoning.",
        "TiDB is MySQL-compatible and is often used for scalable OLTP workloads.",
    ]
    for i, doc in enumerate(sample_texts):
        doc_id = f"doc_{i+1}"
        cleaned = clean_text(doc)
        chunks = chunk_text(cleaned, max_chars=500)
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{idx+1}"
            keywords = extract_keywords_keybert(chunk, keybert_model=kb, top_n=8)
            embeddings = get_embeddings([chunk], embedder=embedder)
            emb = embeddings[0] if embeddings.size else np.array([])
            record = create_vector_record(
                chunk_id, chunk, keywords, emb, metadata={"source": "sample"}
            )
            print(json.dumps(record, indent=2))
    logger.info(
        "Sample run completed. To push records to TiDB, configure tidb_config and call push_to_tidb(record, tidb_config)"
    )
