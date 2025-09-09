import {useEffect, useState} from "react";

export default function Home(){
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
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
                  <div>
                    <h3 style={{color: '#6f42c1', margin: '0 0 10px 0'}}>🎯 CoordinatorAgent - Final Mesaj</h3>
                    <div style={{whiteSpace: 'pre-wrap', marginBottom: 15}}>{ev.message}</div>
                    <div style={{display: 'flex', gap: 10}}>
                      <button 
                        onClick={() => approve(ev)}
                        style={{
                          padding: '8px 16px',
                          backgroundColor: '#28a745',
                          color: 'white',
                          border: 'none',
                          borderRadius: 5,
                          cursor: 'pointer'
                        }}
                      >
                        ✅ Evet (Onayla)
                      </button>
                      <button 
                        onClick={() => reject(ev)}
                        style={{
                          padding: '8px 16px',
                          backgroundColor: '#dc3545',
                          color: 'white',
                          border: 'none',
                          borderRadius: 5,
                          cursor: 'pointer'
                        }}
                      >
                        ❌ Hayır (Reddet)
                      </button>
                    </div>
                  </div>
                )}
                
                {/* Genel event gösterimi */}
                {!['payments_output', 'risk_output', 'investment_output', 'final_proposal'].includes(ev.type) && (
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
    </div>
  );
}