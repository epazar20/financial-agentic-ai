const express = require('express');
const bodyParser = require('body-parser');
const app = express();
app.use(bodyParser.json());
const PORT = process.env.PORT || 4000;

// Mock data store for demonstration
const mockData = {
  users: {
    'web_ui_user': {
      profile: {
        userId: 'web_ui_user',
        name: 'Demo User',
        riskProfile: 'conservative',
        preferences: {
          autoSavingsRate: 0.30,
          preferredInvestments: ['bond', 'fund'],
          riskTolerance: 'low'
        }
      },
      accounts: {
        checking: { id: 'CHK001', balance: 50000, type: 'checking' },
        savings: { id: 'SV001', balance: 15000, type: 'savings' },
        investment: { id: 'INV001', balance: 25000, type: 'investment' }
      },
      transactions: [
        { id: 'tx1001', amount: 25000, type: 'salary_deposit', timestamp: Date.now(), merchant: 'Employer' },
        { id: 'tx1002', amount: 7500, type: 'savings_transfer', timestamp: Date.now() - 86400000, status: 'completed' }
      ]
    },
    'test_user_e2e': {
      profile: {
        userId: 'test_user_e2e',
        name: 'Test User E2E',
        riskProfile: 'conservative',
        preferences: {
          autoSavingsRate: 0.30,
          preferredInvestments: ['bond', 'fund'],
          riskTolerance: 'low'
        }
      },
      accounts: {
        checking: { id: 'CHK001', balance: 50000, type: 'checking' },
        savings: { id: 'SV001', balance: 15000, type: 'savings' },
        investment: { id: 'INV001', balance: 25000, type: 'investment' }
      },
      transactions: [
        { id: 'tx2001', amount: 25000, type: 'salary_deposit', timestamp: Date.now(), merchant: 'Employer' },
        { id: 'tx2002', amount: 7500, type: 'savings_transfer', timestamp: Date.now() - 86400000, status: 'completed' }
      ]
    }
  },
  marketData: {
    bonds: [
      { instrument: 'GovBond1Y', rate: 0.28, risk: 'low', duration: '1Y', updatedAt: Date.now() },
      { instrument: 'GovBond2Y', rate: 0.32, risk: 'low', duration: '2Y', updatedAt: Date.now() },
      { instrument: 'CorpBond1Y', rate: 0.35, risk: 'medium', duration: '1Y', updatedAt: Date.now() }
    ],
    equities: [
      { instrument: 'BIST100', rate: 0.35, risk: 'high', sector: 'index', updatedAt: Date.now() },
      { instrument: 'BlueChip', rate: 0.25, risk: 'medium', sector: 'technology', updatedAt: Date.now() }
    ],
    funds: [
      { instrument: 'BESFund', rate: 0.22, risk: 'medium', type: 'pension', updatedAt: Date.now() },
      { instrument: 'MixedFund', rate: 0.18, risk: 'low', type: 'balanced', updatedAt: Date.now() }
    ]
  }
};

app.get('/health', (req, res) => res.json({ status: 'ok', version: '2.0', tools: Object.keys(mockData) }));

// Existing tools
app.post('/transactions.query', (req, res) => {
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const user = mockData.users[userId];
  
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }
  
  // Mock response with realistic data
  const transactions = user.transactions.filter(tx => {
    if (body.since) {
      return tx.timestamp >= body.since;
    }
    return true;
  }).slice(0, body.limit || 10);
  
  return res.json({
    transactions: transactions,
    total: user.transactions.length,
    userId: userId
  });
});

app.post('/userProfile.get', (req, res) => {
  const userId = req.body.userId || 'web_ui_user';
  const user = mockData.users[userId];
  
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }
  
  return res.json({
    userId: userId,
    profile: user.profile,
    accounts: user.accounts,
    savedPreferences: user.profile.preferences
  });
});

app.post('/risk.scoreTransaction', (req, res) => {
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const tx = body.tx || {};
  
  // Mock risk scoring based on transaction type and amount
  let score = 0.05; // Default low risk
  let reason = 'low risk';
  
  if (tx.type === 'salary_deposit') {
    score = 0.02; // Very low risk for salary
    reason = 'regular salary deposit';
  } else if (tx.amount > 50000) {
    score = 0.15; // Higher risk for large amounts
    reason = 'large amount transaction';
  } else if (tx.type === 'external_transfer') {
    score = 0.25; // Higher risk for external transfers
    reason = 'external transfer';
  }
  
  return res.json({
    score: score,
    reason: reason,
    factors: ['amount', 'type', 'user_history'],
    recommendation: score < 0.1 ? 'approve' : 'review',
    userId: userId,
    timestamp: Date.now()
  });
});

