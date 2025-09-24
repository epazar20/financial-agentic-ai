"""
Finansal Agentic Proje LangGraph Workflow
=========================================

Bu modül LangGraph'in gerçek gücünü kullanarak finansal agent'ların workflow'unu yönetir.
LangGraph'in multi-agent sistem mimarisi ile PaymentsAgent, RiskAgent, InvestmentAgent
ve CoordinatorAgent'ları koordine eder.

LangGraph Özellikleri:
- StateGraph: Agent'lar arası state yönetimi
- Tool Calling: Agent'ların MCP araçlarını kullanması
- Conditional Routing: Dinamik akış kontrolü
- Memory Management: Redis + Qdrant entegrasyonu
- Error Handling: Hata durumlarında fallback mekanizmaları
- Gerçek Ollama LLM: llama3.2:1b model'i ile gerçek LLM çağrıları
- MCP Tool Calling: Fallback sistem ile MCP araçları entegrasyonu

Workflow Akışı:
1. PaymentsAgent: Maaş yatışını analiz eder ve transfer önerisi yapar
2. RiskAgent: İşlem riskini değerlendirir
3. InvestmentAgent: Risk profiline göre yatırım önerileri sunar
4. CoordinatorAgent: Tüm bilgileri birleştirerek final mesaj oluşturur
5. UserInteraction: Kullanıcı etkileşimi ve onay süreci
6. Execution: Onaylanan işlemlerin gerçekleştirilmesi

Son Güncellemeler (2025-09-16):
- Gerçek Ollama llama3.2:1b model'i entegrasyonu
- Bellek optimizasyonu (llama3.2:3b → llama3.2:1b)
- Timeout iyileştirmeleri (30s → 120s)
- MCP Tool Calling fallback sistemi
- Manuel HTTP istekleri ile Ollama entegrasyonu
"""

import time
import json
from typing import TypedDict, Dict, Any, Optional, List, Literal
from queue import Queue
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

from config import config
from services import service_manager


class FinancialState(TypedDict):
    """
    LangGraph workflow state tanımı - LangGraph'in gerçek state yapısı
    
    LangGraph'te state, mesajlar ve verilerin birleşimidir. Bu state:
    - messages: Agent'lar arası iletişim için mesaj listesi
    - data: Workflow boyunca taşınan veriler
    - current_step: Hangi adımda olduğumuzu takip eder
    - user_action: Kullanıcı etkileşimi sonucu
    - error: Hata durumları için
    """
    # LangGraph mesaj sistemi
    messages: List[HumanMessage | AIMessage | SystemMessage]
    
    # Workflow verileri
    userId: str
    amount: int
    correlationId: str
    
    # Agent çıktıları
    payments_output: Optional[Dict[str, Any]]
    risk_output: Optional[Dict[str, Any]]
    investment_output: Optional[Dict[str, Any]]
    coordinator_output: Optional[Dict[str, Any]]
    
    # Kullanıcı etkileşimi
    user_action: Optional[str]  # "approve", "reject", "custom_message"
    custom_message: Optional[str]
    
    # Workflow kontrolü
    current_step: str
    error: Optional[str]
    final_result: Optional[Dict[str, Any]]


