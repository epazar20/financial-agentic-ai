# 📋 PRD: Maaş Yatış Senaryosu - Multi-Agent + Memory Mimarisi

<div align="center">

![Multi-Agent](https://img.shields.io/badge/Architecture-Multi--Agent-blue?style=for-the-badge&logo=robot)
![Memory](https://img.shields.io/badge/Memory-Redis%20%2B%20Qdrant-green?style=for-the-badge&logo=database)
![Event-Driven](https://img.shields.io/badge/Pattern-Event--Driven-orange?style=for-the-badge&logo=apache-kafka)

**Finansal Agentic AI - Maaş Yatış Senaryosu Teknik Dokümantasyonu**

</div>

## 🎯 1. Proje Amacı

Bu PRD (Product Requirements Document), **maaş yatışı** durumunda otomatik olarak devreye giren akıllı finansal danışman sisteminin teknik gereksinimlerini tanımlar.

### 📝 Senaryo Özeti

Kullanıcıya maaş yatması durumunda:
- 🤖 **PaymentsAgent** otomatik işlemleri başlatır
- 🛡️ **RiskAgent** güvenlik ve uyum analizini yapar  
- 📈 **InvestmentAgent** yatırım fırsatları sunar
- 🎯 **CoordinatorAgent** tüm çıktıları Redis (short-term memory) ve Qdrant (long-term memory) ile zenginleştirir
- 📱 Son mesaj kullanıcıya bildirim olarak sunulur

## 🎭 2. Aktörler ve Rolleri

### 2.1 🤖 Agent Rolleri

<div align="center">

| Agent | Rol | MCP Tools | Görev | Çıktı |
|-------|-----|-----------|-------|-------|
| **💳 PaymentsAgent** | Finansal Analist | `transactions.query`<br/>`payments.create`<br/>`savings.createTransfer` | Maaş ödemesini algılama<br/>Bütçe planına göre öneri çıkarma<br/>Transfer hazırlama | Tasarruf önerisi<br/>Transfer planı |
| **🛡️ RiskAgent** | Risk Uzmanı | `risk.scoreTransaction`<br/>`kyc.check` | Gelen maaşın kaynağını analiz etme<br/>Sahtekarlık/kara para riskini kontrol etme | Risk skoru<br/>Güvenlik durumu |
| **📈 InvestmentAgent** | Yatırım Danışmanı | `market.quotes`<br/>`orders.*` | Maaş sonrası uygun yatırım ürünleri önerisi<br/>(Risk durumuna göre) | Yatırım önerileri<br/>Piyasa analizi |
| **🎯 CoordinatorAgent** | Ana Koordinatör | External LLM API<br/>(Hugging Face/OpenAI) | Tüm ajanların çıktısını toplar<br/>Memory'den veri alır<br/>Kişiselleştirilmiş mesaj oluşturur | Final öneri<br/>Kullanıcı mesajı |

</div>

### 2.2 🧠 Memory Katmanları

#### 🔴 Short-Term Memory (Redis)
- **Amaç**: Anlık kullanıcı etkileşimleri
- **İçerik**: 
  - Son konuşma/etkileşimler
  - Önceki 1 günlük onay/red geçmişi
  - Kullanıcı tercihleri ve davranışları
- **TTL**: 24 saat
- **Kullanım**: Hızlı erişim için

#### 🔵 Long-Term Memory (Qdrant Vector DB)
- **Amaç**: Geçmiş analizler ve öğrenme
- **İçerik**:
  - Benzer Kafka event türlerine verilen önceki analiz çıktıları
  - Nomic embed-text ile vektörleştirilmiş veriler
  - Kullanıcı yatırım geçmişi ve tercihleri
- **Kullanım**: RAG (Retrieval Augmented Generation) için Coordinator'a sağlanır

### 2.3 🔧 Tool Calling Mimarisi

<div align="center">

| Agent Kategorisi | LLM | Kullanım Alanı | Örnek |
|------------------|-----|----------------|-------|
| **Non-Coordinator Agents** | Ollama + LLaMA<br/>(Hafif tool-calling modeli) | Tool çağrıları<br/>Basit analizler | `transactions.query()`<br/>`risk.scoreTransaction()` |
| **CoordinatorAgent** | External LLM API<br/>(Hugging Face/OpenAI) | RAG + Memory<br/>Enriched final message | Kişiselleştirilmiş öneri<br/>Kullanıcı mesajı |

</div>

## 🏗️ 3. Teknoloji Yığını

### 3.1 🔧 Backend Orkestrasyon

<div align="center">

| Teknoloji | Rol | Açıklama |
|-----------|-----|----------|
| **🐍 Python LangGraph** | Agent Workflow Orchestration | Multi-agent koordinasyonu ve workflow yönetimi |
| **🌐 Flask REST API** | Dış Dünya Servisleri | Kafka event producer/consumer, MCP server integration |
| **📨 Apache Kafka** | Event Streaming | Mikroservisler arası asenkron iletişim |

</div>

### 3.2 🧠 Memory Sistemleri

<div align="center">

| Teknoloji | Kategori | Açıklama |
|-----------|----------|----------|
| **🔴 Redis** | Short-Term Memory | Hızlı erişim için geçici veri saklama |
| **🔵 Qdrant** | Long-Term Memory | Vector embeddings ile uzun vadeli öğrenme |

</div>

### 3.3 🤖 LLM Katmanları

<div align="center">

| LLM | Kullanım Alanı | Agent |
|-----|----------------|-------|
| **🦙 Ollama (LLaMA)** | Tool-calling modeli | PaymentsAgent, RiskAgent, InvestmentAgent |
| **🌐 External API** | RAG + Memory enriched | CoordinatorAgent |

</div>

### 3.4 🎨 UI/Frontend

<div align="center">

| Teknoloji | Açıklama |
|-----------|----------|
| **🔌 WebSocket** | Real-time bildirim + prompt input |
| **⚡ Server-Sent Events** | Event streaming |
| **🌐 Next.js** | Modern web arayüzü |

</div>

## 🔄 4. Örnek Senaryo - Maaş Yatışı

### 📊 Senaryo Akış Diyagramı

```mermaid
sequenceDiagram
    participant U as 👤 Kullanıcı
    participant K as 📨 Kafka
    participant P as 💳 PaymentsAgent
    participant R as 🛡️ RiskAgent
    participant I as 📈 InvestmentAgent
    participant C as 🎯 CoordinatorAgent
    participant M as 🧠 Memory (Redis+Qdrant)
    participant UI as 📱 Web UI

    U->>K: Maaş yatışı (25.000₺)
    K->>P: transactions.deposit event
    P->>P: transactions.query(userId=123)
    P->>P: savings.createTransfer(amount=7500)
    P->>C: "7.500₺ tasarruf önerisi"
    
    K->>R: Risk analizi tetikle
    R->>R: risk.scoreTransaction(userId=123)
    R->>C: "Risk skoru: 0.05 (düşük)"
    
    K->>I: Yatırım analizi tetikle
    I->>I: market.quotes(assetType=bond)
    I->>C: "Tahvil %28, Hisse %35"
    
    C->>M: Redis: Son 24 saat etkileşimler
    C->>M: Qdrant: Geçmiş yatırım tercihleri
    M->>C: Kullanıcı profil verisi
    
    C->>UI: Kişiselleştirilmiş öneri
    UI->>U: "Tahvile %28 faizle yatırmak ister misin?"
    
    alt Kullanıcı Onayı
        U->>UI: "Evet" tıklar
        UI->>UI: Toast: "İşlem başlatılıyor..."
        UI->>C: approve_all_proposals
        C->>P: Transfer execute emri
        P->>K: payments.executed event
        K->>UI: final-result-report
        UI->>U: "İşlem başarıyla tamamlandı"
    else Kullanıcı Reddi
        U->>UI: "Hayır" tıklar
        UI->>UI: Toast: "Tüm öneriler reddediliyor..."
        UI->>K: all-proposals-rejected event
        K->>UI: Red işlemi tamamlandı
        UI->>U: "İşlem iptal edildi"
    else Özel Mesaj
        U->>UI: "Özel Mesaj" tıklar
        UI->>UI: Modal açılır
        U->>UI: "Sadece tahvil yatırımı yap"
        UI->>UI: Toast: "Özel mesajınız işleniyor..."
        UI->>C: chat_response (özel mesaj)
        C->>C: Mesajı analiz eder
        C->>I: Sadece tahvil yatırımı emri
        I->>K: Tahvil yatırım sonucu
        K->>UI: final-result-report
        UI->>U: "Tahvil yatırımı başarıyla tamamlandı"
    end
```

### 📝 Detaylı Adım Adım Senaryo

#### 🔸 Adım 1: Event Tetikleme
```json
{
  "event": "transactions.deposit",
  "payload": {
    "userId": "123",
    "amount": 25000,
    "timestamp": "2025-09-09T10:00:00Z"
  },
  "meta": {
    "correlationId": "deposit_001",
    "source": "banking_system"
  }
}
```

#### 🔸 Adım 2: PaymentsAgent Analizi
**MCP Tool Çağrıları:**
```javascript
// Geçmiş işlemleri sorgula
transactions.query({
  userId: "123",
  since: "last30d"
});

// Tasarruf transferi öner
savings.createTransfer({
  userId: "123",
  amount: 7500,
  status: "pending"
});
```

**Çıktı:**
> "Maaşın 25.000₺ olarak hesabına geçti. Plan gereği 7.500₺ tasarrufa aktarılabilir."

#### 🔸 Adım 3: RiskAgent Analizi
**MCP Tool Çağrıları:**
```javascript
// Risk skoru hesapla
risk.scoreTransaction({
  userId: "123",
  transaction: {
    type: "deposit",
    amount: 25000,
    source: "salary"
  }
});
```

**Sonuç:**
```json
{
  "score": 0.05,
  "reason": "low risk",
  "factors": ["regular_salary", "known_source", "normal_amount"]
}
```

**Çıktı:**
> "İşlem güvenli, düşük riskli."

#### 🔸 Adım 4: InvestmentAgent Analizi
**Risk Bazlı Strateji:**
- **Low Risk (0.05)** → Agresif yatırım önerileri
- **High Risk (>0.7)** → Temkinli ürünler

**MCP Tool Çağrıları:**
```javascript
// Piyasa verilerini al
market.quotes({
  assetType: "bond",
  tenor: "6m"
});

market.quotes({
  assetType: "equity",
  market: "BIST"
});
```

**Çıktı:**
> "6 aylık tahvil faizi %28, BES fonu %22, hisse senedi endeksi yıllık %35"

#### 🔸 Adım 5: CoordinatorAgent Entegrasyonu
**Input Veriler:**
- **PaymentsAgent** → "25.000₺ maaş, 7.500₺ tasarruf önerisi"
- **RiskAgent** → "low risk (0.05)"
- **InvestmentAgent** → "bond %28, equity %35"
- **Redis** → Son 24 saatteki kullanıcı cevapları ("Evet" → otomatik onay eğilimi)
- **Qdrant** → Önceki benzer maaş yatırımlarında kullanıcı hep tahvil seçmiş

**RAG Process:**
```python
# Qdrant'dan benzer durumları bul
similar_cases = qdrant.search(
    query="salary deposit investment preference",
    filter={"userId": "123"},
    limit=5
)

# Redis'den son etkileşimleri al
recent_interactions = redis.get("user:123:interactions:24h")

# LLM ile kişiselleştirilmiş mesaj oluştur
final_message = llm.generate(
    context={
        "payments": payments_output,
        "risk": risk_output,
        "investment": investment_output,
        "history": similar_cases,
        "preferences": recent_interactions
    }
)
```

**Final Output:**
> "Maaşın 25.000₺ olarak yattı ✅. Bütçene göre 7.500₺ tasarrufa aktarabilirim. Risk puanın düşük görünüyor, önceki tercihlerin de tahvil yönünde olmuş. Bu kez tahvile %28 faizle yatırmak ister misin?"

#### 🔸 Adım 6: Kullanıcı Etkileşimi (Güncellenmiş)

**UI Bildirimi:**
```json
{
  "type": "final_proposal",
  "title": "Maaş Yatışı Bildirimi",
  "message": "Maaşın 25.000₺ olarak yattı ✅",
  "proposal": {
    "action": "transfer_to_savings",
    "amount": 7500,
    "investment": {
      "type": "bond",
      "rate": 0.28,
      "duration": "6m"
    }
  },
  "actions": ["approve", "reject", "custom_message"]
}
```

**Kullanıcı Yanıt Senaryoları:**

**✅ Senaryo A: Tüm Önerileri Onaylama**
```json
{
  "action": "approve_all",
  "userId": "123",
  "correlationId": "deposit_001",
  "timestamp": "2025-09-09T10:05:00Z"
}
```
**Sonuç:** Tüm agent'lar execute edilir, transfer gerçekleşir

**❌ Senaryo B: Tüm Önerileri Reddetme**
```json
{
  "action": "reject_all",
  "userId": "123",
  "correlationId": "deposit_001",
  "timestamp": "2025-09-09T10:05:00Z"
}
```
**Sonuç:** İşlem iptal edilir, kullanıcıya bildirim gönderilir

**💬 Senaryo C: Özel Mesaj ile İstek**
```json
{
  "action": "custom_message",
  "userId": "123",
  "message": "Sadece tahvil yatırımı yap, tasarruf transferini iptal et",
  "correlationId": "deposit_001",
  "timestamp": "2025-09-09T10:05:00Z"
}
```
**Sonuç:** CoordinatorAgent mesajı analiz eder, özel işlemler gerçekleştirir

**Final Execution (Onay Senaryosu):**
```json
{
  "event": "payments.executed",
  "payload": {
    "userId": "123",
    "transactionId": "tx_789",
    "amount": 7500,
    "status": "completed",
    "timestamp": "2025-09-09T10:05:00Z"
  }
}
```

**Final Execution (Özel Mesaj Senaryosu):**
```json
{
  "event": "final-result-report",
  "payload": {
    "userId": "123",
    "result": {
      "message": "Özel isteğiniz doğrultusunda sadece tahvil yatırımı gerçekleştirildi",
      "executed_actions": ["bond_investment"],
      "cancelled_actions": ["savings_transfer"],
      "amount": 5000,
      "investment_type": "bond",
      "rate": 0.28
    },
    "timestamp": "2025-09-09T10:05:00Z"
  }
}
```

## 📨 5. Kafka Topics (Event-Driven Yapı)

### 5.1 📋 Event Topics

<div align="center">

| Topic | Açıklama | Payload Örneği |
|-------|----------|----------------|
| **`transactions.deposit`** | Yeni maaş yatışı | `{userId, amount, timestamp}` |
| **`payments.pending`** | Önerilen otomatik transfer | `{userId, amount, from, to}` |
| **`risk.analysis`** | RiskAgent çıktısı | `{userId, score, reason, factors}` |
| **`investments.proposal`** | Yatırım önerisi | `{userId, products, rates, risk}` |
| **`advisor.finalMessage`** | Kullanıcıya sunulan nihai mesaj | `{userId, message, proposal}` |
| **`payments.executed`** | Onay sonrası işlem sonucu | `{userId, txId, status, amount}` |
| **`all-proposals-approved`** | Tüm öneriler onaylandı | `{userId, correlationId, timestamp}` |
| **`all-proposals-rejected`** | Tüm öneriler reddedildi | `{userId, correlationId, timestamp}` |
| **`chat-analysis`** | Özel mesaj analizi | `{userId, message, analysis, actions}` |
| **`final-result-report`** | Final sonuç raporu | `{userId, result, executed_actions}` |
| **`agent-output`** | Agent çıktıları | `{agent, action, result, correlationId}` |

</div>

### 5.2 🔄 Event Flow

```mermaid
graph LR
    A[transactions.deposit] --> B[payments.pending]
    A --> C[risk.analysis]
    A --> D[investments.proposal]
    B --> E[advisor.finalMessage]
    C --> E
    D --> E
    E --> F{👤 Kullanıcı<br/>Etkileşimi}
    F -->|✅ Evet| G[all-proposals-approved]
    F -->|❌ Hayır| H[all-proposals-rejected]
    F -->|💬 Özel Mesaj| I[chat-analysis]
    G --> J[payments.executed]
    H --> K[İşlem İptal]
    I --> L[agent-output]
    L --> M[final-result-report]
    J --> N[Memory Update]
    K --> N
    M --> N
    
    style A fill:#e1f5fe
    style E fill:#f3e5f5
    style F fill:#fff3e0
    style G fill:#e8f5e8
    style H fill:#ffebee
    style I fill:#f3e5f5
    style M fill:#e8f5e8
```

## 🎨 6. UI Akışı ve Kullanıcı Deneyimi

### 6.1 📱 Bildirim Kartı Tasarımı (Güncellenmiş)

```html
<div class="notification-card">
  <div class="header">
    <span class="icon">💰</span>
    <h3>Maaş Yatışı Bildirimi</h3>
  </div>
  
  <div class="content">
    <p class="amount">Maaşın 25.000₺ yatırıldı.</p>
    <div class="proposal">
      <p><strong>Tasarruf:</strong> 7.500₺ aktarabilirim</p>
      <p><strong>Yatırım Önerisi:</strong> Tahvil %28</p>
      <p class="question">Onaylıyor musun?</p>
    </div>
    
    <!-- Collapse Edilebilir JSON Detayları -->
    <div class="json-details">
      <div class="collapse-header" onclick="toggleCollapse('agent-details')">
        <span>📋 Agent Detayları</span>
        <span class="collapse-icon">▶️</span>
      </div>
      <div class="json-content" id="agent-details" style="display: none;">
        <pre>{JSON içerik}</pre>
      </div>
    </div>
  </div>
  
  <div class="actions">
    <button class="approve" disabled="false">✅ Evet</button>
    <button class="reject" disabled="false">❌ Hayır</button>
    <button class="custom-message" disabled="false">💬 Özel Mesaj</button>
  </div>
  
  <!-- Toast Mesaj Sistemi -->
  <div class="toast-message" id="toast">
    <span class="toast-icon">🔔</span>
    <span class="toast-text">İşlem başlatılıyor...</span>
  </div>
</div>
```

### 6.2 🔄 Real-time Event Handling (Güncellenmiş)

```javascript
// Server-Sent Events bağlantısı
const eventSource = new EventSource('http://localhost:5001/stream');

// Event dinleyicileri
eventSource.addEventListener('agent-output', (event) => {
  const data = JSON.parse(event.data);
  displayAgentOutput(data.agent, data.message, data.result);
});

eventSource.addEventListener('final_proposal', (event) => {
  const data = JSON.parse(event.data);
  showNotification(data.message, data.proposal);
  enableUserActions(); // Butonları aktif et
});

eventSource.addEventListener('final-result-report', (event) => {
  const data = JSON.parse(event.data);
  updateTransactionStatus(data.result);
  disableLoadingState(); // Loading'i kapat
});

// Collapse toggle fonksiyonu
function toggleCollapse(eventId) {
  const content = document.getElementById(eventId);
  const icon = document.querySelector(`[onclick="toggleCollapse('${eventId}')"] .collapse-icon`);
  
  if (content.style.display === 'none') {
    content.style.display = 'block';
    icon.textContent = '🔽';
  } else {
    content.style.display = 'none';
    icon.textContent = '▶️';
  }
}

// Toast mesaj sistemi
function showToast(message) {
  const toast = document.getElementById('toast');
  toast.querySelector('.toast-text').textContent = message;
  toast.style.display = 'flex';
  
  setTimeout(() => {
    toast.style.display = 'none';
  }, 3000);
}

// Kullanıcı aksiyonu (güncellenmiş)
function handleUserAction(action, proposal) {
  // Butonları disabled yap
  disableAllButtons();
  
  // Toast mesaj göster
  showToast(action === 'approve' ? 'İşlem başlatılıyor...' : 
           action === 'reject' ? 'Tüm öneriler reddediliyor...' : 
           'Özel mesajınız işleniyor...');
  
  fetch('/api/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userId: getCurrentUserId(),
      response: action,
      proposal: proposal,
      correlationId: getCurrentCorrelationId()
    })
  });
}

// Özel mesaj modal
function openCustomMessageModal() {
  const modal = document.getElementById('custom-message-modal');
  modal.style.display = 'block';
}

function sendCustomMessage() {
  const message = document.getElementById('custom-message-input').value;
  if (message.trim()) {
    handleUserAction('custom_message', { message: message.trim() });
    closeCustomMessageModal();
  }
}
```

### 6.3 📊 Dashboard Görünümü (Güncellenmiş)

<div align="center">

| Bölüm | İçerik | Güncelleme | Yeni Özellikler |
|-------|--------|------------|-----------------|
| **💰 Maaş Durumu** | Yatış miktarı, tarih | Real-time | Toast bildirimler |
| **📈 Yatırım Önerileri** | Tahvil, hisse, fon oranları | Piyasa verileri | Collapse edilebilir detaylar |
| **🛡️ Risk Analizi** | Risk skoru, güvenlik durumu | Agent çıktısı | JSON içerikler gizli |
| **📋 Bekleyen İşlemler** | Onay bekleyen transferler | Kullanıcı aksiyonu | Disabled state yönetimi |
| **💬 Özel Mesajlar** | Kullanıcı özel istekleri | Modal input | CoordinatorAgent entegrasyonu |
| **🔔 Bildirimler** | Toast mesaj sistemi | 3 saniye otomatik | Modern UI/UX |

</div>

## 🔧 7. Teknik Implementasyon Detayları

### 7.1 🏗️ Mimari Bileşenler

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Next.js Web UI]
        WS[WebSocket Client]
    end
    
    subgraph "API Layer"
        API[Flask REST API]
        SSE[Server-Sent Events]
    end
    
    subgraph "Agent Layer"
        PA[PaymentsAgent]
        RA[RiskAgent]
        IA[InvestmentAgent]
        CA[CoordinatorAgent]
    end
    
    subgraph "Memory Layer"
        REDIS[Redis Cache]
        QDRANT[Qdrant Vector DB]
    end
    
    subgraph "Event Layer"
        KAFKA[Apache Kafka]
        ZK[Zookeeper]
    end
    
    subgraph "External Services"
        MCP[MCP Finance Tools]
        LLM[Hugging Face API]
    end
    
    UI --> API
    WS --> SSE
    API --> PA
    API --> RA
    API --> IA
    API --> CA
    PA --> MCP
    RA --> MCP
    IA --> MCP
    CA --> LLM
    CA --> REDIS
    CA --> QDRANT
    API --> KAFKA
    KAFKA --> ZK
```

### 7.2 🔧 Konfigürasyon Parametreleri

```yaml
# Agent Konfigürasyonu
agents:
  payments:
    savings_rate: 0.30  # %30 otomatik tasarruf
    min_amount: 1000    # Minimum transfer miktarı
    
  risk:
    low_threshold: 0.3  # Düşük risk eşiği
    high_threshold: 0.7 # Yüksek risk eşiği
    
  investment:
    bond_weight: 0.4    # Tahvil ağırlığı
    equity_weight: 0.3  # Hisse ağırlığı
    fund_weight: 0.3    # Fon ağırlığı

# Memory Konfigürasyonu
memory:
  redis:
    ttl: 86400          # 24 saat TTL
    max_connections: 10
    
  qdrant:
    vector_size: 768    # Embedding boyutu
    distance: "cosine"   # Mesafe metriği
    collection: "user_preferences"

# Kafka Konfigürasyonu
kafka:
  bootstrap_servers: "localhost:9092"
  topics:
    deposit: "transactions.deposit"
    pending: "payments.pending"
    risk: "risk.analysis"
    investment: "investments.proposal"
    advisor: "advisor.finalMessage"
    executed: "payments.executed"
```

### 7.3 🧪 Test Senaryoları

#### 🔸 Unit Test Senaryoları
```python
def test_payments_agent():
    """PaymentsAgent'in maaş analizi testi"""
    agent = PaymentsAgent()
    result = agent.analyze_salary_deposit(user_id="123", amount=25000)
    
    assert result.savings_amount == 7500  # %30 tasarruf
    assert result.status == "pending"
    assert result.from_account == "CHK001"
    assert result.to_account == "SV001"

def test_risk_agent():
    """RiskAgent'in risk analizi testi"""
    agent = RiskAgent()
    result = agent.analyze_transaction(user_id="123", amount=25000)
    
    assert result.score <= 1.0
    assert result.score >= 0.0
    assert result.reason in ["low risk", "medium risk", "high risk"]

def test_investment_agent():
    """InvestmentAgent'in yatırım önerisi testi"""
    agent = InvestmentAgent()
    result = agent.get_investment_recommendations(risk_score=0.05)
    
    assert len(result.products) > 0
    assert all(p.rate > 0 for p in result.products)
    assert result.strategy == "aggressive"  # Düşük risk = agresif
```

#### 🔸 Integration Test Senaryoları
```python
def test_end_to_end_scenario():
    """Tam senaryo testi"""
    # 1. Maaş yatışı simüle et
    deposit_event = {
        "userId": "test_user",
        "amount": 25000,
        "timestamp": "2025-09-09T10:00:00Z"
    }
    
    # 2. Kafka event gönder
    kafka_producer.send("transactions.deposit", deposit_event)
    
    # 3. Agent çıktılarını bekle
    payments_output = wait_for_agent_output("PaymentsAgent", timeout=30)
    risk_output = wait_for_agent_output("RiskAgent", timeout=30)
    investment_output = wait_for_agent_output("InvestmentAgent", timeout=30)
    
    # 4. CoordinatorAgent çıktısını bekle
    final_message = wait_for_agent_output("CoordinatorAgent", timeout=60)
    
    # 5. Assertions
    assert payments_output.savings_amount == 7500
    assert risk_output.score < 0.3  # Düşük risk
    assert len(investment_output.products) > 0
    assert "tahvil" in final_message.message.lower()
```

## 📈 8. Performans ve Ölçeklenebilirlik

### 8.1 📊 Performans Metrikleri

<div align="center">

| Metrik | Hedef | Ölçüm |
|--------|-------|-------|
| **Response Time** | < 2 saniye | Agent çıktısı |
| **Throughput** | 1000 req/s | Eşzamanlı kullanıcı |
| **Memory Usage** | < 512MB | Redis cache |
| **Vector Search** | < 100ms | Qdrant query |
| **Kafka Latency** | < 50ms | Event processing |

</div>

### 8.2 🔧 Ölçeklenebilirlik Stratejisi

```yaml
# Horizontal Scaling
scaling:
  agents:
    replicas: 3
    load_balancer: "round_robin"
    
  kafka:
    partitions: 12
    replication_factor: 3
    
  redis:
    cluster_mode: true
    nodes: 6
    
  qdrant:
    shards: 4
    replicas: 2

# Vertical Scaling
resources:
  payments_agent:
    cpu: "1000m"
    memory: "512Mi"
    
  coordinator_agent:
    cpu: "2000m"
    memory: "1Gi"
    
  redis:
    cpu: "500m"
    memory: "256Mi"
    
  qdrant:
    cpu: "1000m"
    memory: "512Mi"
```

## 🔒 9. Güvenlik ve Uyumluluk

### 9.1 🛡️ Güvenlik Önlemleri

<div align="center">

| Güvenlik Katmanı | Açıklama | Implementasyon |
|------------------|----------|----------------|
| **🔐 API Authentication** | JWT token tabanlı kimlik doğrulama | Flask-JWT-Extended |
| **🔒 Data Encryption** | Hassas verilerin şifrelenmesi | AES-256 |
| **🛡️ Input Validation** | Giriş verilerinin doğrulanması | Pydantic models |
| **🚫 Rate Limiting** | API isteklerinin sınırlandırılması | Flask-Limiter |
| **📝 Audit Logging** | Tüm işlemlerin kaydedilmesi | Structured logging |

</div>

### 9.2 📋 Uyumluluk Gereksinimleri

```yaml
compliance:
  gdpr:
    data_retention: "7_years"
    right_to_forget: true
    data_portability: true
    
  pci_dss:
    card_data_encryption: true
    secure_transmission: true
    access_control: true
    
  sox:
    financial_reporting: true
    internal_controls: true
    audit_trail: true
```

## 🚀 10. Deployment ve DevOps

### 10.1 🐳 Container Orchestration

```yaml
# docker-compose.yml
version: '3.8'
services:
  langgraph-agents:
    build: ./langgraph-agents
    ports:
      - "5001:5000"
    environment:
      - HUGGINGFACE_API_KEY=${HUGGINGFACE_API_KEY}
      - REDIS_URL=redis://financial-redis:6379/0
      - QDRANT_HOST=financial-qdrant
      - KAFKA_BOOTSTRAP_SERVERS=financial-kafka:9092
    depends_on:
      - financial-redis
      - financial-qdrant
      - financial-kafka
      
  mcp-finance-tools:
    build: ./mcp-finance-tools
    ports:
      - "4000:4000"
      
  web-ui:
    build: ./web-ui
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:5001
```

### 10.2 🔄 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy Financial Agentic AI

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit
          
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Production
        run: |
          docker-compose -f docker-compose.prod.yml up -d
```

## 🆕 11. Son Güncellemeler ve Yeni Özellikler (2025-09-10)

### 11.1 ✨ UI/UX İyileştirmeleri

#### 🎯 Collapse Edilebilir JSON İçerikler
- **Özellik**: Tüm JSON içerikler başlangıçta kapalı
- **Avantaj**: Temiz görünüm, kullanıcı kontrolü
- **Implementasyon**: `collapsedEvents` state ile yönetim
- **Kullanım**: Header'a tıklayarak açma/kapama

#### 🔔 Toast Mesaj Sistemi
- **Özellik**: Modern kullanıcı bildirimleri
- **Süre**: 3 saniye otomatik kapanma
- **Animasyon**: Slide-in efekti
- **Pozisyon**: Sağ üst köşe, fixed

#### 🔒 Buton Disabled State Yönetimi
- **Özellik**: Çift tıklama koruması
- **Durum**: Loading state ile entegre
- **Görsel**: Gri renk, opacity 0.6
- **Kontrol**: Final rapor gelene kadar disabled

#### 💬 Özel Mesaj Modal Sistemi
- **Özellik**: Kullanıcı özel mesaj gönderebilir
- **Entegrasyon**: CoordinatorAgent'e yönlendirme
- **UI**: Modal popup ile temiz arayüz
- **Kontrol**: Ctrl+Enter ile hızlı gönderim

### 11.2 🔧 Teknik İyileştirmeler

#### 🧠 RAG Sistemi Aktifleştirme
- **Embedding Model**: `all-minilm` (384 dimension)
- **Vector DB**: Qdrant long-term memory
- **RAG Process**: Retrieval Augmented Generation
- **Memory Integration**: Redis + Qdrant çift katman

#### 🔄 Workflow Optimizasyonu
- **Fallback Modu**: Kapatıldı
- **Gerçek Workflow**: LangGraph tam aktif
- **Event Management**: Duplicate engelleme
- **Loading Control**: Final rapor bazlı yönetim

#### 📡 Event Streaming İyileştirmeleri
- **Server-Sent Events**: WebSocket yerine SSE
- **Event Types**: Tip bazlı filtreleme
- **Duplicate Prevention**: Unique key sistemi
- **Real-time Updates**: Anlık bildirimler

### 11.3 🎨 Kullanıcı Deneyimi Geliştirmeleri

#### 📱 Responsive Tasarım
- **Mobil Uyumluluk**: Tüm cihazlarda çalışır
- **Touch Friendly**: Dokunmatik optimizasyon
- **Modern UI**: Güncel tasarım trendleri
- **Accessibility**: Erişilebilirlik standartları

#### 🔄 Akış Kontrolü
- **State Management**: React hooks ile yönetim
- **Error Handling**: Hata durumu yönetimi
- **Loading States**: Kullanıcı bilgilendirmesi
- **Feedback Loop**: Geri bildirim sistemi

## 📚 12. Dokümantasyon ve Kaynaklar

### 12.1 📖 Teknik Dokümantasyon

- [API Documentation](http://localhost:5001/docs) - Swagger/OpenAPI
- [Agent Architecture](docs/architecture.md) - Detaylı mimari açıklaması
- [Memory Systems](docs/memory.md) - Redis ve Qdrant kullanımı
- [Event Flow](docs/events.md) - Kafka event akışı
- [Testing Guide](docs/testing.md) - Test stratejileri
- [UI Components](docs/ui-components.md) - React bileşenleri
- [RAG Implementation](docs/rag-system.md) - Retrieval Augmented Generation

### 12.2 🔗 Dış Kaynaklar

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Apache Kafka Guide](https://kafka.apache.org/documentation/)
- [Qdrant Vector Database](https://qdrant.tech/documentation/)
- [Redis Documentation](https://redis.io/documentation)
- [Hugging Face API](https://huggingface.co/docs/api-inference)
- [Next.js Documentation](https://nextjs.org/docs)
- [React Hooks Guide](https://reactjs.org/docs/hooks-intro.html)

---

<div align="center">

**📋 Bu PRD dokümantasyonu Financial Agentic AI projesinin teknik gereksinimlerini detaylı olarak tanımlar.**

**🔄 Güncelleme Tarihi:** 2025-09-10  
**📝 Versiyon:** 2.1  
**👨‍💻 Geliştirici:** epazar20  
**🆕 Son Güncellemeler:** UI/UX iyileştirmeleri, RAG sistemi, Toast bildirimler, Collapse UI

</div>
