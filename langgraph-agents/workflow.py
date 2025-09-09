"""
Finansal Agentic Proje LangGraph Workflow
=========================================

Bu modül LangGraph kullanarak finansal agent'ların workflow'unu yönetir.
Multi-agent sistem mimarisi ile PaymentsAgent, RiskAgent, InvestmentAgent
ve CoordinatorAgent'ları koordine eder.

Workflow Akışı:
1. PaymentsAgent: Maaş yatışını analiz eder ve transfer önerisi yapar
2. RiskAgent: İşlem riskini değerlendirir
3. InvestmentAgent: Risk profiline göre yatırım önerileri sunar
4. CoordinatorAgent: Tüm bilgileri birleştirerek final mesaj oluşturur
"""

import time
import json
from typing import TypedDict, Dict, Any, Optional
from queue import Queue
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from config import config
from services import service_manager


class FinancialState(TypedDict):
    """
    LangGraph workflow state tanımı
    
    Workflow boyunca taşınan tüm verileri içerir.
    Her agent bu state'i güncelleyerek bir sonraki agent'a bilgi aktarır.
    """
    userId: str          # Kullanıcı ID'si
    amount: int          # Maaş miktarı
    correlationId: str   # İşlem takip ID'si
    payments_output: Dict[str, Any]    # PaymentsAgent çıktısı
    risk_output: Dict[str, Any]        # RiskAgent çıktısı
    investment_output: Dict[str, Any]  # InvestmentAgent çıktısı
    final_message: str    # CoordinatorAgent final mesajı
    user_action: str     # Kullanıcı eylemi


