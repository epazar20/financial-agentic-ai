
# Finansal Agentic AI Projesi
=============================

Bu proje PRD_DEPOSIT.md'de tanımlanan "Maaş Yatış Senaryosu" için multi-agent mimarisi ile geliştirilmiş bir finansal danışman sistemidir.

## 🏗️ Mimari

### Servisler:
1. **langgraph-agents** (Flask orchestrator)
   - HTTP endpoints:
     - `POST /simulate_deposit` -> Maaş yatışı simülasyonu
     - `GET /stream` -> Server-Sent Events stream
     - `POST /action` -> Kullanıcı onayı (approve/reject)
     - `POST /kafka/publish` -> Kafka event yayınlama
   - Environment variables ile servis bağlantıları
   - Dockerfile dahil (port 5000)

2. **mcp-finance-tools** (Node.js mock MCP server)
   - Mock endpoints: transactions.query, userProfile.get, risk.scoreTransaction, market.quotes, savings.createTransfer
   - Dockerfile dahil (port 4000)

3. **web-ui** (Next.js)
   - SSE stream'e bağlanan basit UI
   - Approve/Reject butonları Flask orchestrator'a POST eder

## 🚀 Kurulum ve Çalıştırma

### 1. Environment Variables Ayarlama

```bash
# .env dosyası oluşturun
cp env.example .env

# .env dosyasını düzenleyin ve gerçek değerleri girin
nano .env
```

**Önemli:** `HUGGINGFACE_API_KEY` değerini mutlaka ayarlayın!

### 2. Docker Compose ile Çalıştırma

```bash
# Tüm servisleri build et ve çalıştır
docker compose up --build -d

# Logları takip et
docker compose logs -f langgraph-agents
```

### 3. Servis Sağlık Kontrolü

```bash
# Servislerin çalışıp çalışmadığını kontrol et
curl http://localhost:5001/health
curl http://localhost:4000/health
curl http://localhost:3000
```

## 🧪 Test Senaryosu

### 1. API ile Test

```bash
# Maaş yatışı simülasyonu
curl -X POST http://localhost:5001/simulate_deposit \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "test_user", "amount": 25000, "correlation_id": "test_123"}'
```

### 2. Kafka ile Test

```bash
# Kafka event yayınlama
curl -X POST http://localhost:5001/kafka/publish \
  -H 'Content-Type: application/json' \
  -d '{"topic": "transactions.deposit", "data": {"payload": {"userId": "kafka_user", "amount": 25000}}}'
```

### 3. Web UI ile Test

- http://localhost:3000 adresine gidin
- "💰 25.000₺ Maaş Yatışı" butonlarına tıklayın
- Real-time bildirimleri takip edin

## 🔒 Güvenlik

### Environment Variables
- Tüm secret key'ler environment variable'larda saklanır
- `.env` dosyası `.gitignore`'da yer alır
- `env.example` dosyası örnek konfigürasyon içerir

### Güvenlik Kontrol Listesi
- [ ] `HUGGINGFACE_API_KEY` ayarlandı
- [ ] `.env` dosyası oluşturuldu
- [ ] Production'da `FLASK_DEBUG=false` ayarlandı
- [ ] CORS origins production URL'leri ile güncellendi

## 📁 Dosya Yapısı

```
├── langgraph-agents/          # Flask orchestrator
│   ├── app.py                 # Ana uygulama
│   ├── config.py              # Konfigürasyon
│   ├── services.py            # Servis bağlantıları
│   ├── workflow.py            # LangGraph workflow
│   ├── api.py                 # API endpoints
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile
├── mcp-finance-tools/         # Mock MCP server
│   ├── index.js
│   ├── package.json
│   └── Dockerfile
├── web-ui/                    # Next.js UI
│   ├── pages/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml         # Servis orkestrasyonu
├── .gitignore                 # Git ignore kuralları
├── .dockerignore              # Docker ignore kuralları
├── env.example                # Environment variables örneği
└── README.md                  # Bu dosya
```

## 🔧 Konfigürasyon

### Environment Variables

| Variable | Açıklama | Varsayılan |
|----------|----------|------------|
| `HUGGINGFACE_API_KEY` | Hugging Face API anahtarı | **Zorunlu** |
| `HUGGINGFACE_API_URL` | Hugging Face API endpoint | `https://router.huggingface.co/novita/v3/openai/chat/completions` |
| `HUGGINGFACE_MODEL` | Hugging Face model | `deepseek/deepseek-v3-0324` |
| `REDIS_URL` | Redis bağlantı URL'si | `redis://financial-redis:6379/0` |
| `QDRANT_HOST` | Qdrant host | `financial-qdrant` |
| `QDRANT_PORT` | Qdrant port | `6333` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | `financial-kafka:9092` |
| `OLLAMA_BASE_URL` | Ollama base URL | `http://financial-ollama:11434` |
| `MCP_BASE_URL` | MCP tools URL | `http://mcp-finance-tools:4000` |
| `FLASK_HOST` | Flask host | `0.0.0.0` |
| `FLASK_PORT` | Flask port | `5000` |
| `FLASK_DEBUG` | Flask debug mode | `false` |
| `CORS_ORIGINS` | CORS origins | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | Web UI API URL | `http://localhost:5001` |
| `NEXT_PUBLIC_STREAM_URL` | Web UI stream URL | `http://localhost:5001/stream` |

## 🐛 Sorun Giderme

### Yaygın Sorunlar

1. **CORS Hatası**
   ```bash
   # CORS origins'i kontrol et
   echo $CORS_ORIGINS
   ```

2. **Hugging Face API Hatası**
   ```bash
   # API key'i kontrol et
   echo $HUGGINGFACE_API_KEY
   ```

3. **Servis Bağlantı Hatası**
   ```bash
   # Servis loglarını kontrol et
   docker compose logs langgraph-agents
   ```

## 📝 Notlar

- Bu minimal demo skeleton'dır
- Production için robust error handling, authentication, SSL, proper LLM calls ve audit logs eklenmelidir
- SSE broadcaster yerine WebSocket veya Socket.IO kullanılabilir
