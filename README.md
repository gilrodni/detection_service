# GenAI Detection Service

FastAPI application that classifies user prompts into policy topics (healthcare, finance, legal, and HR) via OpenAI's GPT API. It exposes three endpoints: `/detect`, `/protect`, and `/logs`.

## Features
- LLM-powered topic detection with a deterministic keyword fallback for resiliency.
- Latency-sensitive `/protect` endpoint that returns the first detected topic ASAP.
- In-memory auditing exposed via `/logs`.
- Settings-driven configuration with defaults for AIM Security's proxy (`OPENAI_BASE_URL`) and API key.
- Dockerfile + docker-compose for one-command local runs.

## Project Layout
```
.
├── app/
│   ├── config.py
│   ├── main.py
│   ├── models.py
│   ├── routers/
│   │   └── detection.py
│   └── services.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Getting Started
1. **Create a virtual environment & install deps**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
2. **Configure secrets (optional)**
   The service ships with AIM Security's proxy key baked in for convenience. Override it via environment variables if needed:
   ```
   OPENAI_API_KEY=your-key
   OPENAI_BASE_URL=https://api.aim.security/fw/v1/proxy/openai
   OPENAI_MODEL=gpt-4.1
   ```
3. **Run locally**
   ```bash
   uvicorn app.main:app --reload
   ```
4. **Play with the API**
   - Swagger: `http://localhost:8000/docs`
   - Health: `http://localhost:8000/health`

### Via Docker
```bash
docker-compose up --build
```

## API Overview
- `POST /detect` → classify the prompt and return all detected topics.
- `POST /protect` → fail-fast variant returning the first detected topic.
- `GET /logs` → audit records containing timestamp, route, prompt, and result.

### Example
```bash
curl -s -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{
        "prompt":"How would you budget payroll during a hiring freeze?",
        "settings":{"health":false,"finance":true,"legal":true,"hr":true}
      }'
```
```json
{"detected_topics":["finance","hr"]}
```

## Trade-offs
1. **In-memory audit log** – Fast to implement but volatile; restarts wipe the log. Persisting to Postgres/S3 would be a next step if durability matters.
2. **Single LLM call per request** – Keeps the implementation simple but `/protect` cannot literally stream the first topic; instead it instructs the LLM to return at most one topic. A streaming API or multi-prompt fan-out could further cut latency.
3. **Keyword fallback** – Ensures deterministic behavior when the LLM misbehaves, though accuracy is limited versus the model. Adding evaluation + retraining would improve confidence.

## Next steps
1. Persist audit logs and detection metrics to durable storage (Postgres or a data lake) for compliance.
2. Add automated tests that stub the OpenAI client plus contract tests for the keyword fallback.
3. Implement caching / batching for repeated prompts to reduce cost and latency.
4. Introduce observability hooks (structured logging & tracing) plus configurable SLAs for `/protect`.