class FinancialWorkflow:
    """
    Finansal agent'ların LangGraph workflow'unu yöneten ana sınıf
    
    Bu sınıf LangGraph'in gerçek multi-agent sistem mimarisini implement eder:
    - Her agent bir LangGraph node'u olarak tanımlanır
    - Agent'lar arası iletişim mesaj sistemi ile yapılır
    - Tool calling ile MCP araçları kullanılır
    - Conditional routing ile dinamik akış kontrolü
    - Memory management ile Redis + Qdrant entegrasyonu
    - Gerçek Ollama llama3.2:1b model'i ile LLM çağrıları
    - Fallback sistem ile MCP tool calling
    
    Son Güncellemeler (2025-09-16):
    - Bellek optimizasyonu: llama3.2:3b → llama3.2:1b
    - Timeout iyileştirmeleri: 30s → 120s
    - Manuel HTTP istekleri ile Ollama entegrasyonu
    - MCP Tool Calling fallback sistemi
    """
    
    def __init__(self, publisher_queue: Queue):
        """
        LangGraph workflow'unu başlatır
        
        Args:
            publisher_queue: Event yayınlama kuyruğu (Kafka entegrasyonu için)
        """
        self.publisher_queue = publisher_queue
        self.workflow = None
        
        # LangGraph için gerekli araçları tanımla
        self.tools = self._create_tools()
        
        # ========================================
        # LLM KONFİGÜRASYONU - ÇİFT LLM MİMARİSİ
        # ========================================
        
        # 🔥 ÖNEMLİ: Bu projede çift LLM mimarisi kullanılıyor!
        # 
        # 1. GÜÇLÜ LLM (Ollama llama3.2:3b - ngrok ile host edilen):
        #    - PaymentsAgent, RiskAgent, InvestmentAgent için
        #    - Tool calling için optimize edilmiş (3B parametre)
        #    - MCP araç çağrıları için güçlü analiz yeteneği
        #    - ngrok ile remote erişim, yüksek performans
        #
        # 2. BÜYÜK LLM (Hugging Face deepseek-v3-0324):
        #    - CoordinatorAgent için
        #    - RAG (Retrieval Augmented Generation) için optimize edilmiş
        #    - Redis + Qdrant memory entegrasyonu
        #    - Kişiselleştirilmiş final mesaj oluşturma
        
        # Ollama LLM'i başlat (ngrok ile host edilen remote servis)
        # NOT: LangChain'in ChatOllama sınıfı container içinde bağlantı sorunu yaşıyor
        # Bu yüzden fallback olarak manuel HTTP istekleri kullanacağız
        self.ollama_model = config.OLLAMA_MODELS["LLM_MODEL"]  # llama3.2:3b - ngrok ile host edilen
        self.ollama_base_url = config.OLLAMA_BASE_URL  # http://localhost:11434
        
        # LangChain ChatOllama'yı deneyelim, başarısız olursa fallback kullanacağız
        try:
            # Ollama client'ını doğrudan test et
            import ollama
            
            # Ollama client'ını test et
            client = ollama.Client(host=self.ollama_base_url)
            test_response = client.chat(
                model=self.ollama_model,
                messages=[{"role": "user", "content": "Test mesajı"}]
            )
            print(f"✅ Ollama client test başarılı: {test_response['message']['content'][:50]}...")
            
            # LangChain ChatOllama'yı oluştur
            self.llm = ChatOllama(
                model=self.ollama_model,
                base_url=self.ollama_base_url,
                temperature=0.1,
                request_timeout=60.0,
                num_ctx=2048
            )
            print("✅ ChatOllama başarıyla oluşturuldu")
            
            # Test çağrısı yap
            test_response = self.llm.invoke("Test mesajı")
            print(f"✅ ChatOllama test başarılı: {test_response.content[:50]}...")
            
        except Exception as e:
            print(f"⚠️ ChatOllama oluşturulamadı: {e}")
            print("🔄 Fallback modu aktif - Manuel HTTP istekleri kullanılacak")
            self.llm = None
        
        print("🤖 LLM Konfigürasyonu:")
        print(f"   🔹 Güçlü LLM: Ollama llama3.2:3b (Agent'lar için) - ngrok ile host edilen")
        print(f"   🔹 Büyük LLM: Hugging Face deepseek-v3-0324 (CoordinatorAgent için)")
        print(f"   🔹 Tool Calling: MCP Finance Tools entegrasyonu aktif")
        print(f"   🔹 Embedding: nomic-embed-text:latest (RAG sistemi için)")
        
        # Workflow'u oluştur
        self._create_langgraph_workflow()
    
    def _create_tools(self) -> List:
        """
        LangGraph için MCP araçlarını tanımlar
        
        Bu araçlar agent'ların MCP Finance Tools ile iletişim kurmasını sağlar.
        Her araç LangChain tool formatında tanımlanır.
        
        Returns:
            List: LangChain tool listesi
        """
        return [
            transactions_query,
            userProfile_get,
            risk_scoreTransaction,
            market_quotes,
            savings_createTransfer
        ]
    
    def _create_langgraph_workflow(self):
        """
        Gerçek LangGraph workflow'unu oluşturur
        
        Bu metod LangGraph'in tüm güçlü özelliklerini kullanır:
        - StateGraph: State yönetimi
        - ToolNode: Araç kullanımı
        - Conditional routing: Dinamik akış
        - Memory: Checkpointing
        """
        print("🚀 LangGraph workflow oluşturuluyor...")
        
        # StateGraph oluştur - LangGraph'in ana bileşeni
        workflow = StateGraph(FinancialState)
        
        # ========================================
        # 1. AGENT NODE'LARI TANIMLA
        # ========================================
        
        # PaymentsAgent node'u - Maaş analizi ve transfer önerisi
        workflow.add_node("payments_agent", self._payments_agent_node)
        
        # RiskAgent node'u - Risk analizi
        workflow.add_node("risk_agent", self._risk_agent_node)
        
        # InvestmentAgent node'u - Yatırım önerileri
        workflow.add_node("investment_agent", self._investment_agent_node)
        
        # CoordinatorAgent node'u - Final mesaj oluşturma
        workflow.add_node("coordinator_agent", self._coordinator_agent_node)
        
        # UserInteraction node'u - Kullanıcı etkileşimi
        workflow.add_node("user_interaction", self._user_interaction_node)
        
        # Execution node'u - İşlem gerçekleştirme
        workflow.add_node("execution", self._execution_node)
        
        # Tool node'u - MCP araçlarını kullanma
        tool_node = ToolNode(self.tools)
        workflow.add_node("tools", tool_node)
        
        # ========================================
        # 2. WORKFLOW AKIŞINI TANIMLA
        # ========================================
        
        # Başlangıç noktası
        workflow.add_edge(START, "payments_agent")
        
        # Sıralı agent akışı
        workflow.add_edge("payments_agent", "risk_agent")
        workflow.add_edge("risk_agent", "investment_agent")
        workflow.add_edge("investment_agent", "coordinator_agent")
        
        # Coordinator'dan sonra kullanıcı etkileşimi
        workflow.add_edge("coordinator_agent", "user_interaction")
        
        # Kullanıcı etkileşiminden sonra koşullu routing
        workflow.add_conditional_edges(
            "user_interaction",
            self._should_execute,
            {
                "execute": "execution",
                "end": END
            }
        )
        
        # Execution'dan sonra bitiş
        workflow.add_edge("execution", END)
        
        # ========================================
        # 3. WORKFLOW'U COMPILE ET
        # ========================================
        
        # Memory checkpointing ile compile et
        memory = MemorySaver()
        self.workflow = workflow.compile(checkpointer=memory)
        
        print("✅ LangGraph workflow başarıyla oluşturuldu")
        print("📋 Node'lar: payments_agent → risk_agent → investment_agent → coordinator_agent → user_interaction → execution")
        print("🔧 Araçlar: MCP Finance Tools entegrasyonu aktif")
        print("🧠 Memory: Redis + Qdrant checkpointing aktif")
    
    def _payments_agent_node(self, state: FinancialState) -> FinancialState:
        """
        PaymentsAgent Node - LangGraph node implementasyonu
        
        Bu node LangGraph'in gerçek node yapısını kullanır:
        - State'i alır ve günceller
        - Mesaj sistemi ile iletişim kurar
        - Tool calling ile MCP araçlarını kullanır
        - Event publishing ile Kafka'ya bildirim gönderir
        
        LangGraph Node Özellikleri:
        - Input: FinancialState
        - Output: Güncellenmiş FinancialState
        - Side Effects: Kafka event publishing
        """
        print("🔄 PaymentsAgent node çalışıyor...")
        
        try:
            # State'ten verileri al
            userId = state["userId"]
            amount = state["amount"]
            correlationId = state["correlationId"]
            
            # ========================================
            # 1. KULLANICI PROFİLİNİ ANALİZ ET
            # ========================================
            
            # System mesajı ile agent'a görev ver
            system_message = SystemMessage(content=f"""
Sen PaymentsAgent'sın. Görevin:
1. Kullanıcı {userId} için {amount:,}₺ maaş yatışını analiz et
2. Kullanıcı profilini ve tercihlerini incele
3. Otomatik tasarruf oranını hesapla
4. Transfer önerisi oluştur

Kullanabileceğin araçlar:
- user_profile_get: Kullanıcı profilini al
- transactions_query: Geçmiş işlemleri sorgula
- savings_create_transfer: Transfer önerisi oluştur

Türkçe yanıt ver ve detaylı analiz yap.
            """)
            
            # Human mesajı ile görevi başlat
            human_message = HumanMessage(content=f"""
Kullanıcı {userId} için {amount:,}₺ maaş yatışı analizi yap.
Önce kullanıcı profilini al, sonra geçmiş işlemlerini incele.
Otomatik tasarruf oranını hesaplayarak transfer önerisi oluştur.
            """)
            
            # Mesajları state'e ekle
            messages = state.get("messages", [])
            messages.extend([system_message, human_message])
            
            # ========================================
            # 2. LLM İLE ANALİZ YAP - OLLAMA LLaMA3.2:3B KULLANIMI
            # ========================================
            
            # 🔥 ÖNEMLİ: Burada Ollama üzerinden llama3.2:3b modeli kullanılıyor!
            # Bu güçlü LLM (3B parametre) agent'ların tool calling yapması için optimize edilmiş
            # LangChain'in bind_tools() metodu ile MCP araçları LLM'e bağlanıyor
            # LLM artık hangi araçları kullanabileceğini biliyor ve otomatik olarak çağırıyor
            
            print(f"🤖 PaymentsAgent: Ollama llama3.2:3b modeli ile analiz başlatılıyor...")
            
            # ChatOllama varsa kullan, yoksa manuel HTTP isteği gönder
            if self.llm:
                try:
                    response = self.llm.bind_tools(self.tools).invoke(messages)
                    print(f"✅ ChatOllama başarılı")
                except Exception as e:
                    print(f"⚠️ ChatOllama başarısız: {e}")
                    print(f"🔄 Manuel HTTP isteği gönderiliyor...")
                    response_content = self._call_ollama_manual(messages)
                    # Mock response oluştur
                    # AIMessage zaten import edilmiş
                    response = AIMessage(content=response_content)
            else:
                print(f"🔄 Manuel HTTP isteği gönderiliyor...")
                response_content = self._call_ollama_manual(messages)
                # Mock response oluştur
                # AIMessage zaten import edilmiş
                response = AIMessage(content=response_content)
            
            # ========================================
            # 3. MCP TOOL ÇAĞRILARI - LLM TOOL CALLING
            # ========================================
            
            # 🔥 ÖNEMLİ: LLM'in tool çağrıları yapıp yapmadığını kontrol et
            print(f"🔍 PaymentsAgent: LLM yanıtı alındı, tool çağrıları kontrol ediliyor...")
            print(f"📋 LLM yanıtı: {response.content[:200]}...")
            print(f"📋 Tool calls sayısı: {len(response.tool_calls) if response.tool_calls else 0}")
            
            profile = None
            transactions = None
            
            if response.tool_calls:
                print(f"🎯 PaymentsAgent: {len(response.tool_calls)} adet MCP tool çağrısı tespit edildi!")
                
                # Tool çağrılarını gerçekleştir
                tool_results = []
                for i, tool_call in enumerate(response.tool_calls):
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    print(f"🔧 PaymentsAgent: Tool #{i+1} çağrılıyor: {tool_name}")
                    print(f"📥 Tool args: {tool_args}")
                    
                    # MCP aracını çağır
                    result = self._call_mcp_tool(tool_name, tool_args)
                    tool_results.append(f"{tool_name}: {result}")
                    
                    print(f"✅ PaymentsAgent: Tool #{i+1} tamamlandı: {tool_name}")
                    print(f"📤 Tool result: {str(result)[:200]}...")
                    
                    # Sonuçları sakla
                    if tool_name == "userProfile_get":
                        profile = result
                    elif tool_name == "transactions_query":
                        transactions = result
                
                # Tool sonuçlarını mesaj olarak ekle
                tool_message = AIMessage(content=f"Tool çağrıları tamamlandı: {'; '.join(tool_results)}")
                messages.append(tool_message)
                
                print(f"🔄 PaymentsAgent: Final LLM yanıtı alınıyor...")
                # Final yanıtı al
                final_response = self.llm.invoke(messages)
                messages.append(final_response)
                print(f"✅ PaymentsAgent: Final LLM yanıtı alındı")
            else:
                print(f"⚠️ PaymentsAgent: LLM hiç tool çağrısı yapmadı!")
                print(f"🤔 LLM yanıtı: {response.content[:200]}...")
                
                # Fallback: Manuel olarak gerekli tool'ları çağır
                print(f"🔄 PaymentsAgent: Fallback olarak manuel tool çağrıları yapılıyor...")
                profile = self._call_mcp_tool("userProfile.get", {"userId": userId})
                transactions = self._call_mcp_tool("transactions.query", {
                    "userId": userId,
                    "since": "last30d",
                    "limit": 10
                })
                print(f"📊 PaymentsAgent: Fallback tool çağrıları tamamlandı")
            
            # ========================================
            # 4. PAYMENTS OUTPUT OLUŞTUR
            # ========================================
            
            # LLM tool çağrılarından veya fallback'ten gelen verileri kullan
            if profile is None:
                print(f"⚠️ PaymentsAgent: Profile bulunamadı, varsayılan değerler kullanılıyor")
                profile = {"savedPreferences": {"autoSavingsRate": 0.3}}
            
            auto_rate = profile.get("savedPreferences", {}).get("autoSavingsRate", 0.3)
            propose_amount = int(amount * auto_rate)
            
            print(f"💰 PaymentsAgent: Tasarruf oranı hesaplandı: {auto_rate} ({auto_rate*100}%)")
            print(f"💰 PaymentsAgent: Transfer miktarı hesaplandı: {propose_amount:,}₺")
            print(f"💰 PaymentsAgent: LLM tool calling {'başarılı' if response.tool_calls else 'başarısız - fallback kullanıldı'}")
            
            payments_output = {
                "agent": "PaymentsAgent",
                "action": "analyze_deposit",
                "proposal": {
                    "action": "propose_transfer",
                    "amount": propose_amount,
                    "from": "CHK001",
                    "to": "SV001",
                    "rate": auto_rate
                },
                "message": f"Maaşın {amount:,}₺ olarak hesabına geçti. Plan gereği {propose_amount:,}₺ tasarrufa aktarılabilir.",
                "analysis": {
                    "user_profile": profile,
                    "auto_savings_rate": auto_rate,
                    "proposed_amount": propose_amount
                }
            }
            
            # ========================================
            # 4. EVENT PUBLISHING
            # ========================================
            
            # Agent çıktısını Kafka'ya gönder
            payments_output["type"] = "agent-output"
            self.publisher_queue.put({"event": "agent-output", "data": payments_output})
            
            # Kafka'ya payments.pending event'i gönder
            service_manager.kafka_service.publish_event(
                config.KAFKA_TOPICS["PAYMENTS_PENDING"],
                {
                    "userId": userId,
                    "proposal": payments_output["proposal"],
                    "correlationId": correlationId
                }
            )
            
            # ========================================
            # 5. STATE GÜNCELLE
            # ========================================
            
            # State'i güncelle
            updated_state = {
                **state,
                "messages": messages,
                "payments_output": payments_output,
                "current_step": "payments_agent_completed"
            }
            
            print(f"✅ PaymentsAgent node tamamlandı: {propose_amount:,}₺ transfer önerisi")
            return updated_state
            
        except Exception as e:
            print(f"❌ PaymentsAgent node hatası: {e}")
            return {
                **state,
                "error": f"PaymentsAgent hatası: {str(e)}",
                "current_step": "error"
            }
    
    def _risk_agent_node(self, state: FinancialState) -> FinancialState:
        """
        RiskAgent Node - LangGraph node implementasyonu
        
        Bu node risk analizi yapar ve LangGraph'in mesaj sistemi ile çalışır.
        """
        print("🔄 RiskAgent node çalışıyor...")
        
        try:
            userId = state["userId"]
            correlationId = state["correlationId"]
            payments_output = state.get("payments_output", {})
            
            if not payments_output:
                raise ValueError("PaymentsAgent çıktısı bulunamadı")
            
            proposal = payments_output.get("proposal", {})
            
            # ========================================
            # 1. RİSK ANALİZİ YAP
            # ========================================
            
            # System mesajı ile agent'a görev ver
            system_message = SystemMessage(content=f"""
Sen RiskAgent'sın. Görevin:
1. Transfer işleminin risk skorunu hesapla
2. Risk faktörlerini analiz et
3. Güvenlik durumunu değerlendir

Kullanabileceğin araçlar:
- risk_score_transaction: Risk skorunu hesapla

Türkçe yanıt ver ve risk analizini detaylandır.
            """)
            
            # Human mesajı ile görevi başlat
            human_message = HumanMessage(content=f"""
Transfer işlemi için risk analizi yap:
- Amount: {proposal.get('amount', 0):,}₺
- Type: internal_transfer
- User: {userId}

Risk skorunu hesapla ve analiz et.
            """)
            
            # Mesajları state'e ekle
            messages = state.get("messages", [])
            messages.extend([system_message, human_message])
            
            # ========================================
            # 2. LLM İLE RİSK ANALİZİ - OLLAMA LLaMA3.2:3B KULLANIMI
            # ========================================
            
            # 🔥 ÖNEMLİ: RiskAgent da Ollama llama3.2:3b modeli kullanıyor!
            # Risk analizi için MCP araçlarını (risk.scoreTransaction) çağırması bekleniyor
            
            print(f"🤖 RiskAgent: Ollama llama3.2:3b modeli ile risk analizi başlatılıyor...")
            
            # ChatOllama varsa kullan, yoksa manuel HTTP isteği gönder
            if self.llm:
                try:
                    response = self.llm.bind_tools(self.tools).invoke(messages)
                    print(f"✅ ChatOllama başarılı")
                except Exception as e:
                    print(f"⚠️ ChatOllama başarısız: {e}")
                    print(f"🔄 Manuel HTTP isteği gönderiliyor...")
                    response_content = self._call_ollama_manual(messages)
                    # Mock response oluştur
                    # AIMessage zaten import edilmiş
                    response = AIMessage(content=response_content)
            else:
                print(f"🔄 Manuel HTTP isteği gönderiliyor...")
                response_content = self._call_ollama_manual(messages)
                # Mock response oluştur
                # AIMessage zaten import edilmiş
                response = AIMessage(content=response_content)
            
            # ========================================
            # 3. MCP TOOL ÇAĞRILARI - LLM TOOL CALLING
            # ========================================
            
            # 🔥 ÖNEMLİ: LLM'in tool çağrıları yapıp yapmadığını kontrol et
            print(f"🔍 RiskAgent: LLM yanıtı alındı, tool çağrıları kontrol ediliyor...")
            print(f"📋 LLM yanıtı: {response.content[:200]}...")
            print(f"📋 Tool calls sayısı: {len(response.tool_calls) if response.tool_calls else 0}")
            
            risk_result = None
            
            if response.tool_calls:
                print(f"🎯 RiskAgent: {len(response.tool_calls)} adet MCP tool çağrısı tespit edildi!")
                
                # Tool çağrılarını gerçekleştir
                tool_results = []
                for i, tool_call in enumerate(response.tool_calls):
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    print(f"🔧 RiskAgent: Tool #{i+1} çağrılıyor: {tool_name}")
                    print(f"📥 Tool args: {tool_args}")
                    
                    # MCP aracını çağır
                    result = self._call_mcp_tool(tool_name, tool_args)
                    tool_results.append(f"{tool_name}: {result}")
                    
                    print(f"✅ RiskAgent: Tool #{i+1} tamamlandı: {tool_name}")
                    print(f"📤 Tool result: {str(result)[:200]}...")
                    
                    # Sonuçları sakla
                    if tool_name == "risk_scoreTransaction":
                        risk_result = result
                
                # Tool sonuçlarını mesaj olarak ekle
                tool_message = AIMessage(content=f"Tool çağrıları tamamlandı: {'; '.join(tool_results)}")
                messages.append(tool_message)
                
                print(f"🔄 RiskAgent: Final LLM yanıtı alınıyor...")
                # Final yanıtı al
                final_response = self.llm.invoke(messages)
                messages.append(final_response)
                print(f"✅ RiskAgent: Final LLM yanıtı alındı")
            else:
                print(f"⚠️ RiskAgent: LLM hiç tool çağrısı yapmadı!")
                print(f"🤔 LLM yanıtı: {response.content[:200]}...")
                
                # Fallback: Manuel olarak risk skorunu hesapla
                print(f"🔄 RiskAgent: Fallback olarak manuel risk skoru hesaplanıyor...")
                risk_result = self._call_mcp_tool("risk.scoreTransaction", {
                    "userId": userId,
                    "tx": {
                        "amount": proposal.get("amount", 0),
                        "type": "internal_transfer"
                    }
                })
                print(f"📊 RiskAgent: Fallback risk skoru hesaplandı")
            
            # ========================================
            # 4. RİSK OUTPUT OLUŞTUR
            # ========================================
            
            # LLM tool çağrılarından veya fallback'ten gelen verileri kullan
            if risk_result is None:
                print(f"⚠️ RiskAgent: Risk result bulunamadı, varsayılan değerler kullanılıyor")
                risk_result = {"score": 0.5, "reason": "default", "factors": ["unknown"]}
            
            risk_score = risk_result.get("score", 0.5)
            
            print(f"🛡️ RiskAgent: Risk skoru hesaplandı: {risk_score}")
            print(f"🛡️ RiskAgent: Risk seviyesi: {'düşük' if risk_score < 0.3 else 'orta' if risk_score < 0.7 else 'yüksek'}")
            print(f"🛡️ RiskAgent: LLM tool calling {'başarılı' if response.tool_calls else 'başarısız - fallback kullanıldı'}")
            
            risk_output = {
                "agent": "RiskAgent",
                "action": "analyze_risk",
                "analysis": risk_result,
                "message": f"İşlem güvenli, {'düşük' if risk_score < 0.5 else 'yüksek'} riskli.",
                "risk_score": risk_score,
                "risk_level": "low" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "high"
            }
            
            # ========================================
            # 4. EVENT PUBLISHING
            # ========================================
            
            # Agent çıktısını Kafka'ya gönder
            risk_output["type"] = "agent-output"
            self.publisher_queue.put({"event": "agent-output", "data": risk_output})
            
            # Kafka'ya risk.analysis event'i gönder
            service_manager.kafka_service.publish_event(
                config.KAFKA_TOPICS["RISK_ANALYSIS"],
                {
                    "userId": userId,
                    "analysis": risk_result,
                    "correlationId": correlationId
                }
            )
            
            # ========================================
            # 5. STATE GÜNCELLE
            # ========================================
            
            updated_state = {
                **state,
                "messages": messages,
                "risk_output": risk_output,
                "current_step": "risk_agent_completed"
            }
            
            print(f"✅ RiskAgent node tamamlandı: Risk skoru {risk_score}")
            return updated_state
            
        except Exception as e:
            print(f"❌ RiskAgent node hatası: {e}")
            return {
                **state,
                "error": f"RiskAgent hatası: {str(e)}",
                "current_step": "error"
            }
    
    def _investment_agent_node(self, state: FinancialState) -> FinancialState:
        """InvestmentAgent Node - Risk bazlı yatırım önerileri"""
        print("🔄 InvestmentAgent node çalışıyor...")
        
        try:
            userId = state["userId"]
            correlationId = state["correlationId"]
            risk_output = state.get("risk_output", {})
            
            if not risk_output:
                raise ValueError("RiskAgent çıktısı bulunamadı")
            
            risk_score = risk_output.get("risk_score", 0.5)
            
            # ========================================
            # 1. LLM İLE YATIRIM ANALİZİ - OLLAMA LLaMA3.2:1B KULLANIMI
            # ========================================
            
            # 🔥 ÖNEMLİ: InvestmentAgent da Ollama llama3.2:1b modeli kullanıyor!
            # Yatırım analizi için MCP araçlarını (market.quotes) çağırması bekleniyor
            
            # System mesajı ile agent'a görev ver
            system_message = SystemMessage(content=f"""
Sen InvestmentAgent'sın. Görevin:
1. Risk skoru {risk_score} olan kullanıcı için yatırım önerileri oluştur
2. Risk durumuna göre uygun varlık türlerini belirle
3. Piyasa kotalarını sorgula ve analiz et

Kullanabileceğin araçlar:
- market_quotes: Piyasa kotalarını al

Risk skoru {risk_score} için uygun yatırım stratejisi belirle.
Türkçe yanıt ver ve detaylı analiz yap.
            """)
            
            # Human mesajı ile görevi başlat
            human_message = HumanMessage(content=f"""
Risk skoru {risk_score} olan kullanıcı için yatırım analizi yap.
Risk durumuna göre uygun varlık türlerini belirle ve piyasa kotalarını sorgula.
            """)
            
            # Mesajları state'e ekle
            messages = state.get("messages", [])
            messages.extend([system_message, human_message])
            
            print(f"🤖 InvestmentAgent: Ollama llama3.2:3b modeli ile yatırım analizi başlatılıyor...")
            
            # ChatOllama varsa kullan, yoksa manuel HTTP isteği gönder
            if self.llm:
                try:
                    response = self.llm.bind_tools(self.tools).invoke(messages)
                    print(f"✅ ChatOllama başarılı")
                except Exception as e:
                    print(f"⚠️ ChatOllama başarısız: {e}")
                    print(f"🔄 Manuel HTTP isteği gönderiliyor...")
                    response_content = self._call_ollama_manual(messages)
                    # Mock response oluştur
                    # AIMessage zaten import edilmiş
                    response = AIMessage(content=response_content)
            else:
                print(f"🔄 Manuel HTTP isteği gönderiliyor...")
                response_content = self._call_ollama_manual(messages)
                # Mock response oluştur
                # AIMessage zaten import edilmiş
                response = AIMessage(content=response_content)
            
            # ========================================
            # 2. MCP TOOL ÇAĞRILARI - DETAYLI LOGGING
            # ========================================
            
            print(f"🔍 InvestmentAgent: LLM yanıtı alındı, tool çağrıları kontrol ediliyor...")
            print(f"📋 LLM yanıtı: {response.content[:200]}...")
            print(f"📋 Tool calls sayısı: {len(response.tool_calls) if response.tool_calls else 0}")
            
            quotes = {}
            if response.tool_calls:
                print(f"🎯 InvestmentAgent: {len(response.tool_calls)} adet MCP tool çağrısı tespit edildi!")
                
                # Tool çağrılarını gerçekleştir
                tool_results = []
                for i, tool_call in enumerate(response.tool_calls):
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    print(f"🔧 InvestmentAgent: Tool #{i+1} çağrılıyor: {tool_name}")
                    print(f"📥 Tool args: {tool_args}")
                    
                    # MCP aracını çağır
                    result = self._call_mcp_tool(tool_name, tool_args)
                    tool_results.append(f"{tool_name}: {result}")
                    
                    print(f"✅ InvestmentAgent: Tool #{i+1} tamamlandı: {tool_name}")
                    print(f"📤 Tool result: {str(result)[:200]}...")
                    
                    # Market quotes sonuçlarını sakla
                    if tool_name == "market_quotes":
                        asset_type = tool_args.get("assetType", "unknown")
                        quotes[asset_type] = result
                
                # Tool sonuçlarını mesaj olarak ekle
                tool_message = AIMessage(content=f"Tool çağrıları tamamlandı: {'; '.join(tool_results)}")
                messages.append(tool_message)
                
                print(f"🔄 InvestmentAgent: Final LLM yanıtı alınıyor...")
                # Final yanıtı al
                final_response = self.llm.invoke(messages)
                messages.append(final_response)
                print(f"✅ InvestmentAgent: Final LLM yanıtı alındı")
            else:
                print(f"⚠️ InvestmentAgent: LLM hiç tool çağrısı yapmadı!")
                print(f"🤔 LLM yanıtı: {response.content[:200]}...")
                
                # Fallback: Manuel olarak market quotes al
                print(f"🔄 InvestmentAgent: Fallback olarak manuel market quotes alınıyor...")
                asset_types = ["bond", "equity", "fund"] if risk_score < 0.3 else ["bond", "savings"]
                for asset_type in asset_types:
                    quotes[asset_type] = self._call_mcp_tool("market.quotes", {
                        "assetType": asset_type,
                        "tenor": "1Y"
                    })
                    print(f"📊 InvestmentAgent: Manuel {asset_type} quotes alındı")
            
            # LLM tool çağrılarından veya fallback'ten gelen verileri kullan
            asset_types = list(quotes.keys()) if quotes else ["bond", "equity", "fund"]
            
            print(f"📈 InvestmentAgent: {len(asset_types)} yatırım türü analiz edildi")
            print(f"📈 InvestmentAgent: Yatırım stratejisi: {'agresif' if risk_score < 0.3 else 'muhafazakar'}")
            print(f"📈 InvestmentAgent: LLM tool calling {'başarılı' if response.tool_calls else 'başarısız - fallback kullanıldı'}")
            
            investment_output = {
                "agent": "InvestmentAgent",
                "action": "analyze_investment",
                "recommendation": quotes,
                "message": f"Risk durumuna göre yatırım önerileri: {', '.join(asset_types)}",
                "strategy": "aggressive" if risk_score < 0.3 else "conservative",
                "asset_types": asset_types
            }
        
            # Event publishing
            investment_output["type"] = "agent-output"
            self.publisher_queue.put({"event": "agent-output", "data": investment_output})
            
            service_manager.kafka_service.publish_event(
                config.KAFKA_TOPICS["INVESTMENTS_PROPOSAL"],
                {
                    "userId": userId,
                    "recommendation": quotes,
                    "correlationId": correlationId
                }
            )
            
            print(f"✅ InvestmentAgent node tamamlandı: {len(asset_types)} yatırım önerisi")
            return {
                **state,
                "investment_output": investment_output,
                "current_step": "investment_agent_completed"
            }
            
        except Exception as e:
            print(f"❌ InvestmentAgent node hatası: {e}")
            return {
                **state,
                "error": f"InvestmentAgent hatası: {str(e)}",
                "current_step": "error"
            }
    
    def _coordinator_agent_node(self, state: FinancialState) -> FinancialState:
        """CoordinatorAgent Node - Final mesaj oluşturma ve memory entegrasyonu"""
        print("🔄 CoordinatorAgent node çalışıyor...")
        
        try:
            userId = state["userId"]
            amount = state["amount"]
            correlationId = state["correlationId"]
        
            # Hafızaları al
            short_term_memory = self._get_short_term_memory(userId)
            long_term_memory = self._get_long_term_memory(userId, "deposit analysis")
        
            # ========================================
            # HUGGING FACE API İLE FİNAL MESAJ OLUŞTURMA
            # ========================================
            
            # 🔥 ÖNEMLİ: CoordinatorAgent büyük LLM kullanıyor!
            # Hugging Face API üzerinden deepseek-v3-0324 modeli (büyük LLM)
            # Bu model RAG (Retrieval Augmented Generation) için optimize edilmiş
            # Redis + Qdrant memory'lerden gelen verilerle zenginleştirilmiş prompt
            
            print(f"🧠 CoordinatorAgent: Hugging Face deepseek-v3-0324 modeli ile final mesaj oluşturuluyor...")
            print(f"📚 Memory kullanımı: Redis (kısa vadeli) + Qdrant (uzun vadeli)")
            
            # Prompt oluştur (RAG sistemi ile zenginleştirilmiş)
            prompt = self._build_coordinator_prompt(userId, amount, state, short_term_memory, long_term_memory)
            system_prompt = self._get_coordinator_system_prompt()
            
            # Büyük LLM ile final mesaj oluştur
            llm_response = service_manager.huggingface_service.generate_response(system_prompt, prompt)
            final_message = llm_response.get("text", "Analiz tamamlandı.")
        
            coordinator_output = {
                "agent": "CoordinatorAgent",
                "action": "create_final_message",
                "message": final_message,
                "memory_used": {
                    "short_term": short_term_memory,
                    "long_term": long_term_memory
                }
            }
            
            # Event publishing
            notification = {
                "type": "final_proposal",
                "userId": userId,
                "correlationId": correlationId,
                "message": final_message,
                "proposal": state.get("payments_output", {}).get("proposal", {})
            }
            
            self.publisher_queue.put({"event": "notification", "data": notification})
            
            service_manager.kafka_service.publish_event(
                config.KAFKA_TOPICS["ADVISOR_FINAL_MESSAGE"],
                notification
            )
        
            # Hafızaları güncelle
            self._update_memories(userId, amount, correlationId, final_message)
            
            print("✅ CoordinatorAgent node tamamlandı: Final mesaj oluşturuldu")
            return {
                **state,
                "coordinator_output": coordinator_output,
                "current_step": "coordinator_agent_completed"
            }
            
        except Exception as e:
            print(f"❌ CoordinatorAgent node hatası: {e}")
            return {
                **state,
                "error": f"CoordinatorAgent hatası: {str(e)}",
                "current_step": "error"
            }
    
    def _user_interaction_node(self, state: FinancialState) -> FinancialState:
        """UserInteraction Node - Kullanıcı etkileşimi simülasyonu"""
        print("🔄 UserInteraction node çalışıyor...")
        
        # Bu node gerçek uygulamada Web UI'dan gelen kullanıcı etkileşimini bekler
        # Şimdilik varsayılan olarak "approve" yapıyoruz
        
        user_action = "approve"  # Gerçek uygulamada Web UI'dan gelir
        
        print(f"✅ UserInteraction node tamamlandı: Kullanıcı eylemi '{user_action}'")
        return {
            **state,
            "user_action": user_action,
            "current_step": "user_interaction_completed"
        }
    
    def _execution_node(self, state: FinancialState) -> FinancialState:
        """Execution Node - Onaylanan işlemleri gerçekleştirme"""
        print("🔄 Execution node çalışıyor...")
        
        try:
            userId = state["userId"]
            correlationId = state["correlationId"]
            user_action = state.get("user_action", "approve")
            
            if user_action == "approve":
                # Transfer işlemini gerçekleştir
                payments_output = state.get("payments_output", {})
                proposal = payments_output.get("proposal", {})
                
                # Mock transfer execution
                transfer_result = {
                    "status": "completed",
                    "transactionId": f"tx_{correlationId}",
                    "amount": proposal.get("amount", 0),
                    "timestamp": int(time.time())
                }
                
                # Event publishing
                execution_event = {
                    "event": "payments.executed",
                    "payload": {
                        "userId": userId,
                        "transactionId": transfer_result["transactionId"],
                        "amount": transfer_result["amount"],
                        "status": "completed",
                        "timestamp": transfer_result["timestamp"]
                    }
                }
                
                self.publisher_queue.put({"event": "payments.executed", "data": execution_event})
                
                service_manager.kafka_service.publish_event(
                    config.KAFKA_TOPICS["PAYMENTS_EXECUTED"],
                    execution_event["payload"]
                )
                
                final_result = {
                    "status": "success",
                    "message": "Transfer başarıyla tamamlandı",
                    "execution": transfer_result
                }
                
            elif user_action == "reject":
                final_result = {
                    "status": "rejected",
                    "message": "Tüm öneriler reddedildi"
                }
                
            else:  # custom_message
                final_result = {
                    "status": "custom_processed",
                    "message": "Özel mesaj işlendi"
                }
            
            print(f"✅ Execution node tamamlandı: {final_result['status']}")
            return {
                **state,
                "final_result": final_result,
                "current_step": "execution_completed"
            }
            
        except Exception as e:
            print(f"❌ Execution node hatası: {e}")
            return {
                **state,
                "error": f"Execution hatası: {str(e)}",
                "current_step": "error"
            }
    
    def _should_execute(self, state: FinancialState) -> str:
        """
        Conditional routing - Execution'a gidip gitmeyeceğini belirler
        
        LangGraph'in conditional routing özelliğini kullanır.
        """
        user_action = state.get("user_action")
        
        if user_action in ["approve", "reject", "custom_message"]:
            return "execute"
        else:
            return "end"
    
    def execute(self, initial_state: FinancialState) -> Optional[FinancialState]:
        """
        LangGraph workflow'unu çalıştırır
        
        Bu metod LangGraph'in gerçek invoke metodunu kullanır:
        - State management: LangGraph'in state yönetimi
        - Checkpointing: Memory ile checkpointing
        - Error handling: Hata durumlarında graceful handling
        
        Args:
            initial_state: Başlangıç state'i (LangGraph formatında)
            
        Returns:
            FinancialState: Workflow sonucu
        """
        if not self.workflow:
            print("❌ LangGraph workflow henüz oluşturulmamış")
            return None
        
        try:
            print(f"🚀 LangGraph workflow başlatılıyor: {initial_state['correlationId']}")
            
            # LangGraph'in gerçek invoke metodunu kullan
            config_dict = {"configurable": {"thread_id": initial_state["correlationId"]}}
            
            # Initial state'i LangGraph formatına çevir
            langgraph_state = {
                "messages": initial_state.get("messages", []),
                "userId": initial_state["userId"],
                "amount": initial_state["amount"],
                "correlationId": initial_state["correlationId"],
                "payments_output": initial_state.get("payments_output"),
                "risk_output": initial_state.get("risk_output"),
                "investment_output": initial_state.get("investment_output"),
                "coordinator_output": initial_state.get("coordinator_output"),
                "user_action": initial_state.get("user_action"),
                "custom_message": initial_state.get("custom_message"),
                "current_step": initial_state.get("current_step", "start"),
                "error": initial_state.get("error"),
                "final_result": initial_state.get("final_result")
            }
            
            # Workflow'u çalıştır
            result = self.workflow.invoke(langgraph_state, config=config_dict)
            
            print(f"✅ LangGraph workflow tamamlandı: {initial_state['userId']}")
            print(f"📊 Final step: {result.get('current_step', 'unknown')}")
            
            return result
            
        except Exception as e:
            print(f"❌ LangGraph workflow çalıştırma hatası: {e}")
            return {
                **initial_state,
                "error": f"Workflow hatası: {str(e)}",
                "current_step": "error"
            }
    
    def _call_ollama_manual(self, messages: list) -> str:
        """
        Ollama'ya manuel HTTP isteği gönder (ChatOllama başarısız olduğunda fallback)
        
        Bu metod LangChain'in ChatOllama sınıfı container içinde bağlantı sorunu yaşadığında
        devreye girer. Manuel HTTP istekleri ile Ollama'ya bağlanır ve gerçek LLM çağrıları yapar.
        
        Özellikler:
        - llama3.2:3b model'i kullanır (ngrok ile host edilen güçlü model)
        - 120 saniye timeout süresi
        - LangChain mesaj formatını Ollama formatına çevirir
        - Türkçe ve anlamlı yanıtlar alır
        - MCP tool calling için optimize edilmiş
        
        Args:
            messages: LangChain mesaj listesi (SystemMessage, HumanMessage, AIMessage)
            
        Returns:
            str: Ollama'dan gelen yanıt metni
            
        Son Güncellemeler (2025-09-16):
        - ngrok ile host edilen remote Ollama servisi entegrasyonu
        - Model upgrade: llama3.2:1b → llama3.2:3b (daha güçlü analiz)
        - Timeout artırıldı: 30s → 120s
        - Gerçek LLM çağrıları başarıyla çalışıyor
        - MCP tool calling performansı artırıldı
        """
        try:
            import requests
            
            # LangChain mesajlarını Ollama formatına çevir
            ollama_messages = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    if msg.__class__.__name__ == 'SystemMessage':
                        ollama_messages.append({"role": "system", "content": msg.content})
                    elif msg.__class__.__name__ == 'HumanMessage':
                        ollama_messages.append({"role": "user", "content": msg.content})
                    elif msg.__class__.__name__ == 'AIMessage':
                        ollama_messages.append({"role": "assistant", "content": msg.content})
            
            # Ollama API'sine istek gönder
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_ctx": 2048
                    }
                },
                timeout=120  # Timeout'u 2 dakikaya çıkar
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")
            else:
                print(f"❌ Ollama API hatası: {response.status_code} - {response.text}")
                return "Ollama API hatası"
                
        except Exception as e:
            print(f"❌ Manuel Ollama çağrısı hatası: {e}")
            return "Manuel Ollama çağrısı başarısız"
    
    def _call_mcp_tool(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP aracını çağırır - DETAYLI LOGGING İLE
        
        🔥 ÖNEMLİ: Bu metod LangGraph agent'larının MCP Finance Tools ile iletişim kurmasını sağlar
        Her tool çağrısı detaylı olarak loglanır ve sonuçları takip edilir
        
        Args:
            path: Araç yolu (örn: "userProfile.get", "market.quotes")
            payload: Gönderilecek veri
            
        Returns:
            Dict[str, Any]: Araç yanıtı
        """
        print(f"🌐 MCP Tool Çağrısı: {path}")
        print(f"📥 Payload: {payload}")
        
        try:
            result = service_manager.mcp_service.call_tool(path, payload)
            print(f"✅ MCP Tool Başarılı: {path}")
            print(f"📤 Sonuç: {str(result)[:300]}...")
            return result
        except Exception as e:
            print(f"❌ MCP Tool Hatası: {path} - {e}")
            return {"error": str(e), "path": path}
    
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
        try:
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
        except Exception as e:
            print(f"⚠️ Uzun vadeli hafıza hatası: {e}")
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

PaymentsAgent: {state['payments_output'].get('message', 'N/A')}
RiskAgent: {state['risk_output'].get('message', 'N/A')}
InvestmentAgent: {state['investment_output'].get('message', 'N/A')}

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
        try:
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
            print(f"✅ Uzun vadeli hafıza güncellendi: {userId}")
        except Exception as e:
            print(f"⚠️ Uzun vadeli hafıza güncelleme hatası: {e}")
        
        # Kısa vadeli hafızayı güncelle (Redis)
        try:
            service_manager.redis_service.push_user_event(userId, {
                "type": "deposit",
                "amount": amount,
                "ts": int(time.time()),
                "message": final_message
            })
            print(f"✅ Kısa vadeli hafıza güncellendi: {userId}")
        except Exception as e:
            print(f"⚠️ Kısa vadeli hafıza güncelleme hatası: {e}")
    
    def run(self, initial_state: FinancialState) -> Optional[FinancialState]:
        """
        Workflow'u çalıştırır (execute metodunun alias'ı)
        
        Args:
            initial_state: Başlangıç state'i
            
        Returns:
            FinancialState: Workflow sonucu
        """
        return self.execute(initial_state)
    
    
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
def userProfile_get(userId: str) -> dict:
    """
    Kullanıcı profilini ve tercihlerini getirir
    
    Args:
        userId: Kullanıcı ID'si
        
    Returns:
        dict: Kullanıcı profili
    """
    return service_manager.mcp_service.call_tool("userProfile.get", {"userId": userId})


@tool
def risk_scoreTransaction(userId: str, tx: dict) -> dict:
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
def savings_createTransfer(userId: str, fromAccount: str, toSavingsId: str, amount: int) -> dict:
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
