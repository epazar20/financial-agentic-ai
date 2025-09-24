import {useEffect, useState} from "react";

export default function Home(){
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [showChatPrompt, setShowChatPrompt] = useState(false);
  const [currentProposal, setCurrentProposal] = useState(null);
  const [showCustomMessageModal, setShowCustomMessageModal] = useState(false);
  const [customMessageInput, setCustomMessageInput] = useState("");
  const [currentEvent, setCurrentEvent] = useState(null);
  const [buttonsDisabled, setButtonsDisabled] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const [showToast, setShowToast] = useState(false);
  const [collapsedEvents, setCollapsedEvents] = useState(new Set());
  
  // Yeni event'ler geldiğinde otomatik olarak collapsed state'e ekle
  useEffect(() => {
    events.forEach(ev => {
      if (ev.type === 'agent-output' && ev.result?.result) {
        const eventId = `agent-result-${ev.correlationId}-${ev.timestamp}`;
        setCollapsedEvents(prev => new Set([...prev, eventId]));
      }
      if (['payments_output', 'risk_output', 'investment_output', 'final_proposal', 'chat-analysis', 'all-proposals-approved', 'all-proposals-rejected', 'final-result-report', 'approval-error', 'chat-sent', 'chat-error', 'agent-output'].includes(ev.type)) {
        const eventId = `event-${ev.correlationId}-${ev.timestamp}`;
        setCollapsedEvents(prev => new Set([...prev, eventId]));
      }
    });
  }, [events]);
  
  // Toast mesaj fonksiyonu
  const showToastMessage = (message) => {
    setToastMessage(message);
    setShowToast(true);
    setTimeout(() => {
      setShowToast(false);
    }, 3000);
  };

  // Collapse toggle fonksiyonu
  const toggleCollapse = (eventId) => {
    setCollapsedEvents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(eventId)) {
        newSet.delete(eventId);
      } else {
        newSet.add(eventId);
      }
      return newSet;
    });
  };
  
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
    es.addEventListener("all-proposals-approved", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>{
        // Duplicate event'leri engelle
        const uniqueKey = `${data.correlationId || 'unknown'}_${data.timestamp || Date.now()}_${data.type || 'all-proposals-approved'}`;
        const exists = ev.some(event => 
          `${event.correlationId || 'unknown'}_${event.timestamp || Date.now()}_${event.type || 'all-proposals-approved'}` === uniqueKey
        );
        if (exists) return ev;
        return [data, ...ev];
      });
    });
    es.addEventListener("all-proposals-rejected", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>{
        // Duplicate event'leri engelle
        const uniqueKey = `${data.correlationId || 'unknown'}_${data.timestamp || Date.now()}_${data.type || 'all-proposals-rejected'}`;
        const exists = ev.some(event => 
          `${event.correlationId || 'unknown'}_${event.timestamp || Date.now()}_${event.type || 'all-proposals-rejected'}` === uniqueKey
        );
        if (exists) return ev;
        return [data, ...ev];
      });
      // Red işlemi tamamlandığında butonları tekrar aktif et
      setButtonsDisabled(false);
    });
    es.addEventListener("final-result-report", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>{
        // Duplicate event'leri engelle
        const uniqueKey = `${data.correlationId || 'unknown'}_${data.timestamp || Date.now()}_${data.type || 'final-result-report'}`;
        const exists = ev.some(event => 
          `${event.correlationId || 'unknown'}_${event.timestamp || Date.now()}_${event.type || 'final-result-report'}` === uniqueKey
        );
        if (exists) return ev;
        return [data, ...ev];
      });
      // Final report geldiğinde loading'i kapat ve butonları tekrar aktif et
      setIsLoading(false);
      setButtonsDisabled(false);
    });
    es.addEventListener("agent-output", e=>{
      const data = JSON.parse(e.data);
      setEvents(ev=>{
        // Duplicate event'leri engelle
        const uniqueKey = `${data.correlationId || 'unknown'}_${data.timestamp || Date.now()}_${data.type || 'agent-output'}`;
        const exists = ev.some(event => 
          `${event.correlationId || 'unknown'}_${event.timestamp || Date.now()}_${event.type || 'agent-output'}` === uniqueKey
        );
        if (exists) return ev;
        return [data, ...ev];
      });
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
    // Evet butonuna tıklandığında CoordinatorAgent'e tüm önerileri analiz ettir
    setButtonsDisabled(true);
    setIsLoading(true);
    showToastMessage("🔄 İşlem başlatılıyor...");
    try {
      console.log("🚀 Evet butonuna tıklandı, tüm öneriler onaylanıyor...", item);
      
      const response = await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/approve_all_proposals", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        userId: item.userId || "web_ui_user",
          response: "approve_all",
        proposal: item.proposal || item,
          correlationId: item.correlationId || "corr-demo",
          originalMessage: item.message,
          allProposals: {
            payments: item.paymentsProposal || {amount: 7500, from: "CHK001", to: "SV001"},
            risk: item.riskProposal || {score: 0.05, reason: "low risk"},
            investment: item.investmentProposal || {type: "bond", rate: 0.28}
          }
      })
    });
      
      if (response.ok) {
        const result = await response.json();
        console.log("✅ Tüm öneriler onaylandı:", result);
        
        // approval-success event'i kaldırıldı - kafa karıştırıcıydı
        // setEvents(ev => [{
        //   type: 'approval-success',
        //   message: '✅ Onayınız alındı! Agent\'lar işlemlerinizi gerçekleştiriyor, lütfen bekleyin...',
        //   correlationId: item.correlationId || "corr-demo",
        //   timestamp: new Date().toISOString()
        // }, ...ev]);
        
      } else {
        console.error("❌ Onay işlemi başarısız:", response.statusText);
        
        // Hata mesajını events'e ekle
        setEvents(ev => [{
          type: 'approval-error',
          message: `Onay işlemi başarısız: ${response.statusText}`,
          correlationId: item.correlationId || "corr-demo",
          timestamp: new Date().toISOString()
        }, ...ev]);
      }
    } catch (error) {
      console.error("❌ Onay işlemi hatası:", error);
      
      // Hata mesajını events'e ekle
      setEvents(ev => [{
        type: 'approval-error',
        message: `Onay işlemi hatası: ${error.message}`,
        correlationId: item.correlationId || "corr-demo",
        timestamp: new Date().toISOString()
      }, ...ev]);
    } finally {
      // Loading'i final-result-report event'i kapatacak
      // setIsLoading(false);
    }
  };

  const reject = async (item) => {
    // Hayır butonuna tıklandığında tüm önerilerin reddedildiğini bildir
    // CoordinatorAgent'e yönlendirmeden basit red işlemi
    setButtonsDisabled(true);
    showToastMessage("❌ Tüm öneriler reddediliyor...");
    try {
      const response = await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/reject_all_proposals", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        userId: item.userId || "web_ui_user",
          response: "reject_all",
        proposal: item.proposal || item,
          correlationId: item.correlationId || "corr-demo",
          originalMessage: item.message
      })
    });
      
      if (response.ok) {
        const result = await response.json();
        console.log("Tüm öneriler reddedildi:", result);
      } else {
        console.error("Red işlemi başarısız:", response.statusText);
      }
    } catch (error) {
      console.error("Red işlemi hatası:", error);
    }
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

  // Özel mesaj modal'ını açma fonksiyonu
  const openCustomMessageModal = (event) => {
    console.log("🔍 Özel mesaj modal açılıyor:", event);
    setCurrentEvent(event);
    setShowCustomMessageModal(true);
    setCustomMessageInput("");
  };

  // Özel mesaj modal'ını kapatma fonksiyonu
  const closeCustomMessageModal = () => {
    setShowCustomMessageModal(false);
    setCurrentEvent(null);
    setCustomMessageInput("");
  };

  // Özel mesaj gönderme fonksiyonu
  const sendCustomMessage = async () => {
    if (!customMessageInput.trim() || !currentEvent) return;
    
    setButtonsDisabled(true);
    setIsLoading(true);
    showToastMessage("💬 Özel mesajınız işleniyor...");
    try {
      console.log("💬 Özel mesaj gönderiliyor:", customMessageInput.trim());
      console.log("📋 Event data:", currentEvent);
      
      const response = await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/chat_response", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          userId: currentEvent.userId || "web_ui_user",
          response: customMessageInput.trim(),
          proposal: currentEvent.proposal || currentEvent,
          correlationId: currentEvent.correlationId || "corr-demo",
          originalMessage: currentEvent.message,
          allProposals: {
            payments: currentEvent.paymentsProposal || {amount: 7500, from: "CHK001", to: "SV001"},
            risk: currentEvent.riskProposal || {score: 0.05, reason: "low risk"},
            investment: currentEvent.investmentProposal || {type: "bond", rate: 0.28}
          }
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log("✅ Özel mesaj gönderildi:", result);
        
        // Başarı mesajını events'e ekle
        setEvents(ev => [{
          type: 'chat-sent',
          message: `Özel mesajınız gönderildi: "${customMessageInput.trim()}"`,
          correlationId: currentEvent.correlationId || "corr-demo",
          timestamp: new Date().toISOString()
        }, ...ev]);
        
        // Modal'ı kapat
        closeCustomMessageModal();
        
      } else {
        console.error("❌ Özel mesaj gönderilemedi:", response.statusText);
        
        // Hata mesajını events'e ekle
        setEvents(ev => [{
          type: 'chat-error',
          message: `Özel mesaj gönderilemedi: ${response.statusText}`,
          correlationId: currentEvent.correlationId || "corr-demo",
          timestamp: new Date().toISOString()
        }, ...ev]);
      }
    } catch (error) {
      console.error("❌ Özel mesaj gönderme hatası:", error);
      
      // Hata mesajını events'e ekle
      setEvents(ev => [{
        type: 'chat-error',
        message: `Özel mesaj gönderme hatası: ${error.message}`,
        correlationId: currentEvent.correlationId || "corr-demo",
        timestamp: new Date().toISOString()
      }, ...ev]);
    } finally {
      setIsLoading(false);
    }
  };
  const sendChatResponseForProposal = async (event) => {
    if (!chatInput.trim()) return;
    
    setIsLoading(true);
    try {
      console.log("💬 Chat response gönderiliyor:", chatInput.trim());
      console.log("📋 Event data:", event);
      
      const response = await fetch((process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001") + "/chat_response", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          userId: event.userId || "web_ui_user",
          response: chatInput.trim(),
          proposal: event.proposal || event,
          correlationId: event.correlationId || "corr-demo",
          originalMessage: event.message,
          allProposals: {
            payments: event.paymentsProposal || {amount: 7500, from: "CHK001", to: "SV001"},
            risk: event.riskProposal || {score: 0.05, reason: "low risk"},
            investment: event.investmentProposal || {type: "bond", rate: 0.28}
          }
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log("✅ Chat response sent from proposal:", result);
        
        // Başarı mesajını events'e ekle
        setEvents(ev => [{
          type: 'chat-sent',
          message: `Mesajınız gönderildi: "${chatInput.trim()}"`,
          correlationId: event.correlationId || "corr-demo",
          timestamp: new Date().toISOString()
        }, ...ev]);
        
        setChatInput("");
      } else {
        console.error("❌ Failed to send chat response:", response.statusText);
        
        // Hata mesajını events'e ekle
        setEvents(ev => [{
          type: 'chat-error',
          message: `Mesaj gönderilemedi: ${response.statusText}`,
          correlationId: event.correlationId || "corr-demo",
          timestamp: new Date().toISOString()
        }, ...ev]);
      }
    } catch (error) {
      console.error("❌ Error sending chat response:", error);
      
      // Hata mesajını events'e ekle
      setEvents(ev => [{
        type: 'chat-error',
        message: `Mesaj gönderme hatası: ${error.message}`,
        correlationId: event.correlationId || "corr-demo",
        timestamp: new Date().toISOString()
      }, ...ev]);
    } finally {
      setIsLoading(false);
    }
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

                    {/* Action Buttons and Chat Input */}
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 20,
                      marginTop: 25
                    }}>
                      {/* Buttons Row */}
                      <div style={{
                        display: 'flex',
                        gap: 15,
                        justifyContent: 'center',
                        flexWrap: 'wrap'
                      }}>
                      <button 
                        onClick={() => approve(ev)}
                          disabled={buttonsDisabled}
                        style={{
                            padding: '12px 24px',
                            backgroundColor: buttonsDisabled ? '#6c757d' : '#28a745',
                          color: 'white',
                          border: 'none',
                            borderRadius: 8,
                            cursor: buttonsDisabled ? 'not-allowed' : 'pointer',
                            fontSize: '16px',
                            fontWeight: 'bold',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                            transition: 'all 0.3s ease',
                            opacity: buttonsDisabled ? 0.6 : 1
                          }}
                          onMouseOver={(e) => !buttonsDisabled && (e.target.style.backgroundColor = '#218838')}
                          onMouseOut={(e) => !buttonsDisabled && (e.target.style.backgroundColor = '#28a745')}
                      >
                        ✅ Evet (Onayla)
                      </button>
                        
                      <button 
                        onClick={() => reject(ev)}
                          disabled={buttonsDisabled}
                        style={{
                            padding: '12px 24px',
                            backgroundColor: buttonsDisabled ? '#6c757d' : '#dc3545',
                          color: 'white',
                          border: 'none',
                            borderRadius: 8,
                            cursor: buttonsDisabled ? 'not-allowed' : 'pointer',
                            fontSize: '16px',
                            fontWeight: 'bold',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                            transition: 'all 0.3s ease',
                            opacity: buttonsDisabled ? 0.6 : 1
                          }}
                          onMouseOver={(e) => !buttonsDisabled && (e.target.style.backgroundColor = '#c82333')}
                          onMouseOut={(e) => !buttonsDisabled && (e.target.style.backgroundColor = '#dc3545')}
                      >
                        ❌ Hayır (Reddet)
                      </button>
                        
                        <button 
                          onClick={() => openCustomMessageModal(ev)}
                          disabled={buttonsDisabled}
                          style={{
                            padding: '12px 24px',
                            backgroundColor: buttonsDisabled ? '#6c757d' : '#17a2b8',
                            color: 'white',
                            border: 'none',
                            borderRadius: 8,
                            cursor: buttonsDisabled ? 'not-allowed' : 'pointer',
                            fontSize: '16px',
                            fontWeight: 'bold',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                            transition: 'all 0.3s ease',
                            opacity: buttonsDisabled ? 0.6 : 1
                          }}
                          onMouseOver={(e) => !buttonsDisabled && (e.target.style.backgroundColor = '#138496')}
                          onMouseOut={(e) => !buttonsDisabled && (e.target.style.backgroundColor = '#17a2b8')}
                        >
                          💬 Özel Mesaj
                        </button>
                      </div>

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

                {/* All Proposals Approved Event */}
                {ev.type === 'all-proposals-approved' && (
                  <div style={{
                    backgroundColor: '#e8f5e8',
                    border: '2px solid #28a745',
                    borderRadius: 15,
                    padding: 20,
                    margin: '15px 0',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 15,
                      borderBottom: '2px solid #28a745',
                      paddingBottom: 10
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>✅</span>
                      <h3 style={{
                        color: '#2c5530',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        Tüm Öneriler Onaylandı ve İşlendi
                      </h3>
                    </div>

                    <div style={{marginBottom: 15}}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#2c5530'}}>
                        Onaylanan Agent'lar:
                      </p>
                      <div style={{
                        backgroundColor: 'white',
                        padding: 15,
                        borderRadius: 8,
                        border: '1px solid #ddd'
                      }}>
                        {ev.analysis?.approved_agents?.map((agent, index) => (
                          <div key={index} style={{
                            display: 'flex',
                            alignItems: 'center',
                            marginBottom: 8,
                            padding: 8,
                            backgroundColor: '#f8f9fa',
                            borderRadius: 5
                          }}>
                            <span style={{marginRight: 10}}>
                              {agent === 'PaymentsAgent' ? '💳' : 
                               agent === 'RiskAgent' ? '🛡️' : 
                               agent === 'InvestmentAgent' ? '📈' : '🤖'}
                            </span>
                            <span style={{fontWeight: 'bold'}}>{agent}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{marginBottom: 15}}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#2c5530'}}>
                        İşlem Sonuçları:
                      </p>
                      <div style={{
                        backgroundColor: 'white',
                        padding: 15,
                        borderRadius: 8,
                        border: '1px solid #ddd'
                      }}>
                        {ev.executionResults && Object.entries(ev.executionResults).map(([agent, result]) => (
                          <div key={agent} style={{
                            marginBottom: 10,
                            padding: 10,
                            backgroundColor: '#f8f9fa',
                            borderRadius: 5,
                            border: '1px solid #dee2e6'
                          }}>
                            <p style={{margin: '0 0 5px 0', fontWeight: 'bold', color: '#495057'}}>
                              {agent}: {result.action || 'İşlem tamamlandı'}
                            </p>
                            <p style={{margin: 0, fontSize: '14px', color: '#6c757d'}}>
                              {result.message || 'Başarıyla gerçekleştirildi'}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{
                      backgroundColor: '#d4edda',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #c3e6cb'
                    }}>
                      <p style={{margin: '0 0 8px 0', fontWeight: 'bold', color: '#155724'}}>
                        🎉 Başarı Mesajı:
                      </p>
                      <p style={{margin: 0, color: '#155724'}}>
                        Tüm finansal önerileriniz başarıyla gerçekleştirildi! 
                        Transfer işlemi, risk analizi ve yatırım tercihleriniz güncellendi.
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

                {/* All Proposals Rejected Event */}
                {ev.type === 'all-proposals-rejected' && (
                  <div style={{
                    backgroundColor: '#f8d7da',
                    border: '2px solid #dc3545',
                    borderRadius: 15,
                    padding: 20,
                    margin: '15px 0',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 15,
                      borderBottom: '2px solid #dc3545',
                      paddingBottom: 10
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>❌</span>
                      <h3 style={{
                        color: '#721c24',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        Tüm Öneriler Reddedildi
                      </h3>
                    </div>

                    <div style={{
                      backgroundColor: 'white',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #ddd',
                      marginBottom: 15
                    }}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#721c24'}}>
                        Red Durumu:
                      </p>
                      <p style={{margin: 0, color: '#6c757d'}}>
                        Kullanıcı tüm finansal önerileri reddetti. Hiçbir agent çalıştırılmadı.
                      </p>
                    </div>

                    <div style={{
                      backgroundColor: '#f8d7da',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #f5c6cb'
                    }}>
                      <p style={{margin: '0 0 8px 0', fontWeight: 'bold', color: '#721c24'}}>
                        ℹ️ Bilgi:
                      </p>
                      <p style={{margin: 0, color: '#721c24'}}>
                        Bu durumda CoordinatorAgent'e yönlendirme yapılmadı. 
                        Kullanıcı istediği zaman yeni öneriler talep edebilir.
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

                {/* Final Result Report Event */}
                {ev.type === 'final-result-report' && (
                  <div style={{
                    backgroundColor: '#e8f5e8',
                    border: '2px solid #28a745',
                    borderRadius: 15,
                    padding: 20,
                    margin: '15px 0',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 15,
                      borderBottom: '2px solid #28a745',
                      paddingBottom: 10
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>📊</span>
                      <h3 style={{
                        color: '#2c5530',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        CoordinatorAgent - Final Sonuç Raporu
                      </h3>
                    </div>

                    <div style={{marginBottom: 15}}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#2c5530'}}>
                        Genel Özet:
                      </p>
                      <div style={{
                        backgroundColor: 'white',
                        padding: 15,
                        borderRadius: 8,
                        border: '1px solid #ddd'
                      }}>
                        <p style={{margin: 0, color: '#6c757d'}}>
                          {ev.report?.summary || 'Rapor hazırlanıyor...'}
                        </p>
                      </div>
                    </div>

                    <div style={{marginBottom: 15}}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#2c5530'}}>
                        Başarılı İşlemler:
                      </p>
                      <div style={{
                        backgroundColor: 'white',
                        padding: 15,
                        borderRadius: 8,
                        border: '1px solid #ddd'
                      }}>
                        {ev.report?.successful_operations?.map((operation, index) => (
                          <div key={index} style={{
                            display: 'flex',
                            alignItems: 'center',
                            marginBottom: 8,
                            padding: 8,
                            backgroundColor: '#d4edda',
                            borderRadius: 5
                          }}>
                            <span style={{marginRight: 10}}>✅</span>
                            <span style={{fontWeight: 'bold', color: '#155724'}}>{operation}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {ev.report?.failed_operations && ev.report.failed_operations.length > 0 && (
                      <div style={{marginBottom: 15}}>
                        <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#721c24'}}>
                          Başarısız İşlemler:
                        </p>
                        <div style={{
                          backgroundColor: 'white',
                          padding: 15,
                          borderRadius: 8,
                          border: '1px solid #ddd'
                        }}>
                          {ev.report.failed_operations.map((operation, index) => (
                            <div key={index} style={{
                              display: 'flex',
                              alignItems: 'center',
                              marginBottom: 8,
                              padding: 8,
                              backgroundColor: '#f8d7da',
                              borderRadius: 5
                            }}>
                              <span style={{marginRight: 10}}>❌</span>
                              <span style={{fontWeight: 'bold', color: '#721c24'}}>{operation}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div style={{marginBottom: 15}}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#2c5530'}}>
                        Öneriler:
                      </p>
                      <div style={{
                        backgroundColor: 'white',
                        padding: 15,
                        borderRadius: 8,
                        border: '1px solid #ddd'
                      }}>
                        {ev.report?.recommendations?.map((recommendation, index) => (
                          <div key={index} style={{
                            display: 'flex',
                            alignItems: 'center',
                            marginBottom: 8,
                            padding: 8,
                            backgroundColor: '#e3f2fd',
                            borderRadius: 5
                          }}>
                            <span style={{marginRight: 10}}>💡</span>
                            <span style={{color: '#1976d2'}}>{recommendation}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div style={{
                      backgroundColor: '#d4edda',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #c3e6cb'
                    }}>
                      <p style={{margin: '0 0 8px 0', fontWeight: 'bold', color: '#155724'}}>
                        🎯 Sonraki Adımlar:
                      </p>
                      <ul style={{margin: 0, paddingLeft: 20, color: '#155724'}}>
                        {ev.report?.next_steps?.map((step, index) => (
                          <li key={index} style={{marginBottom: 5}}>{step}</li>
                        ))}
                      </ul>
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

                {/* Approval Success Event - Kaldırıldı */}
                {/* {ev.type === 'approval-success' && (
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
                      borderBottom: '2px solid #28a745',
                      paddingBottom: 10
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>🔄</span>
                      <h3 style={{
                        color: '#1565c0',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        İşlem Başlatıldı
                      </h3>
                    </div>

                    <div style={{
                      backgroundColor: 'white',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #ddd'
                    }}>
                      <p style={{margin: 0, color: '#155724', fontWeight: 'bold'}}>
                        {ev.message}
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
                      Timestamp: {ev.timestamp || 'N/A'}
                    </div>
                  </div>
                )} */}

                {/* Approval Error Event */}
                {ev.type === 'approval-error' && (
                  <div style={{
                    backgroundColor: '#f8d7da',
                    border: '2px solid #dc3545',
                    borderRadius: 15,
                    padding: 20,
                    margin: '15px 0',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 15,
                      borderBottom: '2px solid #dc3545',
                      paddingBottom: 10
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>❌</span>
                      <h3 style={{
                        color: '#721c24',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        Onay Hatası
                      </h3>
                    </div>

                    <div style={{
                      backgroundColor: 'white',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #ddd'
                    }}>
                      <p style={{margin: 0, color: '#721c24', fontWeight: 'bold'}}>
                        {ev.message}
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
                      Timestamp: {ev.timestamp || 'N/A'}
                    </div>
                  </div>
                )}

                {/* Chat Sent Event */}
                {ev.type === 'chat-sent' && (
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
                      <span style={{fontSize: '24px', marginRight: 10}}>💬</span>
                      <h3 style={{
                        color: '#1976d2',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        Mesaj Gönderildi
                      </h3>
                    </div>

                    <div style={{
                      backgroundColor: 'white',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #ddd'
                    }}>
                      <p style={{margin: 0, color: '#1976d2', fontWeight: 'bold'}}>
                        {ev.message}
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
                      Timestamp: {ev.timestamp || 'N/A'}
                    </div>
                  </div>
                )}

                {/* Chat Error Event */}
                {ev.type === 'chat-error' && (
                  <div style={{
                    backgroundColor: '#f8d7da',
                    border: '2px solid #dc3545',
                    borderRadius: 15,
                    padding: 20,
                    margin: '15px 0',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 15,
                      borderBottom: '2px solid #dc3545',
                      paddingBottom: 10
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>❌</span>
                      <h3 style={{
                        color: '#721c24',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        Mesaj Hatası
                      </h3>
                    </div>

                    <div style={{
                      backgroundColor: 'white',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #ddd'
                    }}>
                      <p style={{margin: 0, color: '#721c24', fontWeight: 'bold'}}>
                        {ev.message}
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
                      Timestamp: {ev.timestamp || 'N/A'}
                    </div>
                  </div>
                )}

                {/* Agent Output Event */}
                {ev.type === 'agent-output' && (
                  <div style={{
                    backgroundColor: '#fff3cd',
                    border: '2px solid #ffc107',
                    borderRadius: 15,
                    padding: 20,
                    margin: '15px 0',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 15,
                      borderBottom: '2px solid #ffc107',
                      paddingBottom: 10
                    }}>
                      <span style={{fontSize: '24px', marginRight: 10}}>
                        {ev.agent === 'PaymentsAgent' ? '💳' : 
                         ev.agent === 'RiskAgent' ? '🛡️' : 
                         ev.agent === 'InvestmentAgent' ? '📈' : '🤖'}
                      </span>
                      <h3 style={{
                        color: '#856404',
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 'bold'
                      }}>
                        {ev.agent} - {ev.action}
                      </h3>
                    </div>

                    <div style={{
                      backgroundColor: 'white',
                      padding: 15,
                      borderRadius: 8,
                      border: '1px solid #ddd',
                      marginBottom: 15
                    }}>
                      <p style={{margin: '0 0 10px 0', fontWeight: 'bold', color: '#856404'}}>
                        İşlem Sonucu:
                      </p>
                      <p style={{margin: 0, color: '#6c757d'}}>
                        {ev.result?.message || 'İşlem tamamlandı'}
                      </p>
                    </div>

                    {ev.result?.result && (
                      <div style={{
                        backgroundColor: '#f8f9fa',
                        padding: 15,
                        borderRadius: 8,
                        border: '1px solid #dee2e6'
                      }}>
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          marginBottom: 10,
                          cursor: 'pointer'
                        }}
                        onClick={() => toggleCollapse(`agent-result-${ev.correlationId}-${ev.timestamp}`)}>
                          <p style={{margin: 0, fontWeight: 'bold', color: '#495057'}}>
                            📋 Detaylar:
                          </p>
                          <span style={{
                            fontSize: '16px',
                            color: '#6c757d',
                            transition: 'transform 0.3s ease'
                          }}>
                            {collapsedEvents.has(`agent-result-${ev.correlationId}-${ev.timestamp}`) ? '▶️' : '🔽'}
                          </span>
                        </div>
                        
                        {!collapsedEvents.has(`agent-result-${ev.correlationId}-${ev.timestamp}`) && (
                          <pre style={{
                            margin: 0,
                            fontSize: '12px',
                            color: '#6c757d',
                            whiteSpace: 'pre-wrap',
                            backgroundColor: 'white',
                            padding: 10,
                            borderRadius: 5,
                            border: '1px solid #ddd'
                          }}>
                            {JSON.stringify(ev.result.result, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}

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

                {/* Genel event gösterimi - Sadece bilinen event'leri göster */}
                {['payments_output', 'risk_output', 'investment_output', 'final_proposal', 'chat-analysis', 'all-proposals-approved', 'all-proposals-rejected', 'final-result-report', 'approval-error', 'chat-sent', 'chat-error', 'agent-output'].includes(ev.type) && (
                  <div style={{
                    backgroundColor: '#f8f9fa',
                    padding: 15,
                    borderRadius: 8,
                    border: '1px solid #dee2e6',
                    marginTop: 10
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: 10,
                      cursor: 'pointer'
                    }}
                    onClick={() => toggleCollapse(`event-${ev.correlationId}-${ev.timestamp}`)}>
                      <h4 style={{margin: 0, color: '#495057'}}>📋 Event: {ev.type || 'Unknown'}</h4>
                      <span style={{
                        fontSize: '16px',
                        color: '#6c757d',
                        transition: 'transform 0.3s ease'
                      }}>
                        {collapsedEvents.has(`event-${ev.correlationId}-${ev.timestamp}`) ? '▶️' : '🔽'}
                      </span>
                    </div>
                    
                    {!collapsedEvents.has(`event-${ev.correlationId}-${ev.timestamp}`) && (
                    <pre style={{whiteSpace: 'pre-wrap', fontSize: '12px', backgroundColor: '#f1f1f1', padding: 10, borderRadius: 4}}>
                      {JSON.stringify(ev, null, 2)}
                    </pre>
                    )}
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

      {/* Özel Mesaj Modal */}
      {showCustomMessageModal && (
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
              color: '#17a2b8',
              fontSize: '20px',
              textAlign: 'center'
            }}>
              💬 Özel Mesajınızı Yazın
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
                {currentEvent?.message?.substring(0, 200)}...
              </p>
            </div>

            <div style={{marginBottom: 20}}>
              <label style={{
                display: 'block',
                marginBottom: 8,
                fontWeight: 'bold',
                color: '#495057'
              }}>
                Özel Mesajınız:
              </label>
              <textarea
                value={customMessageInput}
                onChange={(e) => setCustomMessageInput(e.target.value)}
                placeholder="Örneğin: 'Sadece tahvil yatırımı yapmak istiyorum' veya 'Miktarı 5000₺ olarak değiştir'..."
                style={{
                  width: '100%',
                  height: 120,
                  padding: 12,
                  border: '2px solid #17a2b8',
                  borderRadius: 8,
                  fontSize: '14px',
                  fontFamily: 'Arial, sans-serif',
                  resize: 'vertical',
                  boxSizing: 'border-box'
                }}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && e.ctrlKey) {
                    sendCustomMessage();
                  }
                }}
              />
            </div>

            <div style={{
              display: 'flex',
              gap: 10,
              justifyContent: 'center'
            }}>
              <button
                onClick={sendCustomMessage}
                disabled={!customMessageInput.trim() || isLoading}
                style={{
                  padding: '12px 24px',
                  backgroundColor: customMessageInput.trim() && !isLoading ? '#17a2b8' : '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: 8,
                  cursor: customMessageInput.trim() && !isLoading ? 'pointer' : 'not-allowed',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}
              >
                {isLoading ? '⏳' : '📤'} Gönder
              </button>
              
              <button
                onClick={closeCustomMessageModal}
                style={{
                  padding: '12px 24px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: 8,
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}
              >
                ❌ İptal
              </button>
            </div>

            <p style={{
              fontSize: '12px',
              color: '#6c757d',
              margin: '15px 0 0 0',
              textAlign: 'center',
              fontStyle: 'italic'
            }}>
              💡 İpucu: Ctrl+Enter ile hızlı gönderim yapabilirsiniz
            </p>
          </div>
        </div>
      )}

      {/* Toast Mesaj */}
      {showToast && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          backgroundColor: '#28a745',
          color: 'white',
          padding: '15px 20px',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          zIndex: 9999,
          fontSize: '16px',
          fontWeight: 'bold',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          animation: 'slideInRight 0.3s ease-out',
          maxWidth: '300px'
        }}>
          <span style={{fontSize: '20px'}}>🔔</span>
          {toastMessage}
        </div>
      )}

      <style jsx>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}