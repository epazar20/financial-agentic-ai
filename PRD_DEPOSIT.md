PRD: Maaş Yattı Senaryosu – Multi-Agent + Memory Mimarisi
1. Amaç
Kullanıcıya maaş yatması durumunda PaymentsAgent otomatik işlemleri başlatır, RiskAgent güvenlik ve uyum analizini yapar, yatırım fırsatları sunulur. Tüm ajanların çıktıları CoordinatorAgent tarafından Redis (short-term memory) ve Qdrant (long-term memory) ile zenginleştirilir, son mesaj kullanıcıya bildirim olarak sunulur.

2. Aktörler & Rolleri
2.1 Agents
* PaymentsAgent
    * MCP tool: transactions.query, payments.create, savings.createTransfer
    * Görev: maaş ödemesini algılama, bütçe planına göre öneri çıkarma, transfer hazırlama
* RiskAgent
    * MCP tool: risk.scoreTransaction, kyc.check
    * Görev: gelen maaşın kaynağını analiz etme, sahtekârlık / kara para riskini kontrol etme
* InvestmentAgent
    * MCP tool: market.quotes, orders.*
    * Görev: maaş sonrası uygun yatırım ürünleri önerisi sunma (risk durumuna göre)
* AdvisorAgent (Coordinator)
    * External LLM (API, ör. OpenAI GPT-4o)
    * Görev: tüm ajanların çıktısını toplar, Redis short-term memory + Qdrant long-term memory’den veriyi alır, kişiselleştirilmiş nihai mesaj oluşturur

2.2 Memory Katmanları
* Short-Term Memory (Redis)
    * Kullanıcı son konuşma / etkileşimleri (örn. “Evet” dedi mi, önceki 1 günlük onay-red geçmişi)
* Long-Term Memory (Qdrant Vector DB)
    * Benzer Kafka event türlerine verilen önceki analiz çıktıları
    * Nomic embed-text ile vektörleştirilmiş
    * RAG (retrieval augmented generation) için Coordinator’a sağlanır

2.3 Tool Calling
* Non-coordinator agentler (Payments, Risk, Investment) → Ollama + LLaMA (hafif tool-calling modeli)
* CoordinatorAgent (Advisor) → Büyük LLM API (ör. GPT-4o), RAG + memory ile enriched final message üretir

3. Teknoloji Yığını
* Backend Orkestrasyon:
    * Python LangGraph → agent workflow orchestration
    * Spring Boot REST API → dış dünya servisleri, Kafka event producer/consumer, MCP server integration
    * Kafka → event stream (ör. transaction.deposit)
* Memory
    * Redis → short-term memory
    * Qdrant → long-term memory (vector embeddings with nomic)
* LLM
    * Ollama (LLaMA tool-calling modeli) → agent tool çağrıları
    * External API (GPT-4o gibi) → Coordinator Agent
* UI / Frontend
    * WebSocket → real-time bildirim + prompt input (örn. kullanıcı “Evet” derse)

4. Örnek Senaryo – Maaş Yattı
Adım 1 – Event
* Kafka → transactions.deposit event (userId=123, amount=25000, ts=2025-09-09) yayınlanır
Adım 2 – PaymentsAgent
* Tool: transactions.query(userId=123, since=last30d)
* Tool: savings.createTransfer(userId=123, amount=7500) (henüz pending)
* Çıktı: “Maaşın 25.000₺ olarak hesabına geçti. Plan gereği 7.500₺ tasarrufa aktarılabilir.”
Adım 3 – RiskAgent
* Tool: risk.scoreTransaction(userId=123, tx=deposit)
* Örn. Sonuç: { score: 0.05, reason: "low risk" }
* Çıktı: “İşlem güvenli, düşük riskli.”
Adım 4 – InvestmentAgent
* RiskAgent sonucuna göre çalışır:
    * Low risk → daha agresif yatırım önerileri
    * High risk → daha temkinli ürünler
* Tool: market.quotes(assetType=bond, tenor=6m)
* Çıktı: “6 aylık tahvil faizi %28, BES fonu %22, hisse senedi endeksi yıllık %35”
Adım 5 – AdvisorAgent (Coordinator)
* Inputs:
    * PaymentsAgent → “25.000₺ maaş, 7.500₺ tasarruf önerisi”
    * RiskAgent → “low risk”
    * InvestmentAgent → “bond %28, equity %35”
    * Redis → son 24 saatteki kullanıcı cevapları (“Evet” → otomatik onay eğilimi)
    * Qdrant → önceki benzer maaş yatırımlarında kullanıcı hep tahvil seçmiş
* Output:
    * “Maaşın 25.000₺ olarak yattı ✅. Bütçene göre 7.500₺ tasarrufa aktarabilirim. Risk puanın düşük görünüyor, önceki tercihlerin de tahvil yönünde olmuş. Bu kez tahvile %28 faizle yatırmak ister misin?”
Adım 6 – Kullanıcı Etkileşimi
* UI → WebSocket bildirimi gelir
* Kullanıcı prompt: “Evet”
* PaymentsAgent → savings.createTransfer finalize edilir
* Kafka → payments.executed event üretilir

5. Kafka Topics (Event-Driven Yapı)
* transactions.deposit → yeni maaş yatışı
* payments.pending → önerilen otomatik transfer
* risk.analysis → riskAgent çıktı
* investments.proposal → yatırım önerisi
* advisor.finalMessage → kullanıcıya sunulan nihai mesaj
* payments.executed → onay sonrası işlem sonucu

6. UI Akışı
* Bildirim kartı:
    * “Maaşın 25.000₺ yatırıldı.”
    * “Tasarruf: 7.500₺ aktarabilirim. Yatırım önerisi: Tahvil %28. Onaylıyor musun?”
* Prompt alanı → kullanıcı cevap yazar (Evet/Hayır vs.)
* WebSocket → backend → Kafka → agent workflow

👉 Böylece senaryoda çoklu agent, short & long memory, RAG, LLM katmanı farkı (tool-calling vs external LLM), Kafka event-driven mimarisi ve UI bildirim-prompt entegrasyonu birlikte çalışıyor.