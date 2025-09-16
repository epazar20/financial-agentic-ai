"""
Finansal Agentic Proje Konfigürasyon Dosyası
============================================

Bu dosya tüm servis bağlantıları ve konfigürasyon ayarlarını içerir.
Environment variables'dan değerleri alır ve varsayılan değerler sağlar.

Servisler:
- Redis: Kısa vadeli hafıza için
- Qdrant: Uzun vadeli vektör hafızası için  
- Kafka: Event streaming için
- Ollama: Küçük LLM modelleri için
- Hugging Face: Büyük LLM API'si için
- MCP Finance Tools: Finansal araçlar için
"""

import os
from typing import Optional


class Config:
    """
    Ana konfigürasyon sınıfı
    
    Tüm servis bağlantı bilgilerini ve API anahtarlarını yönetir.
    Environment variables'dan değerleri okur ve varsayılan değerler sağlar.
    """
    
    # MCP Finance Tools Konfigürasyonu
    # Mikroservis finansal araçları için temel URL
    MCP_BASE_URL: str = os.environ.get("MCP_BASE_URL", "http://mcp-finance-tools:4000")
    
    # Redis Konfigürasyonu (Kısa Vadeli Hafıza)
    # Kullanıcı eylemleri ve geçici veriler için Redis bağlantısı
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://financial-redis:6379/0")
    
    # Qdrant Konfigürasyonu (Uzun Vadeli Vektör Hafızası)
    # Finansal analizlerin vektör olarak saklanması için
    QDRANT_HOST: str = os.environ.get("QDRANT_HOST", "financial-qdrant")
    QDRANT_PORT: str = os.environ.get("QDRANT_PORT", "6333")
    
    # Ollama Konfigürasyonu (Küçük LLM Modelleri)
    # Tool calling ve embedding işlemleri için yerel LLM servisi
    # ngrok ile host edilen Ollama servisi kullanılıyor
    OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_HOST", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    
    # Kafka Konfigürasyonu (Event Streaming)
    # Mikroservisler arası asenkron iletişim için
    KAFKA_BOOTSTRAP_SERVERS: str = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "financial-kafka:9092")
    
    # Hugging Face API Konfigürasyonu (Büyük LLM)
    # Coordinator agent için güçlü LLM API'si
    HUGGINGFACE_API_URL: str = os.environ.get(
        "HUGGINGFACE_API_URL", 
        "https://router.huggingface.co/novita/v3/openai/chat/completions"
    )
    HUGGINGFACE_API_KEY: Optional[str] = os.environ.get("HUGGINGFACE_API_KEY")
    HUGGINGFACE_MODEL: str = os.environ.get("HUGGINGFACE_MODEL", "deepseek/deepseek-v3-0324")
    
    # Flask Uygulama Konfigürasyonu
    FLASK_HOST: str = os.environ.get("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.environ.get("FLASK_PORT", "5000"))
    FLASK_DEBUG: bool = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    
    # CORS Konfigürasyonu
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
    
    # Qdrant Collection Ayarları
    FINANCIAL_MEMORY_COLLECTION: str = "financial_memory"
    VECTOR_SIZE: int = 768  # nomic-embed-text modelinin vektör boyutu
    VECTOR_DISTANCE: str = "COSINE"  # Vektör benzerlik ölçümü
    
    # Kafka Topic'leri
    KAFKA_TOPICS = {
        "TRANSACTIONS_DEPOSIT": "transactions.deposit",
        "PAYMENTS_PENDING": "payments.pending", 
        "PAYMENTS_EXECUTED": "payments.executed",
        "RISK_ANALYSIS": "risk.analysis",
        "INVESTMENTS_PROPOSAL": "investments.proposal",
        "ADVISOR_FINAL_MESSAGE": "advisor.finalMessage"
    }
    
    # Ollama Model Ayarları
    OLLAMA_MODELS = {
        "LLM_MODEL": "llama3.2:3b",  # Tool calling için güçlü model (ngrok ile host edilen)
        "EMBEDDING_MODEL": "nomic-embed-text:latest"  # Embedding için nomic model
    }
    
    # Redis Key Patterns
    REDIS_KEYS = {
        "USER_LAST_ACTION": "user:{user_id}:last_action",
        "USER_LAST_EVENTS": "user:{user_id}:last_events"
    }
    
    # Redis TTL Ayarları (saniye)
    REDIS_TTL = {
        "USER_ACTION": 60 * 60 * 24,  # 24 saat
        "USER_EVENTS": 60 * 60 * 24   # 24 saat
    }
    
    # API Timeout Ayarları
    API_TIMEOUTS = {
        "MCP_CALL": 6,      # MCP servis çağrıları için
        "HUGGINGFACE": 30,  # Hugging Face API için
        "HTTP_REQUEST": 10   # Genel HTTP istekleri için
    }
    
    @classmethod
    def get_qdrant_config(cls) -> dict:
        """
        Qdrant konfigürasyonunu dictionary olarak döndürür
        
        Returns:
            dict: Qdrant bağlantı ve collection ayarları
        """
        return {
            "host": cls.QDRANT_HOST,
            "port": int(cls.QDRANT_PORT),
            "collection_name": cls.FINANCIAL_MEMORY_COLLECTION,
            "vector_size": cls.VECTOR_SIZE,
            "distance": cls.VECTOR_DISTANCE
        }
    
    @classmethod
    def get_kafka_config(cls) -> dict:
        """
        Kafka konfigürasyonunu dictionary olarak döndürür
        
        Returns:
            dict: Kafka bootstrap servers ve topic ayarları
        """
        return {
            "bootstrap_servers": [cls.KAFKA_BOOTSTRAP_SERVERS],
            "topics": cls.KAFKA_TOPICS
        }
    
    @classmethod
    def get_redis_config(cls) -> dict:
        """
        Redis konfigürasyonunu dictionary olarak döndürür
        
        Returns:
            dict: Redis URL ve TTL ayarları
        """
        return {
            "url": cls.REDIS_URL,
            "ttl": cls.REDIS_TTL,
            "key_patterns": cls.REDIS_KEYS
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Konfigürasyonun geçerliliğini kontrol eder
        
        Returns:
            bool: Konfigürasyon geçerli ise True
        """
        required_configs = [
            cls.MCP_BASE_URL,
            cls.REDIS_URL,
            cls.QDRANT_HOST,
            cls.KAFKA_BOOTSTRAP_SERVERS
        ]
        
        return all(config for config in required_configs)
    
    @classmethod
    def print_config(cls):
        """
        Mevcut konfigürasyonu güvenli bir şekilde yazdırır
        (API anahtarları gizlenir)
        """
        print("=== Finansal Agentic Proje Konfigürasyonu ===")
        print(f"MCP Base URL: {cls.MCP_BASE_URL}")
        print(f"Redis URL: {cls.REDIS_URL}")
        print(f"Qdrant Host: {cls.QDRANT_HOST}:{cls.QDRANT_PORT}")
        print(f"Kafka Servers: {cls.KAFKA_BOOTSTRAP_SERVERS}")
        print(f"Ollama Base URL: {cls.OLLAMA_BASE_URL}")
        print(f"Hugging Face API URL: {cls.HUGGINGFACE_API_URL}")
        print(f"Hugging Face Model: {cls.HUGGINGFACE_MODEL}")
        print(f"Hugging Face API Key: {'***' if cls.HUGGINGFACE_API_KEY else 'Not Set'}")
        print(f"Flask Host: {cls.FLASK_HOST}:{cls.FLASK_PORT}")
        print(f"CORS Origins: {cls.CORS_ORIGINS}")
        print("=============================================")


# Singleton konfigürasyon instance'ı
config = Config()
