# Setup Instructions

## Quick Setup (1 minute)

### 1. Make scripts executable

```bash
chmod +x run.sh test.sh
```

### 2. Start the system

```bash
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
