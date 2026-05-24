# Medical Assistant: Fine-tuned LLM with LangChain RAG Pipeline

A locally-run medical assistant that combines fine-tuned language models with retrieval-augmented generation (RAG) to provide evidence-based clinical guidance. The system answers doctors' questions with relevant medical knowledge from multiple sources, accesses patient records, identifies pending exams, and enforces safety guardrails to prevent unsafe recommendations.

---

## Folder structure

```
module_03/
├── P1-DownloadDatasets.py              # Download 4 medical datasets
├── P2-DataPreparation.ipynb            # Load, process, and consolidate datasets
├── P3-FineTuning.ipynb                 # Fine-tune Phi-3 Mini with LoRA
├── P4-LangChainPipeline.ipynb          # RAG pipeline + LangGraph orchestration
├── data/
│   ├── raw/                            # Raw downloaded datasets
│   │   ├── pubmedqa/                   # PubMedQA Q&A pairs
│   │   ├── medquad/                    # MedQuAD XML files
│   │   ├── epfl_guidelines/            # Clinical practice guidelines
│   │   └── synthea/csv/                # Synthetic patient records
│   └── processed/
│       ├── medical_data.jsonl          # Consolidated training data (25,890 samples)
│       ├── medical_data_train.jsonl    # 80% training split
│       └── medical_data_val.jsonl      # 20% validation split
├── models/
│   └── phi3_medical_lora/              # Fine-tuned LoRA adapters
├── outputs/
│   ├── medical_assistant.log           # Runtime logs
│   ├── audit_log.jsonl                 # Audit trail of all queries
│   └── alert_report_*.json             # Daily pending exam alert reports
└── README.md                           # This file
```

---

## Datasets

We integrated four complementary medical data sources:

| Dataset | Size                            | Purpose | Why relevant |
|---------|---------------------------------|---------|--------------|
| **PubMedQA** | 1K Q&A pairs                    | Medical research questions + evidence-based answers | Trains domain knowledge on clinical evidence and research-backed decision making |
| **MedQuAD** | 47K Q&A pairs (capped: 5K)      | Curated medical Q&A from NIH, Mayo Clinic, CDC | High-quality, trusted health information from authoritative sources |
| **EPFL Guidelines** | 38K clinical guidelines (capped: 5K) | Structured clinical protocols and treatment pathways | Provides explicit decision trees, imaging protocols, and treatment algorithms |
| **Synthea** | 600K synthetic patient records (capped: 15K) | Realistic EHR data with diagnoses, medications, procedures | Real-world context for how protocols apply to actual patients with comorbidities |

**Data capping rationale:** We deliberately limit dataset size to ~25,890 total samples for two reasons:
1. **Demonstrating technique over accuracy** — This project showcases the fine-tuning + RAG architecture, not production-scale accuracy. A smaller dataset trains faster and is reproducible locally.
2. **Resource constraints** — Fine-tuning on M1 Mac and collab GPUs is resource-limited. Capped data runs in reasonable time (15–20 minutes).

All datasets are publicly available, de-identified (Synthea) or already anonymized (others), and free to use.

---

## Tech stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Base Model** | Phi-3 Mini (3.8B) | Lightweight, fast LLM optimized for M1 Mac |
| **Fine-tuning** | LoRA (mlx-lm) | Parameter-efficient adaptation without full retraining |
| **Model Serving** | Ollama | Local LLM inference without cloud dependency |
| **Vector Store** | FAISS (in-memory) | Fast semantic search over chunked medical documents |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 | Efficient (~80 MB) CPU-based text embeddings |
| **Orchestration** | LangGraph | 5-node state machine coordinating patient context, retrieval, and response generation |
| **Patient DB** | SQLite | Local storage for patients, exams, appointments |
| **Language** | Python 3.11 | Notebooks for exploration and iteration |
| **Data Format** | JSONL | Efficient line-based storage with source attribution |

---

## Requirements

**Local machine:**
- Python 3.9+
- Ollama running on host machine (required for P4 inference)
  - Download: https://ollama.ai
  - Required model: `phi3` (pull with `ollama pull phi3`)
  - Default URL: `http://localhost:11434`

