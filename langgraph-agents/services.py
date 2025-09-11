"""
Finansal Agentic Proje Servis Bağlantıları
==========================================

Bu modül tüm dış servislerle (Redis, Qdrant, Kafka, Ollama, Hugging Face) 
bağlantıları yönetir ve servis durumlarını kontrol eder.

Servisler:
- RedisService: Kısa vadeli hafıza yönetimi
- QdrantService: Uzun vadeli vektör hafızası
- KafkaService: Event streaming
- OllamaService: Yerel LLM modelleri
- HuggingFaceService: Büyük LLM API'si
- MCPService: Finansal araçlar
"""

import json
import time
import requests
import redis
from typing import Optional, Dict, Any, List
from kafka import KafkaConsumer, KafkaProducer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_ollama import OllamaLLM, OllamaEmbeddings

from config import config


class ServiceManager:
    """
    Tüm servis bağlantılarını yöneten ana sınıf
    
    Bu sınıf singleton pattern kullanarak tüm servislerin
    tek bir instance'ını yönetir ve bağlantı durumlarını kontrol eder.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(ServiceManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Servis bağlantılarını başlatır"""
        if not ServiceManager._initialized:
            self._initialize_services()
            ServiceManager._initialized = True
    
    def _initialize_services(self):
        """Tüm servisleri başlatır"""
        print("Servis bağlantıları başlatılıyor...")
        
        # Servis instance'larını oluştur
        self.redis_service = RedisService()
        self.qdrant_service = QdrantService()
        self.kafka_service = KafkaService()
        self.ollama_service = OllamaService()
        self.huggingface_service = HuggingFaceService()
        self.mcp_service = MCPService()
        
        print("Tüm servis bağlantıları tamamlandı")
    
    def get_health_status(self) -> Dict[str, bool]:
        """
        Tüm servislerin sağlık durumunu kontrol eder
        
        Returns:
            Dict[str, bool]: Servis adı ve durumu
        """
        return {
            "redis": self.redis_service.is_healthy(),
            "qdrant": self.qdrant_service.is_healthy(),
            "kafka": self.kafka_service.is_healthy(),
            "ollama": self.ollama_service.is_healthy(),
            "huggingface": self.huggingface_service.is_healthy(),
            "workflow": True  # Workflow her zaman True (runtime'da kontrol edilir)
        }


