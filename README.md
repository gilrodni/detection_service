# GenAI Detection Service

FastAPI application that classifies user prompts into policy topics (healthcare, finance, legal, and HR) via OpenAI's GPT API. It exposes three endpoints: `/detect`, `/protect`, and `/logs`.

## Features
- LLM-powered topic detection with a deterministic keyword fallback for resiliency.
- Latency-sensitive `/protect` endpoint that returns the first detected topic ASAP.
- Postgres-backed auditing exposed via `/logs`, retaining timestamp/prompt/topic history.
- Settings-driven configuration with defaults for AIM Security's proxy (`OPENAI_BASE_URL`) and API key.
- Dockerfile + docker-compose for one-command local runs (API + Postgres).

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
2. **Configure secrets & database**
   The service ships with AIM Security's proxy key baked in for convenience. Override it via environment variables if needed:
   ```
   OPENAI_API_KEY=your-key
   OPENAI_BASE_URL=https://api.aim.security/fw/v1/proxy/openai
   OPENAI_MODEL=gpt-4.1
   DB_HOST=localhost
   DB_PORT_CLIENT=5432
   DB_PORT_SERVER=5432
   DB_USER=postgres
   DB_PASSWORD=postgres
   DB_NAME=detection
   ```
3. **Run locally**
   - Start Postgres first (either via `docker-compose up db` or `docker-compose up` and stop the API container).
   - Point your `.env` to that DB and then launch the API directly:
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
1. **Postgres persistence vs. latency** – Writing every call to Postgres adds a few extra ms but guarantees durable, centralized logs even when multiple API pods run behind the same DB.
2. **Full prompt storage** – Keeping the entire prompt meets the assignment requirements but increases storage footprint; redact or encrypt if you handle sensitive data.


## Next steps

1. Add caching (like Redis) for repeated prompts to make responses faster and cheaper.
2. Save logs to a temporary place first (file or Redis), and let another process write them to the database so requests don’t get blocked.
3. Improve the fallback logic (for example more keywords, better rules)
4. Add functional tests.
5. Measure precision and recall using labeled data.
4. Tweak the prompts so the model sticks to the JSON format and handles edge cases better.
5. Add basic security: HTTPS, login/permissions, and safe handling of secrets.
6. Set up CI/CD and a simple cloud deployment (infrastructure, health checks, scaling).
7. Let each customer customize their own topics.
8. Implement rate limiting per user/IP to prevent abuse and avoid hitting API rate limits.
9. Add retries logic.
10. Evaluate different model sizes and pick the best tradeoff between cost, speed, and accuracy. Consider using an ensemble if needed.
