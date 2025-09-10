"""
Finansal Agentic Proje API Endpoints
====================================

Bu modül Flask API endpoint'lerini yönetir ve HTTP isteklerini işler.
RESTful API tasarımı ile mikroservis mimarisini destekler.

Endpoint'ler:
- /simulate_deposit: Maaş yatışı simülasyonu
- /action: Kullanıcı eylemi işleme
- /stream: Server-Sent Events stream
- /health: Servis sağlık kontrolü
- /kafka/publish: Kafka event yayınlama
"""

import time
import json
import threading
from typing import Dict, Any, Optional
from queue import Queue
from flask import Flask, request, Response, jsonify

from config import config
from services import service_manager
from workflow import FinancialWorkflow, FinancialState


class EventBroadcaster:
    """
    Server-Sent Events broadcaster
    
    Tüm bağlı client'lara event'leri yayınlar.
    Thread-safe çalışır.
    """
    
    def __init__(self, publisher_queue: Queue):
        """
        Broadcaster'ı başlatır
        
        Args:
            publisher_queue: Event yayınlama kuyruğu
        """
        self.publisher_queue = publisher_queue
        self.clients = []
        self.clients_lock = threading.Lock()
        self._start_broadcaster()
    
    def _start_broadcaster(self):
        """Broadcaster thread'ini başlatır"""
        def broadcaster():
            """Event broadcaster loop'u"""
            while True:
                try:
                    item = self.publisher_queue.get()
                    if item is None:
                        break
                    
                    # SSE format'ında mesaj oluştur
                    msg = self._format_sse_message(
                        item.get("event", "message"),
                        item.get("data", {})
                    )
                    
                    # Tüm client'lara gönder
                    with self.clients_lock:
                        for q in self.clients:
                            q.put(msg)
                            
                except Exception as e:
                    print(f"Broadcaster hatası: {e}")
        
        # Broadcaster thread'ini başlat
        t = threading.Thread(target=broadcaster, daemon=True)
        t.start()
        print("✅ Event broadcaster başlatıldı")
    
    def _format_sse_message(self, event_name: str, data: Dict[str, Any]) -> str:
        """
        SSE format'ında mesaj oluşturur
        
        Args:
            event_name: Event adı
            data: Event verisi
            
        Returns:
            str: SSE format'ında mesaj
        """
        return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"
    
    def add_client(self, client_queue: Queue):
        """
        Yeni client ekler
        
        Args:
            client_queue: Client queue'su
        """
        with self.clients_lock:
            self.clients.append(client_queue)
    
    def remove_client(self, client_queue: Queue):
        """
        Client'ı kaldırır
        
        Args:
            client_queue: Kaldırılacak client queue'su
        """
        with self.clients_lock:
            try:
                self.clients.remove(client_queue)
            except ValueError:
                pass