class RedisService:
    """
    Redis servisi - Kısa vadeli hafıza yönetimi
    
    Kullanıcı eylemleri, geçici veriler ve session bilgilerini
    Redis'te saklar. Hızlı erişim için optimize edilmiştir.
    """
    
    def __init__(self):
        """Redis bağlantısını başlatır"""
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Redis'e bağlanır"""
        try:
            self.client = redis.from_url(config.REDIS_URL)
            # Bağlantıyı test et
            self.client.ping()
            print("✅ Redis bağlantısı başarılı")
        except Exception as e:
            print(f"❌ Redis bağlantı hatası: {e}")
            self.client = None
    
    def is_healthy(self) -> bool:
        """Redis servisinin sağlık durumunu kontrol eder"""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def set_user_action(self, user_id: str, action_data: Dict[str, Any]) -> bool:
        """
        Kullanıcının son eylemini Redis'te saklar
        
        Args:
            user_id: Kullanıcı ID'si
            action_data: Eylem verisi
            
        Returns:
            bool: Başarılı ise True
        """
        if not self.client:
            return False
        
        try:
            key = config.REDIS_KEYS["USER_LAST_ACTION"].format(user_id=user_id)
            self.client.set(
                key, 
                json.dumps(action_data), 
                ex=config.REDIS_TTL["USER_ACTION"]
            )
            return True
        except Exception as e:
            print(f"Redis set_user_action hatası: {e}")
            return False
    
    def get_user_action(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Kullanıcının son eylemini Redis'ten alır
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Dict[str, Any]: Eylem verisi veya None
        """
        if not self.client:
            return None
        
        try:
            key = config.REDIS_KEYS["USER_LAST_ACTION"].format(user_id=user_id)
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Redis get_user_action hatası: {e}")
            return None
    
    def push_user_event(self, user_id: str, event_data: Dict[str, Any]) -> bool:
        """
        Kullanıcı etkinliğini Redis listesine ekler
        
        Args:
            user_id: Kullanıcı ID'si
            event_data: Etkinlik verisi
            
        Returns:
            bool: Başarılı ise True
        """
        if not self.client:
            return False
        
        try:
            key = config.REDIS_KEYS["USER_LAST_EVENTS"].format(user_id=user_id)
            self.client.lpush(key, json.dumps(event_data))
            self.client.expire(key, config.REDIS_TTL["USER_EVENTS"])
            return True
        except Exception as e:
            print(f"Redis push_user_event hatası: {e}")
            return False


class QdrantService:
    """
    Qdrant servisi - Uzun vadeli vektör hafızası
    
    Finansal analizlerin vektör olarak saklanması ve
    benzerlik araması için kullanılır.
    """
    
    def __init__(self):
        """Qdrant bağlantısını başlatır"""
        self.client: Optional[QdrantClient] = None
        self._connect()
    
    def _connect(self):
        """Qdrant'a bağlanır ve collection oluşturur"""
        try:
            qdrant_config = config.get_qdrant_config()
            self.client = QdrantClient(
                host=qdrant_config["host"], 
                port=qdrant_config["port"]
            )
            
            # Collection'ı kontrol et ve oluştur
            self._ensure_collection_exists()
            print("✅ Qdrant bağlantısı başarılı")
        except Exception as e:
            print(f"❌ Qdrant bağlantı hatası: {e}")
            self.client = None
    
    def _ensure_collection_exists(self):
        """Financial memory collection'ının varlığını garanti eder"""
        if not self.client:
            return
        
        try:
            # Collection'ı kontrol et
            self.client.get_collection(config.FINANCIAL_MEMORY_COLLECTION)
        except:
            # Collection yoksa oluştur
            self.client.create_collection(
                collection_name=config.FINANCIAL_MEMORY_COLLECTION,
                vectors_config=VectorParams(
                    size=config.VECTOR_SIZE, 
                    distance=Distance.COSINE
                )
            )
            print(f"✅ {config.FINANCIAL_MEMORY_COLLECTION} collection'ı oluşturuldu")
    
    def is_healthy(self) -> bool:
        """Qdrant servisinin sağlık durumunu kontrol eder"""
        if not self.client:
            return False
        try:
            # Basit bir health check
            collections = self.client.get_collections()
            return True
        except:
            return False
    
    def store_memory(self, user_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        İçeriği Qdrant'ta vektör olarak saklar
        
        Args:
            user_id: Kullanıcı ID'si
            content: Saklanacak içerik
            metadata: Ek metadata
            
        Returns:
            bool: Başarılı ise True
        """
        if not self.client:
            return False
        
        try:
            # Embedding oluştur (Ollama servisinden)
            embedding = self._get_embedding(content)
            if not embedding:
                return False
            
            # Point oluştur
            point = PointStruct(
                id=int(time.time() * 1000),  # Timestamp as ID
                vector=embedding,
                payload={
                    "userId": user_id,
                    "content": content,
                    "timestamp": int(time.time()),
                    **(metadata or {})
                }
            )
            
            # Point'i sakla
            self.client.upsert(
                collection_name=config.FINANCIAL_MEMORY_COLLECTION,
                points=[point]
            )
            return True
        except Exception as e:
            print(f"Qdrant store_memory hatası: {e}")
            return False
    
    def search_similar(self, user_id: str, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Benzer içerikleri arar
        
        Args:
            user_id: Kullanıcı ID'si
            query_text: Arama metni
            top_k: Döndürülecek sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Benzer içerikler
        """
        if not self.client:
            return []
        
        try:
            # Query embedding oluştur
            query_embedding = self._get_embedding(query_text)
            if not query_embedding:
                return []
            
            # Benzerlik araması yap
            search_result = self.client.search(
                collection_name=config.FINANCIAL_MEMORY_COLLECTION,
                query_vector=query_embedding,
                limit=top_k,
                query_filter={"must": [{"key": "userId", "match": {"value": user_id}}]}
            )
            
            return [{"payload": hit.payload, "score": hit.score} for hit in search_result]
        except Exception as e:
            print(f"Qdrant search_similar hatası: {e}")
            return []
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Metin için embedding oluşturur
        
        Args:
            text: Embedding oluşturulacak metin
            
        Returns:
            List[float]: Embedding vektörü
        """
        # Ollama servisinden embedding al
        ollama_service = OllamaService()
        return ollama_service.get_embedding(text)


class KafkaService:
    """
    Kafka servisi - Event streaming
    
    Mikroservisler arası asenkron iletişim için
    Kafka producer ve consumer yönetimi.
    """
    
    def __init__(self):
        """Kafka bağlantısını başlatır"""
        self.producer: Optional[KafkaProducer] = None
        self._connect_producer()
    
    def _connect_producer(self):
        """Kafka producer'ı başlatır"""
        try:
            kafka_config = config.get_kafka_config()
            self.producer = KafkaProducer(
                bootstrap_servers=kafka_config["bootstrap_servers"],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print("✅ Kafka producer bağlantısı başarılı")
        except Exception as e:
            print(f"❌ Kafka producer bağlantı hatası: {e}")
            self.producer = None
    
    def is_healthy(self) -> bool:
        """Kafka servisinin sağlık durumunu kontrol eder"""
        return self.producer is not None
    
    def publish_event(self, topic: str, data: Dict[str, Any]) -> bool:
        """
        Kafka topic'ine event yayınlar
        
        Args:
            topic: Topic adı
            data: Yayınlanacak veri
            
        Returns:
            bool: Başarılı ise True
        """
        if not self.producer:
            return False
        
        try:
            self.producer.send(topic, data)
            self.producer.flush()
            return True
        except Exception as e:
            print(f"Kafka publish_event hatası: {e}")
            return False
    
    def create_consumer(self, topic: str, group_id: str) -> Optional[KafkaConsumer]:
        """
        Kafka consumer oluşturur
        
        Args:
            topic: Dinlenecek topic
            group_id: Consumer group ID
            
        Returns:
            KafkaConsumer: Consumer instance
        """
        try:
            kafka_config = config.get_kafka_config()
            return KafkaConsumer(
                topic,
                bootstrap_servers=kafka_config["bootstrap_servers"],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id=group_id
            )
        except Exception as e:
            print(f"Kafka consumer oluşturma hatası: {e}")
            return None


class OllamaService:
    """
    Ollama servisi - Yerel LLM modelleri
    
    Küçük LLM modelleri ve embedding işlemleri için
    yerel Ollama servisi ile iletişim.
    """
    
    def __init__(self):
        """Ollama bağlantısını başlatır"""
        self.llm: Optional[OllamaLLM] = None
        self.embeddings: Optional[OllamaEmbeddings] = None
        self._connect()
    
    def _connect(self):
        """Ollama modellerini başlatır"""
        try:
            self.llm = OllamaLLM(model=config.OLLAMA_MODELS["LLM_MODEL"])
            self.embeddings = OllamaEmbeddings(model=config.OLLAMA_MODELS["EMBEDDING_MODEL"])
            print("✅ Ollama bağlantısı başarılı")
        except Exception as e:
            print(f"❌ Ollama bağlantı hatası: {e}")
            self.llm = None
            self.embeddings = None
    
    def is_healthy(self) -> bool:
        """Ollama servisinin sağlık durumunu kontrol eder"""
        return self.llm is not None and self.embeddings is not None
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Metin için embedding oluşturur
        
        Args:
            text: Embedding oluşturulacak metin
            
        Returns:
            List[float]: Embedding vektörü
        """
        try:
            # Direct Ollama API call için
            import requests
            
            response = requests.post(
                f"{config.OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": config.OLLAMA_MODELS["EMBEDDING_MODEL"],
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("embedding")
            else:
                print(f"Ollama embedding API hatası: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Ollama embedding hatası: {e}")
            return None
    
    def generate_text(self, prompt: str) -> Optional[str]:
        """
        LLM ile metin üretir
        
        Args:
            prompt: LLM'e gönderilecek prompt
            
        Returns:
            str: Üretilen metin
        """
        if not self.llm:
            return None
        
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            print(f"Ollama text generation hatası: {e}")
            return None


class HuggingFaceService:
    """
    Hugging Face servisi - Büyük LLM API'si
    
    Coordinator agent için güçlü LLM API'si ile iletişim.
    OpenAI-compatible format kullanır.
    """
    
    def __init__(self):
        """Hugging Face servisini başlatır"""
        self.api_key = config.HUGGINGFACE_API_KEY
        self.api_url = config.HUGGINGFACE_API_URL
        self.model = config.HUGGINGFACE_MODEL
    
    def is_healthy(self) -> bool:
        """Hugging Face servisinin sağlık durumunu kontrol eder"""
        return self.api_key is not None
    
    def generate_response(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Hugging Face API ile yanıt üretir
        
        Args:
            system_prompt: Sistem prompt'u
            user_prompt: Kullanıcı prompt'u
            
        Returns:
            Dict[str, Any]: API yanıtı
        """
        if not self.api_key:
            return {"text": "Hugging Face API anahtarı bulunamadı"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "model": self.model
            }
            
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=config.API_TIMEOUTS["HUGGINGFACE"]
            )
            
            result = response.json()
            
            if response.status_code == 200 and "choices" in result:
                return {"text": result["choices"][0]["message"]["content"]}
            else:
                return {"error": "huggingface_api_failed", "detail": result.get("error", "Unknown error")}
                
        except Exception as e:
            return {"error": "huggingface_api_failed", "detail": str(e)}


class MCPService:
    """
    MCP Finance Tools servisi
    
    Finansal araçlar mikroservisi ile iletişim.
    Tüm finansal işlemler bu servis üzerinden yapılır.
    """
    
    def __init__(self):
        """MCP servisini başlatır"""
        self.base_url = config.MCP_BASE_URL
    
    def is_healthy(self) -> bool:
        """MCP servisinin sağlık durumunu kontrol eder"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def call_tool(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP aracını çağırır
        
        Args:
            path: Araç yolu
            payload: Gönderilecek veri
            
        Returns:
            Dict[str, Any]: Araç yanıtı
        """
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = requests.post(
                url, 
                json=payload, 
                timeout=config.API_TIMEOUTS["MCP_CALL"]
            )
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"error": "mcp_call_failed", "detail": "Invalid JSON response", "url": url}
            else:
                return {"error": "mcp_call_failed", "detail": f"HTTP {response.status_code}: {response.text}", "url": url}
                
        except Exception as e:
            return {"error": "mcp_call_failed", "detail": str(e), "url": url}


# Global servis manager instance
service_manager = ServiceManager()
