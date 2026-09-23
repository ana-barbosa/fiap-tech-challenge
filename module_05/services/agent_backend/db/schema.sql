CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    history_json TEXT NOT NULL,        -- JSON list of {"role": "user"|"assistant", "content": str}
    qualification_json TEXT NOT NULL,  -- JSON dict, Portuguese-aliased (same shape returned by /chat)
    current_specialist TEXT NOT NULL CHECK (current_specialist IN ('real_estate', 'mortgage_advisor')),
    shown_listings_json TEXT NOT NULL, -- JSON dict: {property_id (str): {city, price, rooms, property_type, ..., followed_up_at?}}
    last_active_at TEXT NOT NULL,      -- ISO 8601 UTC
    channel TEXT NOT NULL DEFAULT 'website' CHECK (channel IN ('website', 'telegram')),
    summary TEXT                       -- NULL = not summarized as of the current state (reset on every save())
);

-- Observability differentiator: one row per /chat turn (not per internal model.invoke() call
-- within a turn's ReAct loop). prompt/response are PII-redacted before insert (see redact.py) -
-- this is the only place full prompt/response text is ever persisted in this codebase.
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    specialist TEXT NOT NULL,          -- 'real_estate' | 'mortgage_advisor'
    created_at TEXT NOT NULL,          -- ISO 8601 UTC
    latency_ms INTEGER NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    rag_sources_json TEXT NOT NULL,    -- {"buscar_imoveis": [ids...], ...} - ids only, never raw content
    prompt_redacted TEXT NOT NULL,     -- this turn's user message, PII-scrubbed
    response_redacted TEXT,            -- final reply, PII-scrubbed (NULL on error)
    error TEXT,                        -- NULL on success
    injection_suspected INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_conversation_id ON llm_calls(conversation_id);
