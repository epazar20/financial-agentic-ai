import {useEffect, useState} from "react";

export default function Home(){
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [showChatPrompt, setShowChatPrompt] = useState(false);
  const [currentProposal, setCurrentProposal] = useState(null);
  
  useEffect(()=>{
    const es = new EventSource(process.env.NEXT_PUBLIC_STREAM_URL || "http://localhost:5001/stream");
    es.addEventListener("notification", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>[data,...ev]);
    });
    es.addEventListener("agent-output", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>[data,...ev]);
    });
    es.addEventListener("execution", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>[data,...ev]);
    });
    es.addEventListener("message", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>[data,...ev]);
    });
    es.addEventListener("chat-analysis", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>[data,...ev]);
    });
    return ()=> es.close();
  },[]);

  // PRD_DEPOSIT.md senaryosuna göre maaş yatışı tetikleyici
  const triggerDeposit = async (amount) => {
    setIsLoading(true);
    try {
      const response = await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/simulate_deposit", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          user_id: "web_ui_user",
          amount: amount,
          correlation_id: `web_ui_${Date.now()}`
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log("Deposit triggered:", result);
      } else {
        console.error("Failed to trigger deposit:", response.statusText);
      }
    } catch (error) {
      console.error("Error triggering deposit:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Kafka publish ile maaş yatışı tetikleyici
  const triggerKafkaDeposit = async (amount) => {
    setIsLoading(true);
    try {
      const response = await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/kafka/publish", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          topic: "transactions.deposit",
          data: {
            payload: {
              userId: "web_ui_user",
              amount: amount
            },
            meta: {
              correlationId: `kafka_web_ui_${Date.now()}`,
              timestamp: new Date().toISOString()
            }
          }
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log("Kafka deposit triggered:", result);
      } else {
        console.error("Failed to trigger Kafka deposit:", response.statusText);
      }
    } catch (error) {
      console.error("Error triggering Kafka deposit:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const approve = async (item) => {
    await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/action", {
      method:"POST", 
      headers: {"Content-Type":"application/json"}, 
      body: JSON.stringify({
        userId: item.userId || "web_ui_user",
        response: "approve",
        proposal: item.proposal || item,
        correlationId: item.correlationId || "corr-demo"
      })
    });
  };

  const reject = async (item) => {
    await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/action", {
      method:"POST", 
      headers: {"Content-Type":"application/json"}, 
      body: JSON.stringify({
        userId: item.userId || "web_ui_user",
        response: "reject",
        proposal: item.proposal || item,
        correlationId: item.correlationId || "corr-demo"
      })
    });
  };

  // Chat prompt alanını açma fonksiyonu
  const openChatPrompt = (proposal) => {
    setCurrentProposal(proposal);
    setShowChatPrompt(true);
  };

  // Chat prompt gönderme fonksiyonu
  const sendChatResponse = async () => {
    if (!chatInput.trim() || !currentProposal) return;
    
    setIsLoading(true);
    try {
      const response = await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/chat_response", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          userId: currentProposal.userId || "web_ui_user",
          response: chatInput.trim(),
          proposal: currentProposal.proposal || currentProposal,
          correlationId: currentProposal.correlationId || "corr-demo",
          originalMessage: currentProposal.message
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log("Chat response sent:", result);
        setChatInput("");
        setShowChatPrompt(false);
        setCurrentProposal(null);
      } else {
        console.error("Failed to send chat response:", response.statusText);
      }
    } catch (error) {
      console.error("Error sending chat response:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Chat prompt kapatma fonksiyonu
  const closeChatPrompt = () => {
    setShowChatPrompt(false);
    setCurrentProposal(null);
    setChatInput("");
  };

  return (
    <div style={{padding: 20, fontFamily: 'Arial, sans-serif'}}>
      <h1>🏦 Finansal Agentic Proje - Maaş Yatış Senaryosu</h1>
      
      {/* PRD_DEPOSIT.md senaryosuna göre tetikleyici butonlar */}
      <div style={{marginBottom: 30, padding: 20, border: '2px solid #007bff', borderRadius: 10, backgroundColor: '#f8f9fa'}}>
        <h2>💰 Maaş Yatış Senaryosu Tetikleyicileri</h2>
        <p>PRD_DEPOSIT.md senaryosuna göre maaş yatışını simüle edin:</p>
        
        <div style={{display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 15}}>
          <button 
            onClick={() => triggerDeposit(25000)} 
            disabled={isLoading}
            style={{
              padding: '10px 20px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: 5,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.6 : 1
            }}
          >
            {isLoading ? '⏳ İşleniyor...' : '💳 25.000₺ Maaş Yatışı (API)'}
          </button>
          
          <button 
            onClick={() => triggerKafkaDeposit(25000)} 
            disabled={isLoading}
            style={{
              padding: '10px 20px',
              backgroundColor: '#17a2b8',
              color: 'white',
              border: 'none',
              borderRadius: 5,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.6 : 1
            }}
          >
            {isLoading ? '⏳ İşleniyor...' : '📨 25.000₺ Maaş Yatışı (Kafka)'}
          </button>
          
          <button 
            onClick={() => triggerDeposit(30000)} 
            disabled={isLoading}
            style={{
              padding: '10px 20px',
              backgroundColor: '#ffc107',
              color: 'black',
              border: 'none',
              borderRadius: 5,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.6 : 1
            }}
          >
            {isLoading ? '⏳ İşleniyor...' : '💎 30.000₺ Maaş Yatışı'}
          </button>
        </div>
        
        <p style={{fontSize: '14px', color: '#666'}}>
          <strong>Senaryo:</strong> Maaş yatışı → PaymentsAgent (tasarruf önerisi) → RiskAgent (risk analizi) → InvestmentAgent (yatırım önerileri) → CoordinatorAgent (final mesaj)
        </p>
      </div>

      {/* PRD_DEPOSIT.md senaryosuna göre bildirim kartları */}
      <div>
        <h2>📱 Real-time Bildirimler</h2>
        <p>Agent'ların çıktıları ve kullanıcı etkileşimleri:</p>
        
        {events.length === 0 ? (
          <div style={{padding: 20, textAlign: 'center', color: '#666'}}>
            <p>Henüz bildirim yok. Yukarıdaki butonlardan birini tıklayarak maaş yatış senaryosunu başlatın.</p>
          </div>
        ) : (
          <div>
            {events.map((ev, idx) => (
              <div key={idx} style={{
                border: '1px solid #ddd', 
                padding: 15, 
                margin: 10, 
                borderRadius: 8,
                backgroundColor: ev.type === 'final_proposal' ? '#e8f5e8' : '#f8f9fa'
              }}>
                {/* PRD_DEPOSIT.md senaryosuna göre bildirim formatı */}
                {ev.type === 'payments_output' && (
                  <div>
                    <h3 style={{color: '#007bff', margin: '0 0 10px 0'}}>💳 PaymentsAgent</h3>
                    <p><strong>Maaş Yatışı:</strong> {ev.amount}₺</p>
                    <p><strong>Tasarruf Önerisi:</strong> {ev.transferAmount}₺</p>
                  </div>
                )}
                
                {ev.type === 'risk_output' && (
                  <div>
                    <h3 style={{color: '#dc3545', margin: '0 0 10px 0'}}>🛡️ RiskAgent</h3>
                    <p><strong>Risk Skoru:</strong> {ev.riskScore}</p>
                    <p><strong>Durum:</strong> {ev.riskScore < 0.1 ? '✅ Düşük Risk' : '⚠️ Yüksek Risk'}</p>
                  </div>
                )}
                
                {ev.type === 'investment_output' && (
                  <div>
                    <h3 style={{color: '#28a745', margin: '0 0 10px 0'}}>📈 InvestmentAgent</h3>
                    <p><strong>Yatırım Önerileri:</strong></p>
                    <ul>
                      {ev.investments?.map((inv, i) => (
                        <li key={i}>{inv.type}: {inv.return}% getiri</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {ev.type === 'final_proposal' && (
                  <div style={{
                    backgroundColor: '#e8f5e8',
                    border: '2px solid #28a745',
                    borderRadius: 15,
                    padding: 25,
                    margin: '15px 0',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    {/* Header */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 20,
                      borderBottom: '2px solid #28a745',
                      paddingBottom: 15
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>⭐</span>
                      <span style={{fontSize: '24px', marginRight: 15}}>🔄</span>
                      <h3 style={{
                        color: '#2c5530',
                        margin: 0,
                        fontSize: '20px',
                        fontWeight: 'bold'
                      }}>
                        CoordinatorAgent - Final Mesaj
                      </h3>
                    </div>

                    {/* Greeting */}
                    <div style={{marginBottom: 20}}>
                      <p style={{fontSize: '18px', margin: '0 0 10px 0', fontWeight: 'bold'}}>
                        Merhaba! 👋
                      </p>
                    </div>

                    {/* Message Content */}
                    <div style={{
                      backgroundColor: 'white',
                      padding: 20,
                      borderRadius: 10,
                      marginBottom: 20,
                      border: '1px solid #ddd'
                    }}>
                      <div style={{whiteSpace: 'pre-wrap', lineHeight: '1.6', fontSize: '16px'}}>
                        {ev.message}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div style={{
                      display: 'flex',
                      gap: 15,
                      justifyContent: 'center',
                      marginTop: 25
                    }}>
                      <button 
                        onClick={() => approve(ev)}
                        style={{
                          padding: '12px 24px',
                          backgroundColor: '#28a745',
                          color: 'white',
                          border: 'none',
                          borderRadius: 8,
                          cursor: 'pointer',
                          fontSize: '16px',
                          fontWeight: 'bold',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseOver={(e) => e.target.style.backgroundColor = '#218838'}
                        onMouseOut={(e) => e.target.style.backgroundColor = '#28a745'}
                      >
                        ✅ Evet (Onayla)
                      </button>
                      
                      <button 
                        onClick={() => reject(ev)}
                        style={{
                          padding: '12px 24px',
                          backgroundColor: '#dc3545',
                          color: 'white',
                          border: 'none',
                          borderRadius: 8,
                          cursor: 'pointer',
                          fontSize: '16px',
                          fontWeight: 'bold',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseOver={(e) => e.target.style.backgroundColor = '#c82333'}
                        onMouseOut={(e) => e.target.style.backgroundColor = '#dc3545'}
                      >
                        ❌ Hayır (Reddet)
                      </button>

                      <button 
                        onClick={() => openChatPrompt(ev)}
                        style={{
                          padding: '12px 24px',
                          backgroundColor: '#17a2b8',
                          color: 'white',
                          border: 'none',
                          borderRadius: 8,
                          cursor: 'pointer',
                          fontSize: '16px',
                          fontWeight: 'bold',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseOver={(e) => e.target.style.backgroundColor = '#138496'}
                        onMouseOut={(e) => e.target.style.backgroundColor = '#17a2b8'}
                      >
                        💬 Özel Cevap
                      </button>
                    </div>

                    {/* Footer */}
                    <div style={{
                      fontSize: '12px',
                      color: '#666',
                      marginTop: 20,
                      textAlign: 'center',
                      borderTop: '1px solid #ddd',
                      paddingTop: 15
                    }}>
                      Correlation ID: {ev.correlationId || 'N/A'} | 
                      Timestamp: {ev.timestamp || new Date().toISOString()}
                    </div>
                  </div>
                )}
                
                {/* Chat Analysis Event */}
                {ev.type === 'chat-analysis' && (
                  <div style={{
                    backgroundColor: '#e3f2fd',
                    border: '2px solid #2196f3',
                    borderRadius: 15,
                    padding: 20,
                    margin: '15px 0',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 15,
                      borderBottom: '2px solid #2196f3',
                      paddingBottom: 10
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>🤖</span>
                      <h3 style={{
                        color: '#1976d2',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        AI Analiz Sonucu
                      </h3>
                    </div>

                    <div style={{marginBottom: 15}}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#1976d2'}}>
                        Kullanıcı Cevabı:
                      </p>
                      <p style={{
                        backgroundColor: 'white',
                        padding: 10,
                        borderRadius: 8,
                        border: '1px solid #ddd',
                        fontStyle: 'italic'
                      }}>
                        "{ev.userResponse}"
                      </p>
                    </div>

                    <div style={{marginBottom: 15}}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#1976d2'}}>
                        AI Analizi:
                      </p>
                      <div style={{
                        backgroundColor: 'white',
                        padding: 15,
                        borderRadius: 8,
                        border: '1px solid #ddd'
                      }}>
                        <p style={{margin: '0 0 8px 0'}}>
                          <strong>Agent:</strong> {ev.analysis?.intent || 'Unknown'}
                        </p>
                        <p style={{margin: '0 0 8px 0'}}>
                          <strong>Güven:</strong> {ev.analysis?.confidence ? `${(ev.analysis.confidence * 100).toFixed(1)}%` : 'N/A'}
                        </p>
                        <p style={{margin: '0 0 8px 0'}}>
                          <strong>Neden:</strong> {ev.analysis?.reasoning || 'N/A'}
                        </p>
                        <p style={{margin: 0}}>
                          <strong>Eylem:</strong> {ev.agentAction?.action || 'N/A'}
                        </p>
                      </div>
                    </div>

                    <div style={{
                      backgroundColor: '#f8f9fa',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #dee2e6'
                    }}>
                      <p style={{margin: '0 0 8px 0', fontWeight: 'bold', color: '#495057'}}>
                        Agent Mesajı:
                      </p>
                      <p style={{margin: 0, color: '#6c757d'}}>
                        {ev.agentAction?.message || 'İşlem tamamlandı.'}
                      </p>
                    </div>

                    <div style={{
                      fontSize: '12px',
                      color: '#666',
                      marginTop: 15,
                      textAlign: 'center',
                      borderTop: '1px solid #ddd',
                      paddingTop: 10
                    }}>
                      Correlation ID: {ev.correlationId || 'N/A'} | 
                      Timestamp: {ev.timestamp ? new Date(ev.timestamp * 1000).toISOString() : 'N/A'}
                    </div>
                  </div>
                )}

                {/* Genel event gösterimi */}
                {!['payments_output', 'risk_output', 'investment_output', 'final_proposal', 'chat-analysis'].includes(ev.type) && (
                  <div>
                    <h4 style={{margin: '0 0 10px 0'}}>📋 Event: {ev.type || 'Unknown'}</h4>
                    <pre style={{whiteSpace: 'pre-wrap', fontSize: '12px', backgroundColor: '#f1f1f1', padding: 10, borderRadius: 4}}>
                      {JSON.stringify(ev, null, 2)}
                    </pre>
                  </div>
                )}
                
                <div style={{fontSize: '12px', color: '#666', marginTop: 10}}>
                  Correlation ID: {ev.correlationId || 'N/A'} | 
                  Timestamp: {ev.timestamp || new Date().toISOString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chat Prompt Modal */}
      {showChatPrompt && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: 30,
            borderRadius: 15,
            width: '90%',
            maxWidth: 600,
            boxShadow: '0 10px 30px rgba(0,0,0,0.3)'
          }}>
            <h3 style={{
              margin: '0 0 20px 0',
              color: '#2c5530',
              fontSize: '20px',
              textAlign: 'center'
            }}>
              💬 Özel Cevap Gönder
            </h3>
            
            <div style={{
              backgroundColor: '#f8f9fa',
              padding: 15,
              borderRadius: 8,
              marginBottom: 20,
              border: '1px solid #dee2e6'
            }}>
              <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#495057'}}>
                Mevcut Öneri:
              </p>
              <p style={{margin: 0, fontSize: '14px', color: '#6c757d'}}>
                {currentProposal?.message?.substring(0, 200)}...
              </p>
            </div>

            <div style={{marginBottom: 20}}>
              <label style={{
                display: 'block',
                marginBottom: 8,
                fontWeight: 'bold',
                color: '#495057'
              }}>
                Cevabınız:
              </label>
              <textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Örneğin: 'Sadece tahvil yatırımı yapmak istiyorum' veya 'Miktarı 5000₺ olarak değiştir'..."
                style={{
                  width: '100%',
                  height: 120,
                  padding: 12,
                  border: '2px solid #dee2e6',
                  borderRadius: 8,
                  fontSize: '16px',
                  fontFamily: 'Arial, sans-serif',
                  resize: 'vertical',
                  boxSizing: 'border-box'
                }}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && e.ctrlKey) {
                    sendChatResponse();
                  }
                }}
              />
              <p style={{
                fontSize: '12px',
                color: '#6c757d',
                margin: '5px 0 0 0'
              }}>
                💡 İpucu: Ctrl+Enter ile gönderebilirsiniz
              </p>
            </div>

            <div style={{
              display: 'flex',
              gap: 15,
              justifyContent: 'center'
            }}>
              <button
                onClick={sendChatResponse}
                disabled={!chatInput.trim() || isLoading}
                style={{
                  padding: '12px 24px',
                  backgroundColor: chatInput.trim() && !isLoading ? '#28a745' : '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: 8,
                  cursor: chatInput.trim() && !isLoading ? 'pointer' : 'not-allowed',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all 0.3s ease'
                }}
              >
                {isLoading ? '⏳ Gönderiliyor...' : '📤 Gönder'}
              </button>
              
              <button
                onClick={closeChatPrompt}
                disabled={isLoading}
                style={{
                  padding: '12px 24px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: 8,
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  transition: 'all 0.3s ease'
                }}
              >
                ❌ İptal
              </button>
            </div>

            <div style={{
              marginTop: 20,
              padding: 15,
              backgroundColor: '#e3f2fd',
              borderRadius: 8,
              border: '1px solid #2196f3'
            }}>
              <p style={{
                margin: 0,
                fontSize: '14px',
                color: '#1976d2',
                fontWeight: 'bold'
              }}>
                🤖 AI Analizi:
              </p>
              <p style={{
                margin: '5px 0 0 0',
                fontSize: '13px',
                color: '#1976d2'
              }}>
                Cevabınız CoordinatorAgent tarafından analiz edilecek ve uygun agent'lara yönlendirilecektir.
                Örneğin: "tahvil" → InvestmentAgent, "miktar değiştir" → PaymentsAgent
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}