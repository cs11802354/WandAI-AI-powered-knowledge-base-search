# Setup Instructions

## Quick Setup (1 minute)

### 1. Make scripts executable

```bash
chmod +x run.sh test.sh
```

### 2. Start the system

```bash
before running this command kindly replace open api key with this in ".env" file
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
./run.sh
```

Wait ~50 seconds for services to start (local model download on first run takes 2-3 minutes).

### 3. Run tests

```bash
./test.sh
```

## That's it!

Access points:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs  
- **Celery Monitor**: http://localhost:5555

## Troubleshooting

**If services fail to start:**
```bash
docker compose logs api
docker compose logs celery_worker
```

**Complete reset:**
```bash
docker compose down -v
./run.sh
```
