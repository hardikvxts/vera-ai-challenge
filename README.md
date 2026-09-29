# Vera AI - Merchant Engagement Bot

A merchant engagement service built for the Magicpin Vera AI Challenge. The service ingests contextual business signals across four dimensions—category, merchant, customer, and triggers—and generates timely, high-impact growth recommendations and automated conversational replies.

## Architecture

The system uses a hybrid approach combining LLM-powered generation with a deterministic rule engine for high availability:

1. **Context Engine**: Aggregates four contextual layers:
   - **Category Context**: Industry benchmarks, seasonal trends, and voice guidelines.
   - **Merchant Context**: Business profile, metrics (CTR, views, calls), active promotions, and subscription state.
   - **Customer Context**: Interaction history, visit frequency, and lifecycle status.
   - **Trigger Context**: High-priority events such as subscription renewals, recall alerts, and performance drops.
2. **Generation Pipeline**: Constructs structured prompts for Groq (Llama 3.3 70B) to produce concise, metrics-grounded recommendations with explicit calls to action.
3. **Deterministic Fallback**: If LLM calls encounter rate limits or network errors, the engine seamlessly falls back to rule-based templates so service availability remains 100%.
4. **Context Versioning**: Rejects out-of-order or stale payload updates using incremental version checking.

## Project Structure

```
vera-ai-challenge/
├── app.py                 # FastAPI application and route handlers
├── store.py               # In-memory context and conversation state
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── services/
│   ├── data_loader.py     # Seed dataset ingestion
│   ├── decision.py        # Action classification rules
│   ├── llm.py             # Groq LLM integration
│   ├── message_builder.py # Message construction & fallback engine
│   └── prompt_builder.py  # Context-aware prompt generation
└── data/                  # Seed datasets (categories, merchants, triggers)
```

## API Endpoints

### System & Health
- `GET /`: Service status and summary.
- `GET /v1/healthz`: Uptime and count of loaded contexts.
- `GET /v1/metadata`: Project submission details and approach.

### Core Challenge Endpoints
- `POST /v1/context`: Ingests scoped context (`category`, `merchant`, `customer`, `trigger`) with version validation.
- `POST /v1/tick`: Processes active triggers and returns recommended actions and message drafts.
- `POST /v1/reply`: Analyzes merchant replies and determines next steps (`send`, `wait`, or `end`).
- `POST /v1/teardown`: Clears active contexts and resets conversation state.

### Testing & Debug
- `GET /v1/debug`: Inspects available seed keys.
- `GET /v1/sample`: Returns seed merchant profiles.
- `GET /v1/simulate/{idx}`: Generates a test recommendation for a given merchant index.

## Getting Started

### 1. Set Up Environment
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your Groq API key (optional — rule-based fallback will operate automatically if not provided):
```
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run the Application
```bash
uvicorn app:app --reload --port 8000
```
Interactive API documentation will be available at `http://127.0.0.1:8000/docs`.

## Author

**Hardik Vats**  
Email: [hardiksharmavats@gmail.com](mailto:hardiksharmavats@gmail.com)  
GitHub: [@hardikvxts](https://github.com/hardikvxts)
