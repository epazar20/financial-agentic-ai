#!/usr/bin/env python3
"""
Basit Test Sunucusu - Maaş Yatış Senaryosu Testi
===============================================

Bu sunucu PRD_DEPOSIT.md senaryosunu test etmek için
basit bir Flask API ve SSE stream sağlar.
"""

import json
import time
import threading
from queue import Queue
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Event broadcasting için queue
publisher_queue = Queue()
clients = []
clients_lock = threading.Lock()

def broadcaster():
    """Event broadcaster thread'i"""
    while True:
        try:
            item = publisher_queue.get()
            if item is None:
                break
            
            # SSE format'ında mesaj oluştur
            msg = f"event: {item.get('event', 'message')}\ndata: {json.dumps(item.get('data', {}))}\n\n"
            
            # Tüm client'lara gönder
            with clients_lock:
                for q in clients:
                    q.put(msg)
                    
        except Exception as e:
            print(f"Broadcaster hatası: {e}")

# Broadcaster thread'ini başlat
t = threading.Thread(target=broadcaster, daemon=True)
t.start()

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint'i"""
    return jsonify({"status": "ok", "message": "Test sunucusu çalışıyor"}), 200

@app.route('/simulate_deposit', methods=['POST'])
def simulate_deposit():
    """
    Maaş yatışı simülasyonu endpoint'i
    PRD_DEPOSIT.md senaryosuna göre workflow'u simüle eder
    """
    try:
        print("🎯 Maaş yatış simülasyonu başlatılıyor...")
        
        # Request body'yi parse et
        event = request.get_json()
        if not event:
            return jsonify({"error": "JSON payload gerekli"}), 400
        
        user_id = event.get("user_id", "test_user")
        amount = event.get("amount", 25000)
        correlation_id = event.get("correlation_id", f"corr-{int(time.time())}")
        
        print(f"📊 Maaş yatışı: {amount}₺ - Kullanıcı: {user_id}")
        
        # Background thread'de workflow'u başlat
        threading.Thread(
            target=process_deposit_workflow,
            args=(user_id, amount, correlation_id)
        ).start()
        
        return jsonify({
            "status": "accepted",
            "correlationId": correlation_id,
            "message": f"Maaş yatışı {amount}₺ olarak işleme alındı"
        }), 202
        
    except Exception as e:
        print(f"❌ Simulate deposit hatası: {e}")
        return jsonify({"error": "İşlem başlatılamadı"}), 500

@app.route('/kafka/publish', methods=['POST'])
def kafka_publish():
    """
    Kafka event yayınlama endpoint'i
    Manuel olarak Kafka topic'lerine event yayınlar
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Payload gerekli"}), 400
        
        topic = payload.get("topic")
        data = payload.get("data", {})
        
        if not topic:
            return jsonify({"error": "Topic gerekli"}), 400
        
        print(f"📨 Kafka event yayınlanıyor: {topic}")
        
        # Event'i SSE stream'e gönder
        publisher_queue.put({
            "event": "kafka-event",
            "data": {
                "topic": topic,
                "data": data,
                "timestamp": time.time()
            }
        })
        
        return jsonify({
            "status": "published",
            "topic": topic,
            "message": f"Event {topic} topic'ine yayınlandı"
        }), 200
        
    except Exception as e:
        print(f"❌ Kafka publish hatası: {e}")
        return jsonify({"error": "Event yayınlanamadı"}), 500

@app.route('/action', methods=['POST'])
def user_action():
    """
    Kullanıcı eylemi işleme endpoint'i
    Kullanıcının finansal öneriye verdiği yanıtı işler
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Payload gerekli"}), 400
        
        user_id = payload.get("userId", "test_user")
        response = payload.get("response", "approve")
        
        print(f"👤 Kullanıcı eylemi: {user_id} - {response}")
        
        # Event'i yayınla
        publisher_queue.put({
            "event": "user-action",
            "data": {
                "userId": user_id,
                "response": response,
                "timestamp": time.time()
            }
        })
        
        # Finalize işlemini background thread'de başlat
        threading.Thread(
            target=finalize_user_action,
            args=(payload,)
        ).start()
        
        return jsonify({"status": "accepted"}), 202
        
    except Exception as e:
        print(f"❌ User action hatası: {e}")
        return jsonify({"error": "Eylem işlenemedi"}), 500

@app.route('/stream')
def stream():
    """
    Server-Sent Events stream endpoint'i
    Real-time event stream sağlar
    """
    def generate():
        """SSE event generator"""
        # Yeni client queue'su oluştur
        q = Queue()
        with clients_lock:
            clients.append(q)
        
        try:
            while True:
                # Queue'dan mesaj al
                msg = q.get()
                yield msg
        except GeneratorExit:
            # Client disconnect olduğunda queue'yu temizle
            with clients_lock:
                try:
                    clients.remove(q)
                except ValueError:
                    pass
    
    return Response(generate(), mimetype="text/event-stream")

@app.route('/health', methods=['GET'])
def health_check():
    """Servis sağlık kontrolü endpoint'i"""
    return jsonify({
        "status": "healthy",
        "services": {
            "test_server": True,
            "mcp_finance_tools": True,  # Mock
            "redis": True,  # Mock
            "qdrant": True,  # Mock
            "kafka": True  # Mock
        }
    }), 200

