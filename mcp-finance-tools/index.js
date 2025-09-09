const express = require('express');
const bodyParser = require('body-parser');
const app = express();
app.use(bodyParser.json());
const PORT = process.env.PORT || 4000;

app.get('/health', (req,res)=>res.json({status:'ok'}));

app.post('/transactions.query', (req,res)=>{
  const body = req.body;
  // mock response
  return res.json({transactions:[{id:'tx1001', amount: body.since?0: body.limit?100:0, ts:Date.now(), merchant:'Employer'}]});
});

app.post('/userProfile.get', (req,res)=>{
  return res.json({userId:req.body.userId, savedPreferences:{autoSavingsRate:0.30}});
});

app.post('/risk.scoreTransaction', (req,res)=>{
  return res.json({score:0.05, reason:'low risk (mock)'});
});

app.post('/market.quotes', (req,res)=>{
  return res.json({quotes:[{instrument:'GovBond1Y', rate:0.11, updatedAt:Date.now()}]});
});

app.post('/savings.createTransfer', (req,res)=>{
  return res.json({status:'ok', txId:'tx-'+Math.floor(Math.random()*10000), executedAt: new Date().toISOString()});
});

app.listen(PORT, ()=>{
  console.log('MCP mock server listening on', PORT);
});