app.post('/market.quotes', (req, res) => {
  const body = req.body;
  const assetType = body.assetType || 'bond';
  const tenor = body.tenor || '1Y';
  
  let quotes = [];
  
  switch (assetType.toLowerCase()) {
    case 'bond':
      quotes = mockData.marketData.bonds.filter(bond => bond.duration === tenor);
      break;
    case 'equity':
      quotes = mockData.marketData.equities;
      break;
    case 'fund':
      quotes = mockData.marketData.funds;
      break;
    default:
      quotes = [...mockData.marketData.bonds, ...mockData.marketData.equities, ...mockData.marketData.funds];
  }
  
  return res.json({
    assetType: assetType,
    tenor: tenor,
    quotes: quotes,
    updatedAt: Date.now(),
    marketStatus: 'open'
  });
});

app.post('/savings.createTransfer', (req, res) => {
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  
  // Mock transfer creation
  const transferId = `tx-${Math.floor(Math.random() * 10000)}`;
  const status = body.status || 'pending';
  
  return res.json({
    status: 'ok',
    txId: transferId,
    userId: userId,
    amount: body.amount,
    from: body.from,
    to: body.to,
    status: status,
    executedAt: status === 'completed' ? new Date().toISOString() : null,
    createdAt: new Date().toISOString()
  });
});

// New enhanced tools for chat response handling

app.post('/payments.modifyTransfer', (req, res) => {
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const newAmount = body.newAmount;
  const transferId = body.transferId || `tx-${Math.floor(Math.random() * 10000)}`;
  
  // Mock transfer modification
  return res.json({
    status: 'ok',
    action: 'transfer_modified',
    txId: transferId,
    userId: userId,
    originalAmount: body.originalAmount,
    newAmount: newAmount,
    difference: newAmount - (body.originalAmount || 0),
    message: `Transfer miktarı ${newAmount}₺ olarak güncellendi`,
    executedAt: new Date().toISOString()
  });
});

app.post('/investment.updatePreference', (req, res) => {
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const preferredInvestment = body.preferredInvestment || 'bond';
  const allocation = body.allocation || 100; // percentage
  
  // Mock investment preference update
  return res.json({
    status: 'ok',
    action: 'preference_updated',
    userId: userId,
    preferredInvestment: preferredInvestment,
    allocation: allocation,
    message: `${preferredInvestment} yatırım tercihi %${allocation} olarak ayarlandı`,
    updatedAt: new Date().toISOString()
  });
});

app.post('/risk.performAnalysis', (req, res) => {
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const analysisType = body.analysisType || 'comprehensive';
  
  // Mock comprehensive risk analysis
  const analysis = {
    overallScore: 0.05,
    categories: {
      transactionRisk: 0.02,
      marketRisk: 0.08,
      liquidityRisk: 0.03,
      creditRisk: 0.01
    },
    recommendations: [
      'Düşük risk profili uygun',
      'Tahvil yatırımları önerilir',
      'Acil durum fonu yeterli'
    ],
    riskLevel: 'low'
  };
  
  return res.json({
    status: 'ok',
    action: 'risk_analysis_completed',
    userId: userId,
    analysis: analysis,
    message: `Risk analizi tamamlandı. Genel risk skoru: ${analysis.overallScore}`,
    timestamp: Date.now()
  });
});

app.post('/general.getAdvice', (req, res) => {
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const question = body.question || '';
  
  // Mock general advice based on question keywords
  let advice = 'Genel finansal danışmanlık hizmeti sağlandı.';
  
  if (question.toLowerCase().includes('tahvil')) {
    advice = 'Tahvil yatırımları düşük riskli ve sabit getiri sağlar. Devlet tahvilleri önerilir.';
  } else if (question.toLowerCase().includes('hisse')) {
    advice = 'Hisse senedi yatırımları yüksek riskli ancak uzun vadede yüksek getiri potansiyeli sunar.';
  } else if (question.toLowerCase().includes('tasarruf')) {
    advice = 'Tasarruf oranınızı %30 civarında tutmanız önerilir. Acil durum fonu için 3-6 aylık gider tutarında birikim yapın.';
  }
  
  return res.json({
    status: 'ok',
    action: 'advice_provided',
    userId: userId,
    question: question,
    advice: advice,
    timestamp: Date.now()
  });
});