class APIHandler:
    """
    Flask API endpoint'lerini yöneten ana sınıf
    
    Bu sınıf tüm HTTP endpoint'lerini handle eder ve
    business logic'i workflow'a yönlendirir.
    """
    
    def __init__(self, app: Flask, publisher_queue: Queue, workflow: FinancialWorkflow, broadcaster: EventBroadcaster):
        """
        API handler'ı başlatır
        
        Args:
            app: Flask uygulama instance'ı
            publisher_queue: Event yayınlama kuyruğu
            workflow: Finansal workflow instance'ı
            broadcaster: Event broadcaster instance'ı
        """
        self.app = app
        self.publisher_queue = publisher_queue
        self.workflow = workflow
        self.broadcaster = broadcaster
        self._register_routes()
    
    def _register_routes(self):
        """Tüm API route'larını kaydeder"""
        print("🔧 API route'ları kaydediliyor...")
        
        @self.app.route("/test", methods=["GET"])
        def test():
            """Test endpoint'i"""
            print("🧪 Test endpoint çağrıldı")
            return jsonify({"status": "ok", "message": "Test endpoint çalışıyor"}), 200
        
        @self.app.route("/simulate_deposit", methods=["POST"])
        def simulate_deposit():
            """
            Maaş yatışı simülasyonu endpoint'i
            
            Bu endpoint maaş yatışı event'ini tetikler ve
            LangGraph workflow'unu başlatır.
            
            Request Body:
                {
                    "payload": {
                        "userId": "user_123",
                        "amount": 25000
                    },
                    "meta": {
                        "correlationId": "corr-123" // opsiyonel
                    }
                }
            
            Returns:
                202: İşlem kabul edildi
                400: Geçersiz request
            """
            print("🎯 simulate_deposit route çağrıldı")
            return self._handle_simulate_deposit()
        
        @self.app.route("/action", methods=["POST"])
        def user_action():
            """
            Kullanıcı eylemi işleme endpoint'i
            
            Bu endpoint kullanıcının finansal öneriye verdiği
            yanıtı işler ve gerekli aksiyonları alır.
            
            Request Body:
                {
                    "userId": "user_123",
                    "proposalId": "prop_123",
                    "response": "accept", // veya "reject"
                    "correlationId": "corr-123"
                }
            
            Returns:
                202: Eylem kabul edildi
                400: Geçersiz request
            """
            return self._handle_user_action()
        
        @self.app.route("/chat_response", methods=["POST"])
        def chat_response():
            """
            Kullanıcının özel cevabını işleme endpoint'i
            
            Bu endpoint kullanıcının doğal dil ile verdiği
            cevabı analiz eder ve uygun agent'lara yönlendirir.
            
            Request Body:
                {
                    "userId": "user_123",
                    "response": "Sadece tahvil yatırımı yapmak istiyorum",
                    "proposal": { ... },
                    "correlationId": "corr-123",
                    "originalMessage": "Maaşın 25.000₺ olarak yattı..."
                }
            
            Returns:
                200: Cevap analiz edildi ve işlendi
                400: Geçersiz request
            """
            return self._handle_chat_response()
        
        @self.app.route("/stream")
        def stream():
            """
            Server-Sent Events stream endpoint'i
            
            Bu endpoint real-time event stream'i sağlar.
            Web UI'nin agent çıktılarını ve bildirimleri
            gerçek zamanlı olarak almasını sağlar.
            
            Returns:
                text/event-stream: SSE stream
            """
            return self._handle_stream()
        
        @self.app.route("/health", methods=["GET"])
        def health_check():
            """
            Servis sağlık kontrolü endpoint'i
            
            Tüm servislerin durumunu kontrol eder ve
            sistem sağlığını raporlar.
            
            Returns:
                200: Sağlık durumu JSON'u
            """
            return self._handle_health_check()
        
        @self.app.route("/kafka/publish", methods=["POST"])
        def kafka_publish():
            """
            Kafka event yayınlama endpoint'i
            
            Manuel olarak Kafka topic'lerine event
            yayınlamak için kullanılır.
            
            Request Body:
                {
                    "topic": "transactions.deposit",
                    "data": { ... }
                }
            
            Returns:
                200: Event yayınlandı
                400: Geçersiz request
                500: Kafka hatası
            """
            return self._handle_kafka_publish()
    
    def _handle_simulate_deposit(self) -> tuple:
        """
        Maaş yatışı simülasyonunu işler
        
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            print(f"🎯 _handle_simulate_deposit çağrıldı")
            
            # Request body'yi parse et
            print(f"📥 Request context: {request}")
            event = request.get_json()
            print(f"📥 Request body: {event}")
            
            if not event:
                print("❌ JSON payload bulunamadı")
                return jsonify({"error": "JSON payload gerekli"}), 400
            
            print(f"✅ JSON payload alındı: {event}")
            
            # Correlation ID'yi ayarla
            correlation_id = event.get("correlation_id") or event.get("meta", {}).get("correlationId") or f"corr-{int(time.time())}"
            print(f"🔗 Correlation ID: {correlation_id}")
            
            # Request'i workflow formatına çevir
            workflow_event = {
                "payload": {
                    "userId": event.get("user_id"),
                    "amount": event.get("amount")
                },
                "meta": {
                    "correlationId": correlation_id
                }
            }
            print(f"🔄 Workflow event oluşturuldu: {workflow_event}")
            
            # Workflow'u background thread'de başlat
            print(f"🧵 Background thread başlatılıyor...")
            thread = threading.Thread(
                target=self._process_deposit_workflow, 
                args=(workflow_event,)
            )
            thread.start()
            print(f"✅ Background thread başlatıldı: {thread.is_alive()}")
            
            return jsonify({
                "status": "accepted",
                "correlationId": correlation_id
            }), 202
            
        except Exception as e:
            print(f"Simulate deposit hatası: {e}")
            return jsonify({"error": "İşlem başlatılamadı"}), 500
    
    def _handle_user_action(self) -> tuple:
        """
        Kullanıcı eylemini işler
        
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            # Request body'yi parse et
            payload = request.get_json()
            if not payload:
                return jsonify({"error": "Payload gerekli"}), 400
            
            user_id = payload.get("userId")
            if not user_id:
                return jsonify({"error": "userId gerekli"}), 400
            
            # Redis'e kullanıcı eylemini kaydet
            service_manager.redis_service.set_user_action(user_id, payload)
            
            # Event'i yayınla
            self.publisher_queue.put({"event": "user-action", "data": payload})
            
            # Finalize işlemini background thread'de başlat
            threading.Thread(
                target=self._finalize_user_action, 
                args=(payload,)
            ).start()
            
            return jsonify({"status": "accepted"}), 202
            
        except Exception as e:
            print(f"User action hatası: {e}")
            return jsonify({"error": "Eylem işlenemedi"}), 500
    
    def _handle_chat_response(self) -> tuple:
        """
        Kullanıcının özel cevabını işler
        
        CoordinatorAgent'in LLM ile kullanıcı cevabını analiz edip
        uygun agent'lara yönlendirmesini sağlar.
        
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            # Request body'yi parse et
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON payload gerekli"}), 400
            
            user_response = data.get("response", "").strip()
            if not user_response:
                return jsonify({"error": "Boş cevap gönderilemez"}), 400
            
            print(f"💬 Chat cevabı alındı: {user_response}")
            
            original_proposal = data.get("proposal", {})
            original_message = data.get("originalMessage", "")
            correlation_id = data.get("correlationId", f"chat-{int(time.time())}")
            
            # CoordinatorAgent'e kullanıcı cevabını analiz ettir
            analysis_result = self._analyze_user_response_with_llm(
                user_response=user_response,
                original_proposal=original_proposal,
                original_message=original_message
            )
            
            print(f"🤖 LLM Analiz Sonucu: {analysis_result}")
            
            # Analiz sonucuna göre uygun agent'ı seç ve işle
            agent_action = self._execute_agent_based_on_analysis(
                analysis_result=analysis_result,
                user_response=user_response,
                original_proposal=original_proposal,
                correlation_id=correlation_id,
                user_id=data.get("userId")
            )
            
            # Sonuç event'ini yayınla
            self.publisher_queue.put({
                "event": "chat-analysis",
                "data": {
                    "userId": data.get("userId"),
                    "userResponse": user_response,
                    "analysis": analysis_result,
                    "agentAction": agent_action,
                    "correlationId": correlation_id,
                    "timestamp": time.time()
                }
            })
            
            return jsonify({
                "status": "success",
                "message": "Cevap analiz edildi ve işlendi",
                "analysis": analysis_result,
                "agentAction": agent_action,
                "correlationId": correlation_id
            }), 200
            
        except Exception as e:
            print(f"❌ Chat response endpoint hatası: {e}")
            return jsonify({"error": str(e)}), 500
    
    def _handle_stream(self) -> Response:
        """
        Server-Sent Events stream'i işler
        
        Returns:
            Response: SSE stream response
        """
        def generate():
            """SSE event generator"""
            # Yeni client queue'su oluştur
            q = Queue()
            self.broadcaster.add_client(q)
            
            try:
                while True:
                    # Queue'dan mesaj al
                    msg = q.get()
                    yield msg
            except GeneratorExit:
                # Client disconnect olduğunda queue'yu temizle
                self.broadcaster.remove_client(q)
        
        return Response(generate(), mimetype="text/event-stream")
    
    def _handle_health_check(self) -> tuple:
        """
        Servis sağlık kontrolünü işler
        
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            # Tüm servislerin durumunu kontrol et
            services_status = service_manager.get_health_status()
            
            # Workflow durumunu ekle
            services_status["workflow"] = self.workflow.is_ready()
            
            # Genel sağlık durumunu belirle
            all_healthy = all(services_status.values())
            status = "healthy" if all_healthy else "degraded"
            
            return jsonify({
                "status": status,
                "services": services_status
            }), 200
            
        except Exception as e:
            print(f"Health check hatası: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 500
    
    def _handle_kafka_publish(self) -> tuple:
        """
        Kafka event yayınlamayı işler
        
        Returns:
            tuple: (response_data, status_code)
        """
        try:
            # Request body'yi parse et
            payload = request.get_json()
            if not payload:
                return jsonify({"error": "Payload gerekli"}), 400
            
            topic = payload.get("topic")
            data = payload.get("data", {})
            
            if not topic:
                return jsonify({"error": "Topic gerekli"}), 400
            
            # Kafka'ya event yayınla
            success = service_manager.kafka_service.publish_event(topic, data)
            
            if success:
                return jsonify({
                    "status": "published",
                    "topic": topic
                }), 200
            else:
                return jsonify({
                    "error": "Kafka producer mevcut değil"
                }), 500
                
        except Exception as e:
            print(f"Kafka publish hatası: {e}")
            return jsonify({
                "error": "Event yayınlanamadı",
                "detail": str(e)
            }), 500
    
    def _process_deposit_workflow(self, event: Dict[str, Any]):
        """
        Maaş yatışı workflow'unu işler
        
        Args:
            event: Event verisi
        """
        try:
            print(f"🔄 Deposit workflow başlatılıyor: {event}")
            
            payload = event.get("payload", {})
            user_id = payload.get("userId")
            amount = payload.get("amount")
            correlation_id = event.get('meta', {}).get('correlationId', f"corr-{int(time.time())}")
            
            print(f"📊 Parsed data - User: {user_id}, Amount: {amount}, Correlation: {correlation_id}")
            
            if not user_id or not amount:
                print("❌ Geçersiz event: userId veya amount eksik")
                return
            
            # Workflow hazır değilse fallback kullan
            workflow_ready = self.workflow.is_ready()
            print(f"🔍 Workflow hazır mı: {workflow_ready}")
            
            if not workflow_ready:
                print("⚠️ Workflow hazır değil, fallback kullanılıyor")
                self._process_deposit_fallback(event)
                return
            
            # Initial state oluştur
            initial_state: FinancialState = {
                "userId": user_id,
                "amount": amount,
                "correlationId": correlation_id,
                "payments_output": {},
                "risk_output": {},
                "investment_output": {},
                "final_message": "",
                "user_action": ""
            }
            
            # Workflow'u çalıştır
            result = self.workflow.execute(initial_state)
            
            if result:
                print(f"✅ Workflow tamamlandı: {user_id} - {result.get('final_message', 'No message')}")
            else:
                print(f"❌ Workflow başarısız: {user_id}")
                
        except Exception as e:
            print(f"❌ Deposit workflow işleme hatası: {e}")
            # Fallback'e geç
            self._process_deposit_fallback(event)
    
    def _process_deposit_fallback(self, event: Dict[str, Any]):
        """
        Workflow fallback işlemi
        
        LangGraph workflow kullanılamadığında basit
        sıralı işlem yapar.
        
        Args:
            event: Event verisi
        """
        try:
            payload = event.get("payload", {})
            user_id = payload.get("userId")
            amount = payload.get("amount")
            correlation_id = event.get('meta', {}).get('correlationId', f"corr-{int(time.time())}")
            
            print(f"🔄 Fallback workflow başlatılıyor: {user_id}")
            
            # PaymentsAgent
            payments_req = {"userId": user_id, "since": None, "limit": 10}
            txs = service_manager.mcp_service.call_tool("transactions.query", payments_req)
            profile = service_manager.mcp_service.call_tool("userProfile.get", {"userId": user_id})
            auto_rate = profile.get("savedPreferences", {}).get("autoSavingsRate", 0.3)
            propose_amount = int(amount * auto_rate)
            
            payments_output = {
                "agent": "PaymentsAgent",
                "proposal": {
                    "action": "propose_transfer",
                    "amount": propose_amount,
                    "from": "CHK001",
                    "to": "SV001"
                }
            }
            self.publisher_queue.put({"event": "agent-output", "data": payments_output})
            
            # RiskAgent
            risk_req = {
                "userId": user_id,
                "tx": {"amount": propose_amount, "type": "internal_transfer"}
            }
            risk_res = service_manager.mcp_service.call_tool("risk.scoreTransaction", risk_req)
            risk_output = {"agent": "RiskAgent", "analysis": risk_res}
            self.publisher_queue.put({"event": "agent-output", "data": risk_output})
            
            # InvestmentAgent
            quotes = service_manager.mcp_service.call_tool("market.quotes", {
                "assetType": "bond",
                "tenor": "1Y"
            })
            invest_output = {"agent": "InvestmentAgent", "recommendation": quotes}
            self.publisher_queue.put({"event": "agent-output", "data": invest_output})
            
            # Coordinator
            prompt = f"User {user_id} deposit {amount}. PaymentsAgent: {payments_output['proposal']}. Risk: {risk_res}. Quotes: {quotes}."
            qres = service_manager.qdrant_service.search_similar(user_id, "deposit analysis", top_k=3)
            prompt += f" Past similar analysis: {qres}."
            
            llm_response = service_manager.huggingface_service.generate_response(
                "Sen bir finansal danışmansın.", prompt
            )
            final_message = llm_response.get("text", "Analiz tamamlandı.")
            
            notification = {
                "type": "final_proposal",
                "userId": user_id,
                "correlationId": correlation_id,
                "message": final_message,
                "proposal": payments_output['proposal']
            }
            self.publisher_queue.put({"event": "notification", "data": notification})
            
            print(f"✅ Fallback workflow tamamlandı: {user_id}")
            
        except Exception as e:
            print(f"❌ Fallback workflow hatası: {e}")
    
    def _finalize_user_action(self, payload: Dict[str, Any]):
        """
        Kullanıcı eylemini finalize eder
        
        Args:
            payload: Kullanıcı eylem verisi
        """
        try:
            user_id = payload.get("userId")
            proposal = payload.get("proposalId") or payload.get("proposal", {})
            correlation_id = payload.get("correlationId", f"corr-{int(time.time())}")
            
            # MCP savings.createTransfer çağrısı
            mcp_payload = {
                "userId": user_id,
                "fromAccount": "CHK001",
                "toSavingsId": "SV001",
                "amount": proposal.get("amount", 0)
            }
            result = service_manager.mcp_service.call_tool("savings.createTransfer", mcp_payload)
            
            # Execution result'ı yayınla
            execution_result = {
                "type": "execution_result",
                "userId": user_id,
                "correlationId": correlation_id,
                "result": result
            }
            self.publisher_queue.put({"event": "execution", "data": execution_result})
            
            # Kafka'ya gönder
            service_manager.kafka_service.publish_event(
                config.KAFKA_TOPICS["PAYMENTS_EXECUTED"],
                execution_result
            )
            
            print(f"✅ User action finalized: {user_id} - {result}")
            
        except Exception as e:
            print(f"❌ Finalize user action hatası: {e}")
    
    def _analyze_user_response_with_llm(self, user_response: str, original_proposal: dict, original_message: str) -> dict:
        """
        Kullanıcı cevabını LLM ile analiz eder
        
        CoordinatorAgent'in Hugging Face API'sini kullanarak kullanıcının
        doğal dil cevabını analiz eder ve hangi agent'a yönlendirileceğini belirler.
        
        Args:
            user_response: Kullanıcının verdiği cevap
            original_proposal: Orijinal öneri
            original_message: Orijinal mesaj
            
        Returns:
            dict: Analiz sonucu
        """
        try:
            # LLM prompt'u hazırla
            prompt = f"""
Sen bir finansal danışman koordinatörüsün. Kullanıcının verdiği cevabı analiz et ve hangi agent'a yönlendirileceğini belirle.

ORİJİNAL ÖNERİ:
{original_message}

KULLANICI CEVABI:
{user_response}

Mevcut agent'lar:
1. PaymentsAgent: Transfer miktarı değişiklikleri, tasarruf oranı ayarları
2. RiskAgent: Risk analizi, güvenlik kontrolleri
3. InvestmentAgent: Yatırım ürünü seçimi, portföy ayarları
4. GeneralAgent: Genel sorular, bilgi talepleri

Analiz sonucunu JSON formatında döndür:
{{
    "intent": "agent_name",
    "confidence": 0.0-1.0,
    "reasoning": "neden bu agent seçildi",
    "parameters": {{"key": "value"}},
    "action_required": true/false
}}
"""
            
            # Hugging Face API'yi çağır
            llm_response = service_manager.huggingface_service.generate_response(
                "Sen bir finansal danışman koordinatörüsün.", 
                prompt
            )
            
            # Response'u parse et
            response_text = llm_response.get("text", "{}")
            
            # JSON parse etmeye çalış
            try:
                import re
                # JSON kısmını bul
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    # Fallback analiz
                    analysis = self._fallback_response_analysis(user_response)
            except json.JSONDecodeError:
                # Fallback analiz
                analysis = self._fallback_response_analysis(user_response)
            
            print(f"🧠 LLM Analiz: {analysis}")
            return analysis
            
        except Exception as e:
            print(f"❌ LLM analiz hatası: {e}")
            # Fallback analiz
            return self._fallback_response_analysis(user_response)
    
    def _fallback_response_analysis(self, user_response: str) -> dict:
        """
        LLM kullanılamadığında basit keyword analizi
        
        Args:
            user_response: Kullanıcı cevabı
            
        Returns:
            dict: Basit analiz sonucu
        """
        response_lower = user_response.lower()
        
        # Keyword mapping
        if any(word in response_lower for word in ["tahvil", "bond", "faiz", "getiri"]):
            return {
                "intent": "InvestmentAgent",
                "confidence": 0.8,
                "reasoning": "Yatırım ürünü tercihi belirtildi",
                "parameters": {"preferred_investment": "bond"},
                "action_required": True
            }
        elif any(word in response_lower for word in ["hisse", "equity", "borsa", "sermaye"]):
            return {
                "intent": "InvestmentAgent", 
                "confidence": 0.8,
                "reasoning": "Hisse senedi tercihi belirtildi",
                "parameters": {"preferred_investment": "equity"},
                "action_required": True
            }
        elif any(word in response_lower for word in ["miktar", "tutar", "para", "₺", "tl"]):
            return {
                "intent": "PaymentsAgent",
                "confidence": 0.7,
                "reasoning": "Transfer miktarı değişikliği isteniyor",
                "parameters": {"amount_modification": True},
                "action_required": True
            }
        elif any(word in response_lower for word in ["risk", "güvenli", "emniyet"]):
            return {
                "intent": "RiskAgent",
                "confidence": 0.7,
                "reasoning": "Risk analizi talebi",
                "parameters": {"risk_analysis": True},
                "action_required": True
            }
        else:
            return {
                "intent": "GeneralAgent",
                "confidence": 0.5,
                "reasoning": "Genel soru veya bilgi talebi",
                "parameters": {"general_query": True},
                "action_required": False
            }
    
    def _execute_agent_based_on_analysis(self, analysis_result: dict, user_response: str, 
                                        original_proposal: dict, correlation_id: str, user_id: str) -> dict:
        """
        Analiz sonucuna göre uygun agent'ı çalıştırır
        
        Args:
            analysis_result: LLM analiz sonucu
            user_response: Kullanıcı cevabı
            original_proposal: Orijinal öneri
            correlation_id: Correlation ID
            user_id: Kullanıcı ID
            
        Returns:
            dict: Agent aksiyon sonucu
        """
        try:
            intent = analysis_result.get("intent", "GeneralAgent")
            parameters = analysis_result.get("parameters", {})
            
            print(f"🎯 Agent seçildi: {intent}")
            
            if intent == "PaymentsAgent":
                return self._execute_payments_agent(user_response, parameters, correlation_id, user_id)
            elif intent == "RiskAgent":
                return self._execute_risk_agent(user_response, parameters, correlation_id, user_id)
            elif intent == "InvestmentAgent":
                return self._execute_investment_agent(user_response, parameters, correlation_id, user_id)
            else:
                return self._execute_general_agent(user_response, parameters, correlation_id, user_id)
                
        except Exception as e:
            print(f"❌ Agent execution hatası: {e}")
            return {"error": str(e), "agent": "Unknown"}
    
    def _execute_payments_agent(self, user_response: str, parameters: dict, correlation_id: str, user_id: str) -> dict:
        """PaymentsAgent'i çalıştırır"""
        try:
            # Miktar değişikliği analizi
            amount_modification = parameters.get("amount_modification", False)
            
            if amount_modification:
                # Kullanıcı cevabından miktarı çıkarmaya çalış
                import re
                amount_match = re.search(r'(\d+)[\s]*₺?', user_response)
                if amount_match:
                    new_amount = int(amount_match.group(1))
                    
                    # Yeni MCP tool ile transfer güncelle
                    transfer_result = service_manager.mcp_service.call_tool("payments.modifyTransfer", {
                        "userId": user_id,
                        "newAmount": new_amount,
                        "originalAmount": 7500,  # Default amount
                        "transferId": f"tx-{int(time.time())}"
                    })
                    
                    # Event'i yayınla
                    self.publisher_queue.put({
                        "event": "agent-output",
                        "data": {
                            "agent": "PaymentsAgent",
                            "action": "transfer_modified",
                            "message": f"Transfer miktarı {new_amount}₺ olarak güncellendi.",
                            "result": transfer_result,
                            "correlationId": correlation_id
                        }
                    })
                    
                    return {
                        "agent": "PaymentsAgent",
                        "action": "amount_modified",
                        "new_amount": new_amount,
                        "result": transfer_result,
                        "message": f"Transfer miktarı {new_amount}₺ olarak güncellendi."
                    }
            
            return {
                "agent": "PaymentsAgent",
                "action": "no_change",
                "message": "PaymentsAgent analizi tamamlandı."
            }
            
        except Exception as e:
            print(f"❌ PaymentsAgent execution hatası: {e}")
            return {"error": str(e), "agent": "PaymentsAgent"}
    
    def _execute_risk_agent(self, user_response: str, parameters: dict, correlation_id: str, user_id: str) -> dict:
        """RiskAgent'i çalıştırır"""
        try:
            # Risk analizi talebi
            risk_analysis = parameters.get("risk_analysis", False)
            
            if risk_analysis:
                # Yeni MCP tool ile kapsamlı risk analizi
                risk_result = service_manager.mcp_service.call_tool("risk.performAnalysis", {
                    "userId": user_id,
                    "analysisType": "comprehensive"
                })
                
                # Event'i yayınla
                self.publisher_queue.put({
                    "event": "agent-output",
                    "data": {
                        "agent": "RiskAgent",
                        "action": "risk_analysis_completed",
                        "message": f"Risk analizi tamamlandı. Genel risk skoru: {risk_result.get('analysis', {}).get('overallScore', 'N/A')}",
                        "result": risk_result,
                        "correlationId": correlation_id
                    }
                })
                
                return {
                    "agent": "RiskAgent",
                    "action": "risk_analysis",
                    "result": risk_result,
                    "message": f"Risk analizi tamamlandı. Genel risk skoru: {risk_result.get('analysis', {}).get('overallScore', 'N/A')}"
                }
            
            return {
                "agent": "RiskAgent",
                "action": "no_change",
                "message": "RiskAgent analizi tamamlandı."
            }
            
        except Exception as e:
            print(f"❌ RiskAgent execution hatası: {e}")
            return {"error": str(e), "agent": "RiskAgent"}
    
    def _execute_investment_agent(self, user_response: str, parameters: dict, correlation_id: str, user_id: str) -> dict:
        """InvestmentAgent'i çalıştırır"""
        try:
            # Yatırım ürünü tercihi
            preferred_investment = parameters.get("preferred_investment", "bond")
            
            # Yeni MCP tool ile yatırım tercihini güncelle
            preference_result = service_manager.mcp_service.call_tool("investment.updatePreference", {
                "userId": user_id,
                "preferredInvestment": preferred_investment,
                "allocation": 100
            })
            
            # MCP tool ile piyasa verilerini al
            quotes_result = service_manager.mcp_service.call_tool("market.quotes", {
                "assetType": preferred_investment,
                "tenor": "1Y"
            })
            
            # Event'i yayınla
            self.publisher_queue.put({
                "event": "agent-output",
                "data": {
                    "agent": "InvestmentAgent",
                    "action": "investment_preference_updated",
                    "message": f"{preferred_investment} yatırım tercihi güncellendi.",
                    "result": {"preference": preference_result, "quotes": quotes_result},
                    "correlationId": correlation_id
                }
            })
            
            return {
                "agent": "InvestmentAgent",
                "action": "investment_preference",
                "preferred_investment": preferred_investment,
                "result": {"preference": preference_result, "quotes": quotes_result},
                "message": f"{preferred_investment} yatırım önerisi hazırlandı."
            }
            
        except Exception as e:
            print(f"❌ InvestmentAgent execution hatası: {e}")
            return {"error": str(e), "agent": "InvestmentAgent"}
    
    def _execute_general_agent(self, user_response: str, parameters: dict, correlation_id: str, user_id: str) -> dict:
        """GeneralAgent'i çalıştırır"""
        try:
            # Yeni MCP tool ile genel danışmanlık
            advice_result = service_manager.mcp_service.call_tool("general.getAdvice", {
                "userId": user_id,
                "question": user_response
            })
            
            # Event'i yayınla
            self.publisher_queue.put({
                "event": "agent-output",
                "data": {
                    "agent": "GeneralAgent",
                    "action": "advice_provided",
                    "message": advice_result.get("advice", "Genel danışmanlık hizmeti sağlandı."),
                    "result": advice_result,
                    "correlationId": correlation_id
                }
            })
            
            return {
                "agent": "GeneralAgent",
                "action": "general_response",
                "result": advice_result,
                "message": advice_result.get("advice", "Genel soru yanıtlandı.")
            }
            
        except Exception as e:
            print(f"❌ GeneralAgent execution hatası: {e}")
            return {"error": str(e), "agent": "GeneralAgent"}
