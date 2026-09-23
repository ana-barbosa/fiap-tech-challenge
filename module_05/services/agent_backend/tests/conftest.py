import os
import tempfile
from pathlib import Path

import chromadb
from chromadb.config import Settings

os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
os.environ.setdefault("CRM_BASE_URL", "http://crm.test")
os.environ.setdefault("CONVERSATION_RETENTION_DAYS", "60")
os.environ.setdefault("CONVERSATION_HISTORY_LIMIT", "30")
os.environ.setdefault("TELEGRAM_BOT_INTERNAL_URL", "http://telegram_bot.test")
os.environ.setdefault("WEBSITE_PUBLIC_URL", "http://website.test")
os.environ.setdefault("FOLLOWUP_INACTIVITY_SECONDS", "120")
os.environ.setdefault("FOLLOWUP_POLL_INTERVAL_SECONDS", "30")
os.environ.setdefault("SUMMARY_IDLE_SECONDS", "60")
os.environ.setdefault("SUMMARY_POLL_INTERVAL_SECONDS", "30")
os.environ.setdefault("RATE_LIMIT_MAX_REQUESTS", "20")
os.environ.setdefault("RATE_LIMIT_WINDOW_SECONDS", "60")

_chroma_dir = Path(tempfile.mkdtemp()) / "chroma"
os.environ["CHROMA_PATH"] = str(_chroma_dir)

os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.sqlite")

_seed_client = chromadb.PersistentClient(path=str(_chroma_dir), settings=Settings(anonymized_telemetry=False))

_seed_client.get_or_create_collection("listings").upsert(
    ids=["1", "2", "3"],
    documents=[
        "apartment para rent em Centro, Taubaté. Apartamento claro e tranquilo, perto do comércio.",
        "house para sale em Praia Grande, Ubatuba. Casa de praia a poucos metros da areia.",
        "apartment para sale em Centro, São José dos Campos. Apartamento amplo com vista para a cidade.",
    ],
    metadatas=[
        {"city": "Taubaté", "property_type": "apartment", "listing_type": "rent", "price": 2000.0, "rooms": 2},
        {"city": "Ubatuba", "property_type": "house", "listing_type": "sale", "price": 650000.0, "rooms": 3},
        {
            "city": "São José dos Campos",
            "property_type": "apartment",
            "listing_type": "sale",
            "price": 480000.0,
            "rooms": 3,
        },
    ],
)
_seed_client.get_or_create_collection("geo").upsert(
    ids=["Taubaté", "Ubatuba"],
    documents=[
        "Taubaté é um município brasileiro do estado de São Paulo, no interior, sem litoral.",
        "Ubatuba é um município litorâneo de São Paulo, conhecido por suas praias.",
    ],
    metadatas=[{"city": "Taubaté"}, {"city": "Ubatuba"}],
)
_seed_client.get_or_create_collection("roi_summary").upsert(
    ids=["Taubaté|Centro|apartment"],
    documents=[
        "Imóveis do tipo apartment no bairro Centro, Taubaté, têm yield bruto estimado de 7.20% ao ano."
    ],
    metadatas=[{"city": "Taubaté", "neighborhood": "Centro", "property_type": "apartment", "gross_yield": 0.072}],
)
_seed_client.get_or_create_collection("financing_kb").upsert(
    ids=["itbi", "financiamento_programas"],
    documents=[
        "O ITBI é um imposto municipal cobrado na transferência de um imóvel, geralmente "
        "entre 2% e 3% do valor da transação, variando por município.",
        "O Minha Casa Minha Vida oferece taxas de juros reduzidas e subsídio para famílias "
        "de baixa e média renda, com condições que variam por faixa de renda.",
    ],
    metadatas=[{"source_file": "itbi.pdf"}, {"source_file": "financiamento_programas.pdf"}],
)