---

## Architecture overview

```
Download Datasets (P1) [Python script]
├─ Download PubMedQA data
├─ Download MedQuAD data
├─ Download Synthea data
└─ Output: Raw datasets to data/raw/

       ↓

Data Preparation (P2)
├─ Load: PubMedQA, MedQuAD, EPFL, Synthea
├─ Process: Normalize, clean, anonymize
├─ Consolidate: Merge with source preservation
└─ Output: 25,890 training samples (JSONL)

       ↓

Fine-tuning (P3) [Colab GPU recommended]
├─ Load: medical_data_train.jsonl (80%)
├─ Tokenize: max 512 tokens
├─ LoRA Config: rank=8, alpha=16
├─ Train: 3 epochs, batch=2
├─ Validate: medical_data_val.jsonl (20%)
└─ Output: Phi-3 LoRA adapters

       ↓

RAG Pipeline (P4) [Local M1 Mac]
├─ Chunk: 15,204 document chunks
├─ Embed: all-MiniLM-L6-v2 → FAISS index
├─ Retrieve: Top-3 chunks per query
└─ LangGraph State Machine:
    1. get_patient_context        → Fetch patient data from SQLite
    2. retrieve_medical_knowledge → Query FAISS for relevant docs
    3. generate_response          → LLM generates clinical guidance
    4. validate_response          → Safety check + source attribution
    5. log_interaction            → Audit trail (JSONL)
```

---

## Execution

**Run in order:**

### P1: Download Datasets
```bash
python P1-DownloadDatasets.py
```
- Creates folder structure in `data/raw/`
- Downloads 3 datasets to `data/raw/`

### P2: Data Preparation
```bash
jupyter notebook P2-DataPreparation.ipynb
```
- Loads all datasets from `data/raw/`
- Consolidates into `data/processed/medical_data.jsonl` with source preservation (25,890 samples)
- Creates 80/20 train/validation split
- Output: `data/processed/medical_data_train.jsonl` (20,712 samples), `medical_data_val.jsonl` (5,178 samples)

### P3: Fine-tuning ⚠️ **GPU required**
```bash
jupyter notebook P3-FineTuning.ipynb
```
- Fine-tunes Phi-3 Mini on training data with LoRA
- Saves adapters to `models/phi3_medical_lora/`
- Output: LoRA adapter weights

### P4: LangChain RAG Pipeline
```bash
jupyter notebook P4-LangChainPipeline.ipynb
```
- Loads fine-tuned model via Ollama
- Chunks medical documents → FAISS index
- Runs 7 demo queries with patient context
- Generates audit logs and alert reports

**Important notes:**
- P1 and P2 are quick and can run locally
- **P3 must run on GPU** (Colab recommended) — fine-tuning on CPU is impractical
- P4 runs locally after fine-tuning completes; transfer model adapters back to your machine

---

## Outputs and artifacts

**Critical outputs:**

1. **Processed training data** (`data/processed/`)
   - `medical_data_train.jsonl` — 20,712 samples for fine-tuning
   - `medical_data_val.jsonl` — 5,178 samples for validation

2. **Fine-tuned model** (`models/phi3_medical_lora/`)
   - LoRA adapter weights (~50 MB)
   - Can be loaded into Ollama or other inference frameworks

3. **FAISS index** (created in P4, in-memory)
   - 15,204 vectorized document chunks
   - Built on-the-fly from processed data; not persisted to disk

4. **Audit trail** (`outputs/audit_log.jsonl`)
   - Every query, response, and safety flag
   - JSONL format: one interaction per line
   - Used for compliance and debugging

5. **Alert reports** (`outputs/alert_report_*.json`)
   - Daily pending exam alerts for all patients
   - Structured recommendations for each patient

---

## Medical Assistant Capabilities

**What it can do:**

