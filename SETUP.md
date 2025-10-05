# Setup Instructions

## Quick Setup (1 minute)

### 1. Make scripts executable

```bash
chmod +x run.sh test.sh
```

### 2. Start the system

```bash
before running this command kindly replace key with this in ".env" file (please concatenate all part)
part1:sk-proj-G-
part2:akIaoEOp3as8EFktpftBEUOMUAK3y-BnVOCpuO5XRJRpBTBme8Nnewzp
part3:_k1wMkK9W8KfC0A2T3BlbkFJUT6Dx5nw9Em5DrVIU8JFM4Sirjptw58L-SnlpsmDWmu1xrLYmAaXBTb1FOceWr6vTHOpuFHBMA
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
