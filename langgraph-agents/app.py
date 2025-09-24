"""
Finansal Agentic Proje Ana Uygulama
===================================

Bu dosya tüm bileşenleri bir araya getirerek ana uygulamayı oluşturur.
Modüler mimari ile servisleri, workflow'u ve API'yi koordine eder.

Mimari:
- Config: Konfigürasyon yönetimi
- Services: Dış servis bağlantıları
- Workflow: LangGraph multi-agent workflow
- API: Flask REST API endpoints
- Kafka Consumer: Event streaming
"""

import threading
import time
from queue import Queue
from flask import Flask
from flask_cors import CORS

from config import config
from services import service_manager
from workflow import FinancialWorkflow
from api import APIHandler, EventBroadcaster


class FinancialAgenticApp:
    """
    Finansal Agentic Proje ana uygulama sınıfı
    
    Bu sınıf tüm bileşenleri koordine eder ve uygulamayı başlatır.
    Singleton pattern kullanarak tek instance garantisi sağlar.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(FinancialAgenticApp, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Ana uygulamayı başlatır"""
        print("🎯 FinancialAgenticApp __init__ çağrıldı")
        if not FinancialAgenticApp._initialized:
            print("🔄 İlk kez başlatılıyor, _initialize_app çağrılıyor")
            self._initialize_app()
            FinancialAgenticApp._initialized = True
        else:
            print("ℹ️ Zaten başlatılmış")
    
    def _initialize_app(self):
        """Uygulama bileşenlerini başlatır"""
        print("🚀 Finansal Agentic Proje başlatılıyor...")
        
        # Konfigürasyonu yazdır
        config.print_config()
        
        # Flask uygulamasını oluştur
        self.app = Flask(__name__)
        
        # CORS desteği ekle (web-ui erişimi için)
        cors_origins = config.CORS_ORIGINS.split(',')
        CORS(self.app, origins=cors_origins, 
             allow_headers=['Content-Type', 'Authorization'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
        
        # Event broadcasting için queue oluştur
        self.publisher_queue = Queue()
        
        # Event broadcaster'ı başlat
        self.broadcaster = EventBroadcaster(self.publisher_queue)
        self.broadcaster._start_broadcaster()
        
        # Finansal workflow'u oluştur
        print("🔧 Finansal Workflow başlatılıyor...")
        self.workflow = FinancialWorkflow(self.publisher_queue)
        print("✅ Finansal Workflow başlatıldı")
        
        # API handler'ı başlat
        print("🔧 API Handler başlatılıyor...")
        self.api_handler = APIHandler(self.app, self.publisher_queue, self.workflow, self.broadcaster)
        print("✅ API Handler başlatıldı")
        
        # Kafka consumer'ı başlat
        self._start_kafka_consumer()
        
        print("✅ Finansal Agentic Proje başarıyla başlatıldı")
    
    def _start_kafka_consumer(self):
        """Kafka consumer thread'ini başlatır"""
        def kafka_consumer():
            """
            Kafka consumer loop'u
            
            transactions.deposit topic'ini dinler ve
            gelen event'leri workflow'a yönlendirir.
            """
            try:
                consumer = service_manager.kafka_service.create_consumer(
                    config.KAFKA_TOPICS["TRANSACTIONS_DEPOSIT"],
                    "financial_agents_group"
                )
                
                if not consumer:
                    print("❌ Kafka consumer oluşturulamadı")
                    return
                
                print("✅ Kafka consumer başlatıldı")
                
                for message in consumer:
                    try:
                        event_data = message.value
                        print(f"📨 Kafka event alındı: {event_data}")
                        
                        # Workflow'u background thread'de başlat
                        threading.Thread(
                            target=self._handle_kafka_event,
                            args=(event_data,)
                        ).start()
                        
                    except Exception as e:
                        print(f"❌ Kafka mesaj işleme hatası: {e}")
                        
            except Exception as e:
                print(f"❌ Kafka consumer hatası: {e}")
        
        # Kafka consumer thread'ini başlat
        kafka_thread = threading.Thread(target=kafka_consumer, daemon=True)
        kafka_thread.start()
    
    def _handle_kafka_event(self, event_data: dict):
        """
        Kafka event'ini işler
        
        Args:
            event_data: Kafka'dan gelen event verisi
        """
        try:
            payload = event_data.get("payload", {})
            user_id = payload.get("userId")
            amount = payload.get("amount")
            correlation_id = event_data.get('meta', {}).get('correlationId', f"corr-{int(time.time())}")
            
            if not user_id or not amount:
                print("❌ Geçersiz Kafka event: userId veya amount eksik")
                return
            
            # Workflow hazır değilse fallback kullan
            if not self.workflow.is_ready():
                print("⚠️ Workflow hazır değil, fallback kullanılıyor")
                self.api_handler._process_deposit_fallback(event_data)
                return
            
            # Initial state oluştur
            initial_state = {
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
                print(f"✅ Kafka workflow tamamlandı: {user_id}")
            else:
                print(f"❌ Kafka workflow başarısız: {user_id}")
                
        except Exception as e:
            print(f"❌ Kafka event işleme hatası: {e}")
            # Fallback'e geç
            self.api_handler._process_deposit_fallback(event_data)
    
    def run(self):
        """Flask uygulamasını çalıştırır"""
        print(f"🌐 Flask uygulaması başlatılıyor: {config.FLASK_HOST}:{config.FLASK_PORT}")
        
        self.app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG
        )


def main():
    """
    Ana uygulama entry point'i
    
    Bu fonksiyon uygulamayı başlatır ve tüm bileşenleri
    koordine eder.
    """
    try:
        # Ana uygulamayı oluştur
        app = FinancialAgenticApp()
        
        # Uygulamayı çalıştır
        app.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Uygulama kullanıcı tarafından durduruldu")
    except Exception as e:
        print(f"❌ Uygulama hatası: {e}")
        raise


if __name__ == "__main__":
    main()
