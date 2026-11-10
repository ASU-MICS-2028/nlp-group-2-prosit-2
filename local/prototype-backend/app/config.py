from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_fallback_model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 8192
    generated_dir: str = "generated"
    demand_log_path: str = "data/demand_log.jsonl"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Step 1: sessions, jobs, users and tokens live in this SQLite file, so a restart loses nothing
    database_url: str = "sqlite:///data/builder.db"
    # Step 2: how long a login lasts, and how many new requests a user may make per 24 hours
    # (each request spends money on the OpenAI key; admins are not limited)
    token_days: int = 7
    daily_request_limit: int = 20
    # Step 4: long-term memory (lasting facts about each person, learned from approved plans)
    memory_enabled: bool = True
    memory_max_facts: int = 20  # kept per person; the oldest are dropped first
    memory_facts_in_prompt: int = 10
    # Step 5: RAG (reuse similar approved designs as examples in the prompt)
    rag_enabled: bool = True
    rag_top_k: int = 3
    # Below this an example is too different to help. 0.25 (not 0.2) drops the two wrong matches seen in
    # app.rag_check; chosen on that same check, so treat its numbers as optimistic.
    rag_min_score: float = 0.25
    # "embedding" (meaning-based, model2vec, free and local) or "tfidf" (shared words only).
    # If the embedding model folder is missing, retrieval falls back to tfidf.
    rag_method: str = "embedding"
    embedding_model_path: str = "data/embedding-model"
    # Chosen on the tuning set in app.rag_check (21/21 right, 0 wrong for any cut 0.30-0.45); see design-doc 7c
    rag_embedding_min_score: float = 0.35

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