def process_deposit_workflow(user_id: str, amount: int, correlation_id: str):
    """
    Maaş yatışı workflow'unu işler
    PRD_DEPOSIT.md senaryosuna göre agent'ları simüle eder
    """
    try:
        print(f"🔄 Deposit workflow başlatılıyor: {user_id} - {amount}₺")
        
        # Adım 1: PaymentsAgent
        print("🔄 PaymentsAgent çalışıyor...")
        auto_rate = 0.3  # %30 otomatik tasarruf
        propose_amount = int(amount * auto_rate)
        
        payments_output = {
            "agent": "PaymentsAgent",
            "proposal": {
                "action": "propose_transfer",
                "amount": propose_amount,
                "from": "CHK001",
                "to": "SV001"
            },
            "message": f"Maaşın {amount:,}₺ olarak hesabına geçti. Plan gereği {propose_amount:,}₺ tasarrufa aktarılabilir."
        }
        
        publisher_queue.put({"event": "agent-output", "data": payments_output})
        time.sleep(1)  # Simülasyon gecikmesi
        
        # Adım 2: RiskAgent
        print("🔄 RiskAgent çalışıyor...")
        risk_score = 0.05  # Düşük risk
        
        risk_output = {
            "agent": "RiskAgent",
            "analysis": {"score": risk_score, "reason": "low risk"},
            "message": f"İşlem güvenli, {'düşük' if risk_score < 0.5 else 'yüksek'} riskli."
        }
        
        publisher_queue.put({"event": "agent-output", "data": risk_output})
        time.sleep(1)
        
        # Adım 3: InvestmentAgent
        print("🔄 InvestmentAgent çalışıyor...")
        
        # Risk bazlı yatırım stratejisi
        if risk_score < 0.3:  # Düşük risk - agresif
            quotes = {
                "bond": {"rate": 0.28, "instrument": "6 aylık tahvil"},
                "equity": {"rate": 0.35, "instrument": "Hisse senedi endeksi"},
                "fund": {"rate": 0.22, "instrument": "BES fonu"}
            }
        else:  # Yüksek risk - muhafazakar
            quotes = {
                "bond": {"rate": 0.28, "instrument": "6 aylık tahvil"},
                "savings": {"rate": 0.15, "instrument": "Tasarruf hesabı"}
            }
        
        investment_output = {
            "agent": "InvestmentAgent",
            "recommendation": quotes,
            "message": f"Risk durumuna göre yatırım önerileri: {', '.join(quotes.keys())}"
        }
        
        publisher_queue.put({"event": "agent-output", "data": investment_output})
        time.sleep(1)
        
        # Adım 4: CoordinatorAgent
        print("🔄 CoordinatorAgent çalışıyor...")
        
        # Hafıza simülasyonu
        short_term_memory = "Son kullanıcı eylemi: Evet (otomatik onay eğilimi)"
        long_term_memory = "Geçmiş benzer analizler:\n- Önceki maaş yatırımlarında kullanıcı hep tahvil seçmiş\n- Risk profili düşük, agresif yatırım tercih ediyor"
        
        # Final mesaj oluştur
        final_message = f"""Maaşın {amount:,}₺ olarak yattı ✅. 

Bütçene göre {propose_amount:,}₺ tasarrufa aktarabilirim. Risk puanın düşük görünüyor ({risk_score}), önceki tercihlerin de tahvil yönünde olmuş. 

Bu kez tahvile %28 faizle yatırmak ister misin?"""
        
        # Final notification oluştur
        notification = {
            "type": "final_proposal",
            "userId": user_id,
            "correlationId": correlation_id,
            "message": final_message,
            "proposal": payments_output["proposal"],
            "timestamp": time.time()
        }
        
        publisher_queue.put({"event": "notification", "data": notification})
        
        print(f"✅ Workflow tamamlandı: {user_id}")
        
    except Exception as e:
        print(f"❌ Deposit workflow hatası: {e}")

def finalize_user_action(payload: dict):
    """
    Kullanıcı eylemini finalize eder
    """
    try:
        user_id = payload.get("userId", "test_user")
        response = payload.get("response", "approve")
        
        print(f"🔄 User action finalize ediliyor: {user_id} - {response}")
        
        # MCP savings.createTransfer simülasyonu
        result = {
            "status": "ok",
            "txId": f"tx-{int(time.time())}",
            "executedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": payload.get("proposal", {}).get("amount", 0)
        }
        
        # Execution result'ı yayınla
        execution_result = {
            "type": "execution_result",
            "userId": user_id,
            "correlationId": payload.get("correlationId", f"corr-{int(time.time())}"),
            "result": result,
            "timestamp": time.time()
        }
        
        publisher_queue.put({"event": "execution", "data": execution_result})
        
        print(f"✅ User action finalized: {user_id} - {result}")
        
    except Exception as e:
        print(f"❌ Finalize user action hatası: {e}")

if __name__ == "__main__":
    print("🚀 Test sunucusu başlatılıyor...")
    print("📡 Endpoint'ler:")
    print("  - GET  /test")
    print("  - POST /simulate_deposit")
    print("  - POST /kafka/publish")
    print("  - POST /action")
    print("  - GET  /stream")
    print("  - GET  /health")
    print("🌐 Sunucu: http://localhost:5001")
    
    app.run(host="0.0.0.0", port=5001, debug=True)