app.post('/portfolio.getStatus', (req, res) => {
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  
  // Mock portfolio status
  const portfolio = {
    totalValue: 90000,
    allocation: {
      checking: 50000,
      savings: 15000,
      investment: 25000
    },
    performance: {
      daily: 0.02,
      monthly: 0.15,
      yearly: 0.28
    },
    riskScore: 0.05
  };
  
  return res.json({
    status: 'ok',
    userId: userId,
    portfolio: portfolio,
    message: 'Portföy durumu başarıyla alındı',
    timestamp: Date.now()
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('MCP Server Error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    message: err.message,
    timestamp: Date.now()
  });
});

// Alias endpoints for LLM tool calling compatibility
app.post('/user_profile_get', (req, res) => {
  // Redirect to userProfile.get
  const userId = req.body.userId || 'web_ui_user';
  const user = mockData.users[userId];
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }
  res.json({ userId, ...user });
});

app.post('/userProfile_get', (req, res) => {
  // Redirect to userProfile.get
  const userId = req.body.userId || 'web_ui_user';
  const user = mockData.users[userId];
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }
  res.json({ userId, ...user });
});

app.post('/transactions_query', (req, res) => {
  // Redirect to transactions.query
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const limit = body.limit || 10;
  const since = body.since;
  
  const user = mockData.users[userId];
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }
  
  let transactions = user.transactions || [];
  if (since) {
    const sinceDate = new Date(since);
    transactions = transactions.filter(tx => new Date(tx.timestamp) >= sinceDate);
  }
  
  res.json({
    transactions: transactions.slice(0, limit),
    total: transactions.length,
    userId
  });
});

app.post('/risk_score_transaction', (req, res) => {
  // Redirect to risk.scoreTransaction
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const tx = body.tx || {};
  
  // Simple risk scoring logic
  let score = 0.5; // default medium risk
  if (tx.amount < 1000) score = 0.1;
  else if (tx.amount < 10000) score = 0.3;
  else if (tx.amount < 50000) score = 0.5;
  else score = 0.8;
  
  if (tx.type === 'internal_transfer') score *= 0.1; // internal transfers are low risk
  
  res.json({
    score,
    reason: score < 0.3 ? 'low risk' : score < 0.7 ? 'medium risk' : 'high risk',
    factors: ['amount', 'type', 'user_history'],
    recommendation: score < 0.5 ? 'approve' : 'review',
    userId,
    timestamp: Date.now()
  });
});

app.post('/savings_create_transfer', (req, res) => {
  // Redirect to savings.createTransfer
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const amount = body.amount || 0;
  const fromAccount = body.fromAccount || 'CHK001';
  const toSavingsId = body.toSavingsId || 'SV001';
  
  const txId = `tx-${Math.floor(Math.random() * 10000)}`;
  
  res.json({
    status: 'pending',
    txId,
    userId,
    amount,
    fromAccount,
    toSavingsId,
    executedAt: null,
    createdAt: new Date().toISOString()
  });
});

app.post('/savings_createTransfer', (req, res) => {
  // Redirect to savings.createTransfer
  const body = req.body;
  const userId = body.userId || 'web_ui_user';
  const amount = body.amount || 0;
  const fromAccount = body.fromAccount || 'CHK001';
  const toSavingsId = body.toSavingsId || 'SV001';
  
  const txId = `tx-${Math.floor(Math.random() * 10000)}`;
  
  res.json({
    status: 'pending',
    txId,
    userId,
    amount,
    fromAccount,
    toSavingsId,
    executedAt: null,
    createdAt: new Date().toISOString()
  });
});

// 404 handler - must be last
app.use((req, res) => {
  res.status(404).json({ 
    error: 'Tool not found',
    path: req.path,
    method: req.method,
    timestamp: Date.now()
  });
});

app.listen(PORT, () => {
  console.log(`🚀 MCP Finance Tools Server v2.0 listening on port ${PORT}`);
  console.log(`📊 Available tools: transactions.query, userProfile.get, risk.scoreTransaction, market.quotes, savings.createTransfer`);
  console.log(`🆕 Enhanced tools: payments.modifyTransfer, investment.updatePreference, risk.performAnalysis, general.getAdvice, portfolio.getStatus`);
  console.log(`🔧 Alias tools: user_profile_get, transactions_query, risk_score_transaction, savings_create_transfer, savings_createTransfer`);
  console.log(`💾 Mock data loaded for ${Object.keys(mockData.users).length} users`);
});