✅ **Contextualized clinical guidance** — Combines patient history, pending exams, and relevant medical knowledge  
✅ **Evidence-based recommendations** — Cites sources (PubMedQA, MedQuAD, EPFL Guidelines, Synthea)  
✅ **Safety validation** — Flags direct prescriptions and enforces human-in-the-loop approval  
✅ **Audit trail** — Logs every query, patient accessed, and safety flag for compliance  
✅ **Automated workflows** — Daily pending exam alerts for all patients  
✅ **Patient data retrieval** — Accesses diagnoses, medications, allergies, pending tests from SQLite  

**Safety guardrails:**

- **Pattern-based detection** — Flags responses containing phrases like "I prescribe," "start taking," "increase the dose"
- **Mandatory disclaimer** — Every response includes: "⚠️ Human Validation Required — This is informational support only. All prescriptions, dosage changes, and treatment decisions must be reviewed and approved by the attending physician before implementation."
- **Source accountability** — Every response lists which documents were used, enabling physician verification
- **Allergy awareness** — Patient allergies are checked in context (e.g., warns against penicillin-based antibiotics for penicillin-allergic patients)

**Limitations:**

❌ **Does not make final treatment decisions** — Always defers to physician approval  
❌ **Retrieval-limited** — Responses reflect data in FAISS index; no real-time internet access  
❌ **No patient data modification** — Read-only access to SQLite (intentional safety boundary)  
❌ **Hallucination risk** — LLM may generate plausible-sounding but incorrect medical advice  
❌ **No real-time updates** — Guidelines in dataset are frozen; doesn't reflect latest protocols  

---

## Inference Examples

### Example 1: Heart Failure with Elevated BNP

**Query:** "What does an elevated BNP of 450 pg/mL indicate in a heart failure patient and what should we monitor?"  
**Patient:** Carlos Oliveira, 72y, CHF + AFib, pending Echocardiogram

**Response excerpt:**
> Based on established medical knowledge, elevated BNP of 450 pg/mL indicates worsening cardiac function. You should monitor:
> - Dyspnea, orthopnea, paroxysmal nocturnal dyspnea
> - Renal function (diuretics can cause electrolyte imbalances)
> - INR levels (Warfarin for AFib stroke prevention)
> - Blood pressure closely (hypertension exacerbates HF)
> - Await echocardiogram results before therapy adjustments
> ⚠️ Human Validation Required — All treatment decisions require physician approval.

**Sources used:**
- MedQuAD (2 chunks)  
- EPFL Guidelines (1 chunk)

**Safety status:** ✅ SAFE (no direct prescriptions)

---

### Example 2: Allergy Cross-Reactivity (Safety Flag)

**Query:** "Can this patient receive Amoxicillin for a bacterial infection?"  
**Patient:** João Silva, 65y, Penicillin allergy, pending HbA1c + renal panel

**Response:**
> ⚠️ SAFETY FLAG: Direct prescription language detected — physician review mandatory.
> 
> Based on the patient's allergy profile, Amoxicillin carries cross-reactivity risk with penicillin allergies. Physician should review before prescribing. Consider alternative antibiotics (fluoroquinolones, macrolides, cephalosporins with caution). Pending renal function test will inform choice.
> ⚠️ Human Validation Required...

**Sources used:**
- MedQuAD (2 chunks)  
- EPFL Guidelines (1 chunk)

**Safety status:** ⚠️ FLAGGED (pattern "i would advise" triggered safety check)

---

### Example 3: Diabetes Management

**Query:** "Patient's HbA1c is 8.2%, above the 7% target. What are evidence-based next steps?"  
**Patient:** Roberto Ferreira, 55y, Type 2 Diabetes, pending microalbumin ratio

**Response excerpt:**
> Given HbA1c 8.2% (above target), consider:
> 1. Review current medications (Metformin 1000mg already on board)
> 2. Dietary consultation with registered dietitian
> 3. Increase self-monitoring of blood glucose
> 4. Educational resources on diabetes self-management
> 5. Await microalbumin results before adjusting renal-dependent meds
> 
> Potential intensification strategies: DPP-4 inhibitor, SGLT2 inhibitor, or insulin (requires physician evaluation). All changes require Dr. Pedro Lima's approval.

**Sources used:**
- MedQuAD (2 chunks)  
- PubMedQA (1 chunk)

**Safety status:** ✅ SAFE