class FinancialWorkflow:
    """
    Finansal agent'ların LangGraph workflow'unu yöneten ana sınıf
    
    Bu sınıf multi-agent sistem mimarisini implement eder ve
    tüm agent'ları koordine eder.
    """
    
    def __init__(self, publisher_queue: Queue):
        """
        Workflow'u başlatır
        
        Args:
            publisher_queue: Event yayınlama kuyruğu
        """
        self.publisher_queue = publisher_queue
        self.workflow = None
        self._create_workflow()
    
    def _create_workflow(self):
        """LangGraph workflow'unu oluşturur"""
        print("Finansal workflow oluşturuluyor...")
        
        # StateGraph oluştur
        workflow = StateGraph(FinancialState)
        
        # Agent node'larını ekle
        workflow.add_node("payments", self._payments_agent)
        workflow.add_node("risk", self._risk_agent)
        workflow.add_node("investment", self._investment_agent)
        workflow.add_node("coordinator", self._coordinator_agent)
        
        # Workflow akışını tanımla
        workflow.add_edge("payments", "risk")
        workflow.add_edge("risk", "investment")
        workflow.add_edge("investment", "coordinator")
        workflow.add_edge("coordinator", END)
        
        # Entry point'i ayarla
        workflow.set_entry_point("payments")
        
        # Workflow'u compile et
        memory = MemorySaver()
        self.workflow = workflow.compile(checkpointer=memory)
        
        print("✅ Finansal workflow başarıyla oluşturuldu")
    
    def _payments_agent(self, state: FinancialState) -> FinancialState:
        """
        PaymentsAgent: Maaş yatışını analiz eder ve transfer önerisi yapar
        
        Bu agent:
        - Kullanıcı profilini ve geçmiş işlemlerini analiz eder
        - Otomatik tasarruf oranını hesaplar
        - Transfer önerisi oluşturur
        - Kafka'ya payments.pending event'i gönderir
        
        Args:
            state: Mevcut workflow state'i
            
        Returns:
            FinancialState: Güncellenmiş state
        """
        print("🔄 PaymentsAgent çalışıyor...")
        
        userId = state["userId"]
        amount = state["amount"]
        
        # Kullanıcı profilini ve işlemlerini al
        profile = self._call_mcp_tool("userProfile.get", {"userId": userId})
        auto_rate = profile.get("savedPreferences", {}).get("autoSavingsRate", 0.3)
        propose_amount = int(amount * auto_rate)
        
        # PaymentsAgent çıktısını oluştur
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
        
        # Event'i yayınla
        self.publisher_queue.put({"event": "agent-output", "data": payments_output})
        
        # Kafka'ya gönder
        service_manager.kafka_service.publish_event(
            config.KAFKA_TOPICS["PAYMENTS_PENDING"],
            {
                "userId": userId,
                "proposal": payments_output["proposal"],
                "correlationId": state["correlationId"]
            }
        )
        
        print(f"✅ PaymentsAgent tamamlandı: {propose_amount:,}₺ transfer önerisi")
        return {**state, "payments_output": payments_output}
    
    def _risk_agent(self, state: FinancialState) -> FinancialState:
        """
        RiskAgent: İşlem riskini değerlendirir
        
        Bu agent:
        - Transfer işleminin risk skorunu hesaplar
        - Risk analizi yapar
        - Kafka'ya risk.analysis event'i gönderir
        
        Args:
            state: Mevcut workflow state'i
            
        Returns:
            FinancialState: Güncellenmiş state
        """
        print("🔄 RiskAgent çalışıyor...")
        
        userId = state["userId"]
        proposal = state["payments_output"]["proposal"]
        
        # Risk skorunu hesapla
        risk_result = self._call_mcp_tool("risk.scoreTransaction", {
            "userId": userId,
            "tx": {
                "amount": proposal["amount"],
                "type": "internal_transfer"
            }
        })
        
        # RiskAgent çıktısını oluştur
        risk_score = risk_result.get("score", 0.5)
        risk_output = {
            "agent": "RiskAgent",
            "analysis": risk_result,
            "message": f"İşlem güvenli, {'düşük' if risk_score < 0.5 else 'yüksek'} riskli."
        }
        
        # Event'i yayınla
        self.publisher_queue.put({"event": "agent-output", "data": risk_output})
        
        # Kafka'ya gönder
        service_manager.kafka_service.publish_event(
            config.KAFKA_TOPICS["RISK_ANALYSIS"],
            {
                "userId": userId,
                "analysis": risk_result,
                "correlationId": state["correlationId"]
            }
        )
        
        print(f"✅ RiskAgent tamamlandı: Risk skoru {risk_score}")
        return {**state, "risk_output": risk_output}
    
    def _investment_agent(self, state: FinancialState) -> FinancialState:
        """
        InvestmentAgent: Risk profiline göre yatırım önerileri sunar
        
        Bu agent:
        - Risk skoruna göre yatırım stratejisi belirler
        - Piyasa kotalarını alır
        - Yatırım önerilerini oluşturur
        - Kafka'ya investments.proposal event'i gönderir
        
        Args:
            state: Mevcut workflow state'i
            
        Returns:
            FinancialState: Güncellenmiş state
        """
        print("🔄 InvestmentAgent çalışıyor...")
        
        userId = state["userId"]
        risk_score = state["risk_output"]["analysis"].get("score", 0.5)
        
        # Risk bazlı yatırım stratejisi
        if risk_score < 0.3:  # Düşük risk - agresif
            asset_types = ["bond", "equity", "fund"]
        else:  # Yüksek risk - muhafazakar
            asset_types = ["bond", "savings"]
        
        # Piyasa kotalarını al
        quotes = {}
        for asset_type in asset_types:
            quotes[asset_type] = self._call_mcp_tool("market.quotes", {
                "assetType": asset_type,
                "tenor": "1Y"
            })
        
        # InvestmentAgent çıktısını oluştur
        investment_output = {
            "agent": "InvestmentAgent",
            "recommendation": quotes,
            "message": f"Risk durumuna göre yatırım önerileri: {', '.join(asset_types)}"
        }
        
        # Event'i yayınla
        self.publisher_queue.put({"event": "agent-output", "data": investment_output})
        
        # Kafka'ya gönder
        service_manager.kafka_service.publish_event(
            config.KAFKA_TOPICS["INVESTMENTS_PROPOSAL"],
            {
                "userId": userId,
                "recommendation": quotes,
                "correlationId": state["correlationId"]
            }
        )
        
        print(f"✅ InvestmentAgent tamamlandı: {len(asset_types)} yatırım önerisi")
        return {**state, "investment_output": investment_output}
    
    def _coordinator_agent(self, state: FinancialState) -> FinancialState:
        """
        CoordinatorAgent: Tüm bilgileri birleştirerek final mesaj oluşturur
        
        Bu agent:
        - Redis'ten kısa vadeli hafızayı alır
        - Qdrant'tan uzun vadeli hafızayı alır
        - Hugging Face API ile final mesaj oluşturur
        - Hafızaları günceller
        - Kafka'ya advisor.finalMessage event'i gönderir
        
        Args:
            state: Mevcut workflow state'i
            
        Returns:
            FinancialState: Güncellenmiş state
        """
        print("🔄 CoordinatorAgent çalışıyor...")
        
        userId = state["userId"]
        amount = state["amount"]
        correlationId = state["correlationId"]
        
        # Kısa vadeli hafızayı al (Redis)
        short_term_memory = self._get_short_term_memory(userId)
        
        # Uzun vadeli hafızayı al (Qdrant)
        long_term_memory = self._get_long_term_memory(userId, "deposit analysis")
        
        # Kapsamlı prompt oluştur
        prompt = self._build_coordinator_prompt(
            userId, amount, state, short_term_memory, long_term_memory
        )
        
        # Hugging Face API ile final mesaj oluştur
        system_prompt = self._get_coordinator_system_prompt()
        llm_response = service_manager.huggingface_service.generate_response(
            system_prompt, prompt
        )
        
        final_message = llm_response.get("text", "Analiz tamamlandı.")
        
        # Hafızaları güncelle
        self._update_memories(userId, amount, correlationId, final_message)
        
        # Final notification oluştur
        notification = {
            "type": "final_proposal",
            "userId": userId,
            "correlationId": correlationId,
            "message": final_message,
            "proposal": state["payments_output"]["proposal"]
        }
        
        # Event'i yayınla
        self.publisher_queue.put({"event": "notification", "data": notification})
        
        # Kafka'ya gönder
        service_manager.kafka_service.publish_event(
            config.KAFKA_TOPICS["ADVISOR_FINAL_MESSAGE"],
            notification
        )
        
        print(f"✅ CoordinatorAgent tamamlandı: Final mesaj oluşturuldu")
        return {**state, "final_message": final_message}
    
    def _call_mcp_tool(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP aracını çağırır
        
        Args:
            path: Araç yolu
            payload: Gönderilecek veri
            
        Returns:
            Dict[str, Any]: Araç yanıtı
        """
        return service_manager.mcp_service.call_tool(path, payload)
    
    def _get_short_term_memory(self, userId: str) -> str:
        """
        Redis'ten kısa vadeli hafızayı alır
        
        Args:
            userId: Kullanıcı ID'si
            
        Returns:
            str: Kısa vadeli hafıza bilgisi
        """
        last_action = service_manager.redis_service.get_user_action(userId)
        if last_action:
            return f"Son kullanıcı eylemi: {last_action}"
        return ""
    
    def _get_long_term_memory(self, userId: str, query: str) -> str:
        """
        Qdrant'tan uzun vadeli hafızayı alır
        
        Args:
            userId: Kullanıcı ID'si
            query: Arama sorgusu
            
        Returns:
            str: Uzun vadeli hafıza bilgisi
        """
        similar_memories = service_manager.qdrant_service.search_similar(
            userId, query, top_k=3
        )
        
        if similar_memories:
            memory_texts = [
                f"- {mem['payload'].get('content', '')[:100]}..." 
                for mem in similar_memories
            ]
            return f"Geçmiş benzer analizler:\n" + "\n".join(memory_texts)
        return ""
    
    def _build_coordinator_prompt(self, userId: str, amount: int, state: FinancialState, 
                                short_term_memory: str, long_term_memory: str) -> str:
        """
        Coordinator agent için kapsamlı prompt oluşturur
        
        Args:
            userId: Kullanıcı ID'si
            amount: Maaş miktarı
            state: Workflow state'i
            short_term_memory: Kısa vadeli hafıza
            long_term_memory: Uzun vadeli hafıza
            
        Returns:
            str: Coordinator prompt'u
        """
        return f"""
Kullanıcı {userId} için {amount:,}₺ maaş yatışı analizi:

PaymentsAgent: {state['payments_output']['message']}
RiskAgent: {state['risk_output']['message']}
InvestmentAgent: {state['investment_output']['message']}

Short-term memory: {short_term_memory}
Long-term memory: {long_term_memory}

Bu bilgileri kullanarak kullanıcıya kişiselleştirilmiş, samimi ve net bir öneri mesajı oluştur.
"""
    
    def _get_coordinator_system_prompt(self) -> str:
        """
        Coordinator agent için system prompt döndürür
        
        Returns:
            str: System prompt
        """
        return """Sen bir finansal danışmansın. Kullanıcıya samimi, güvenilir ve kişiselleştirilmiş tavsiyeler veriyorsun. 

Görevlerin:
1. Kullanıcının finansal durumunu analiz et
2. Risk profiline göre uygun öneriler sun
3. Geçmiş tercihlerini dikkate al
4. Net ve anlaşılır bir dil kullan
5. Kullanıcıya güven veren bir ton kullan

Türkçe yanıt ver ve finansal terimleri açıkla."""
    
    def _update_memories(self, userId: str, amount: int, correlationId: str, final_message: str):
        """
        Hafızaları günceller
        
        Args:
            userId: Kullanıcı ID'si
            amount: Maaş miktarı
            correlationId: İşlem takip ID'si
            final_message: Final mesaj
        """
        # Uzun vadeli hafızayı güncelle (Qdrant)
        service_manager.qdrant_service.store_memory(
            user_id=userId,
            content=f"Deposit analysis for {amount}₺: {final_message}",
            metadata={
                "type": "deposit_analysis",
                "amount": amount,
                "correlationId": correlationId
            }
        )
        
        # Kısa vadeli hafızayı güncelle (Redis)
        service_manager.redis_service.push_user_event(userId, {
            "type": "deposit",
            "amount": amount,
            "ts": int(time.time()),
            "message": final_message
        })
    
    def execute(self, initial_state: FinancialState) -> Optional[FinancialState]:
        """
        Workflow'u çalıştırır
        
        Args:
            initial_state: Başlangıç state'i
            
        Returns:
            FinancialState: Workflow sonucu
        """
        if not self.workflow:
            print("❌ Workflow henüz oluşturulmamış")
            return None
        
        try:
            print(f"🚀 Workflow başlatılıyor: {initial_state['correlationId']}")
            
            # Workflow'u çalıştır
            config_dict = {"configurable": {"thread_id": initial_state["correlationId"]}}
            result = self.workflow.invoke(initial_state, config=config_dict)
            
            print(f"✅ Workflow tamamlandı: {initial_state['userId']}")
            return result
            
        except Exception as e:
            print(f"❌ Workflow çalıştırma hatası: {e}")
            return None
    
    def is_ready(self) -> bool:
        """
        Workflow'un hazır olup olmadığını kontrol eder
        
        Returns:
            bool: Hazır ise True
        """
        return self.workflow is not None


# LangGraph Tools - MCP Finance Tools için
@tool
def transactions_query(userId: str, since: str = None, limit: int = 10) -> dict:
    """
    Kullanıcı işlemlerini sorgular
    
    Args:
        userId: Kullanıcı ID'si
        since: Başlangıç tarihi (opsiyonel)
        limit: Maksimum sonuç sayısı
        
    Returns:
        dict: İşlem listesi
    """
    return service_manager.mcp_service.call_tool("transactions.query", {
        "userId": userId, 
        "since": since, 
        "limit": limit
    })


@tool
def user_profile_get(userId: str) -> dict:
    """
    Kullanıcı profilini ve tercihlerini getirir
    
    Args:
        userId: Kullanıcı ID'si
        
    Returns:
        dict: Kullanıcı profili
    """
    return service_manager.mcp_service.call_tool("userProfile.get", {"userId": userId})


@tool
def risk_score_transaction(userId: str, tx: dict) -> dict:
    """
    İşlem risk skorunu hesaplar
    
    Args:
        userId: Kullanıcı ID'si
        tx: İşlem bilgileri
        
    Returns:
        dict: Risk analizi
    """
    return service_manager.mcp_service.call_tool("risk.scoreTransaction", {
        "userId": userId, 
        "tx": tx
    })


@tool
def market_quotes(assetType: str, tenor: str = "1Y") -> dict:
    """
    Yatırım ürünleri için piyasa kotalarını getirir
    
    Args:
        assetType: Varlık türü (bond, equity, fund, savings)
        tenor: Vade süresi
        
    Returns:
        dict: Piyasa kotaları
    """
    return service_manager.mcp_service.call_tool("market.quotes", {
        "assetType": assetType, 
        "tenor": tenor
    })


@tool
def savings_create_transfer(userId: str, fromAccount: str, toSavingsId: str, amount: int) -> dict:
    """
    Tasarruf transferi oluşturur
    
    Args:
        userId: Kullanıcı ID'si
        fromAccount: Kaynak hesap
        toSavingsId: Hedef tasarruf hesabı
        amount: Transfer miktarı
        
    Returns:
        dict: Transfer sonucu
    """
    return service_manager.mcp_service.call_tool("savings.createTransfer", {
        "userId": userId,
        "fromAccount": fromAccount,
        "toSavingsId": toSavingsId,
        "amount": amount
    })
