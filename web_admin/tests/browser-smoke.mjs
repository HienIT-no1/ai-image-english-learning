import http from 'node:http';
import { once } from 'node:events';
import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createAdminServer } from '../server.mjs';

const browserPath = process.env.ADMIN_TEST_BROWSER || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const profile = await mkdtemp(path.join(os.tmpdir(),'english-admin-browser-'));
const topics = [{topic_id:1,name:'Động vật',slug:'animals',symbol:'🐱',vocabulary_count:1}];
const words = [{vocabulary_id:1,word:'cat',ipa:'/kæt/',level:'BEGINNER',meanings:[{meaning_id:1,meaning_vi:'con mèo'}],examples:[{example_id:1,sentence_en:'A cat.',sentence_vi:'Một con mèo.'}],topics:[topics[0]],relations:[]}];
let ident=2;
const writes=[];
const backend = http.createServer(async(req,res) => {
  let body=''; for await(const chunk of req) body+=chunk;
  const data=body ? JSON.parse(body) : null;
  const route = new URL(req.url,'http://local').pathname;
  let result;
  if(route==='/auth/login') result={access_token:data.username==='learner' ? 'learner-token' : 'admin-token'};
  else if(!req.headers.authorization) {res.writeHead(401,{'content-type':'application/json'});res.end('{"detail":"Not authenticated"}');return;}
  else if(route==='/users/me') result={user_id:1,username:'admin',full_name:'Admin Test',role:req.headers.authorization.includes('learner') ? 'USER':'ADMIN'};
  else if(route==='/admin/summary') result={users:2,admins:1,topics:topics.length,vocabularies:words.length,completed_quizzes:5};
  else if(route==='/admin/users') result=[{user_id:1,username:'admin',email:'admin@example.com',full_name:'Admin Test',role:'ADMIN'},{user_id:2,username:'learner',email:'learner@example.com',full_name:'Người học',role:'USER'}];
  else if(route==='/admin/topics' && req.method==='GET') result=topics;
  else if(route==='/admin/vocabularies' && req.method==='GET') result=words;
  else if(route==='/admin/topics' && req.method==='POST') {result={...data,topic_id:ident++,vocabulary_count:0};topics.push(result);writes.push({route,data});}
  else if(route.startsWith('/admin/topics/') && req.method==='DELETE') {const index=topics.findIndex(t=>t.topic_id===Number(route.split('/').at(-1)));topics.splice(index,1);result={message:'Topic deleted'};writes.push({route});}
  else if(route==='/admin/vocabularies' && req.method==='POST') {result={...data,vocabulary_id:ident++,level:'BEGINNER',meanings:[{meaning_id:1,meaning_vi:data.meaning_vi}],examples:data.sentence_en ? [{example_id:1,sentence_en:data.sentence_en,sentence_vi:data.sentence_vi}] : [],topics:topics.filter(t=>data.topic_ids.includes(t.topic_id)),relations:[]};words.push(result);writes.push({route,data});}
  else if(route.startsWith('/admin/vocabularies/') && req.method==='PUT') {const word=words.find(w=>w.vocabulary_id===Number(route.split('/').at(-1)));word.meanings[0].meaning_vi=data.meaning_vi;result=word;writes.push({route,data});}
  else {res.writeHead(404);res.end('{}');return;}
  res.writeHead(req.method==='POST' && route!=='/auth/login' ? 201:200,{'content-type':'application/json'});res.end(JSON.stringify(result));
});
async function listen(server){server.listen(0,'127.0.0.1');await once(server,'listening');return `http://127.0.0.1:${server.address().port}`;}
const backendUrl=await listen(backend), server=createAdminServer({backend:backendUrl}), url=await listen(server);
let browser, socket;
try {
  browser=spawn(browserPath,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:['ignore','ignore','pipe']});
  const debuggerUrl=await new Promise((resolve,reject)=>{let output='';const timer=setTimeout(()=>reject(new Error('Browser startup timed out')),20000);browser.once('error',e=>{clearTimeout(timer);reject(e);});browser.stderr.on('data',chunk=>{output+=chunk;const m=output.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(m){clearTimeout(timer);resolve(m[1]);}});});
  const port=new URL(debuggerUrl).port;
  const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let seq=0;const pending=new Map(), errors=[];
  socket.onmessage=event=>{const m=JSON.parse(event.data);if(m.id){const pair=pending.get(m.id);pending.delete(m.id);if(m.error)pair.reject(new Error(m.error.message));else pair.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);};
  const cdp=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);return r.result.value;};
  const wait=async expression=>{const deadline=Date.now()+10000;while(Date.now()<deadline){if(await evaluate(expression))return;await new Promise(resolve=>setTimeout(resolve,60));}throw new Error(`Timed out: ${expression}`);};
  const click=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const fill=(selector,value)=>evaluate(`document.querySelector(${JSON.stringify(selector)}).value=${JSON.stringify(value)}`);
  const submit=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).requestSubmit()`);
  await cdp('Runtime.enable');await cdp('Page.enable');
  await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await cdp('Page.navigate',{url});await wait("Boolean(document.querySelector('#login-form'))");
  await fill('[name=username]','learner');await fill('[name=password]','password-test');await submit('#login-form');
  await wait("document.querySelector('#login-error').textContent.includes('quyền quản trị')");
  assert.equal(await evaluate("sessionStorage.getItem('admin_token')"),null);
  await fill('[name=username]','admin');await submit('#login-form');
  await wait("document.querySelectorAll('.stat-number').length===4");
  assert.equal(await evaluate("document.querySelector('.stat-number').textContent"),'2');
  const dashboardImage=await cdp('Page.captureScreenshot',{format:'png'});
  const dashboardPath=path.join(os.tmpdir(),'english-admin-dashboard.png');await writeFile(dashboardPath,Buffer.from(dashboardImage.data,'base64'));
  await click('[data-quick=topic]');await wait("Boolean(document.querySelector('#edit-form')) && document.querySelector('#editor').open");
  await fill('[name=name]','Đồ ăn');await fill('[name=slug]','food');await submit('#edit-form');
  await wait("!document.querySelector('#editor').open && document.querySelectorAll('.topic-card').length===2");
  await evaluate("location.hash='vocabulary'");await wait("Boolean(document.querySelector('[data-edit=\"1\"]'))");
  await click('[data-edit="1"]');await fill('[name=meaning_vi]','mèo nhà');await submit('#edit-form');
  await wait("!document.querySelector('#editor').open && document.querySelector('#rows').textContent.includes('mèo nhà')");
  assert.equal(writes.at(-1).data.sentence_en,'A cat.');
  await click('#create');await fill('[name=word]','apple');await fill('[name=meaning_vi]','quả táo');await click('[name=topic_ids][value="1"]');await submit('#edit-form');
  await wait("!document.querySelector('#editor').open && document.querySelector('#rows').textContent.includes('apple')");
  assert.deepEqual(writes.at(-1).data.topic_ids,[1]);
  await fill('#search','TAO');await evaluate("document.querySelector('#search').dispatchEvent(new Event('input',{bubbles:true}))");
  assert.equal(await evaluate("document.querySelectorAll('tbody tr').length"),1);
  await click('[data-detail="3"]');await wait("document.querySelector('#editor').open");await click('[data-close]');
  await evaluate("location.hash='topics'");await wait("document.querySelectorAll('.topic-card').length===2");
  assert.equal(await evaluate("document.querySelector('[data-delete=\"1\"]').disabled"),true);
  await click('[data-delete="2"]');await click('#confirm-delete');await wait("!document.querySelector('#editor').open && document.querySelectorAll('.topic-card').length===1");
  await evaluate("location.hash='users'");await wait("document.querySelectorAll('tbody tr').length===2");
  await evaluate("document.querySelector('#filter').value='ADMIN';document.querySelector('#filter').dispatchEvent(new Event('change'))");
  assert.equal(await evaluate("document.querySelectorAll('tbody tr').length"),1);
  await cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await evaluate("location.hash='dashboard'");await wait("document.querySelectorAll('.stat-number').length===4");
  assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));
  await click('#open-menu');assert.equal(await evaluate("document.querySelector('#sidebar').classList.contains('open')"),true);await click('#close-menu');
  const mobileImage=await cdp('Page.captureScreenshot',{format:'png'});const mobilePath=path.join(os.tmpdir(),'english-admin-mobile.png');await writeFile(mobilePath,Buffer.from(mobileImage.data,'base64'));
  await click('#logout');await wait("Boolean(document.querySelector('#login-form'))");assert.equal(await evaluate("sessionStorage.getItem('admin_token')"),null);
  assert.deepEqual(errors,[]);
  console.log('PASS: USER rejection, ADMIN login, dashboard, topic create/delete, word create/edit/detail, Vietnamese search, user filter, mobile navigation and logout.');
  console.log(`Desktop screenshot: ${dashboardPath}\nMobile screenshot: ${mobilePath}`);
} finally {
  socket?.close();
  if(browser && browser.exitCode===null){browser.kill();await Promise.race([once(browser,'exit'),new Promise(resolve=>setTimeout(resolve,3000))]);}
  server.closeAllConnections();backend.closeAllConnections();await Promise.all([new Promise(resolve=>server.close(resolve)),new Promise(resolve=>backend.close(resolve))]);
  // Only remove the dedicated temporary profile, after verifying its resolved parent and name.
  const resolved=path.resolve(profile);
  if(path.dirname(resolved)===path.resolve(os.tmpdir()) && path.basename(resolved).startsWith('english-admin-browser-')) await rm(resolved,{recursive:true,force:true,maxRetries:3,retryDelay:200}).catch(()=>{});
}
