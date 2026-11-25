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
let contentId=2;
const wordContent = data => ({
  meanings: data.meanings.map(item => ({...item,meaning_id:item.meaning_id || contentId++})),
  examples: data.examples.map(item => ({...item,example_id:item.example_id || contentId++})),
});
const writes=[];
const users=[{user_id:1,username:'admin',email:'admin@example.com',full_name:'Admin Test',role:'ADMIN',is_locked:false},{user_id:2,username:'learner',email:'learner@example.com',full_name:'Người học',role:'USER',is_locked:false}];
const quizAttempt = {
  attempt_id:1, user_id:2, username:'learner', full_name:'Người học', quiz_type:'FILL_BLANK',
  status:'COMPLETED', total_questions:1, answered_count:1, correct_answers:1,
  started_at:'2026-11-25T00:00:00Z', completed_at:'2026-11-25T00:01:00Z', aborted_at:null,
};
const learningDay = {
  date:'2026-11-25', active_learners:2, study_events:4, correct_events:3,
  accuracy_rate:75, next_day_return_rate:50, returned_learner_days:1, eligible_learner_days:2,
};
const gameDay = { date:'2026-11-25', game_runs:2, scored_runs:1, average_score:120, passed_rounds:1 };
const reportRequests = [];
const backend = http.createServer(async(req,res) => {
  let body=''; for await(const chunk of req) body+=chunk;
  const data=body ? JSON.parse(body) : null;
  const {pathname:route, searchParams} = new URL(req.url,'http://local');
  let result;
  if(route==='/auth/login') result={access_token:data.username==='learner' ? 'learner-token' : 'admin-token'};
  else if(!req.headers.authorization) {res.writeHead(401,{'content-type':'application/json'});res.end('{"detail":"Not authenticated"}');return;}
  else if(route==='/users/me') result={user_id:1,username:'admin',full_name:'Admin Test',role:req.headers.authorization.includes('learner') ? 'USER':'ADMIN'};
  else if(route==='/admin/summary') result={users:2,admins:1,topics:topics.length,vocabularies:words.length,completed_quizzes:5};
  else if (route==='/admin/quizzes') {
    const items = searchParams.get('status') === 'ABORTED' ? [] : [quizAttempt];
    result={items, total:items.length, offset:0, limit:20};
  }
  else if (route==='/admin/quizzes/summary') result={total:1,completed:1,in_progress:0,aborted:0,by_quiz_type:[{quiz_type:'FILL_BLANK',total:1,completed:1,in_progress:0,aborted:0}],by_question_type:[{question_type:'FILL_BLANK',answered:1,correct:1}],common_misses:[]};
  else if (route==='/admin/quizzes/1') result={...quizAttempt,questions:[{position:1,question_type:'FILL_BLANK',word:'cat',meaning_vi:'con mèo',options:[],user_answer:'cat',correct_answer:'cat',is_correct:true,answered_at:'2026-11-25T00:01:00Z'}]};
  else if (route==='/admin/analytics/learning') {
    reportRequests.push(req.url);
    result={...learningDay,start_date:'2026-11-19',end_date:learningDay.date,daily:[{...learningDay,date:'2026-11-24'},{...learningDay,next_day_return_rate:null}],hardest_words:[{word:'cat',attempts:4,incorrect:1,incorrect_rate:25}]};
  }
  else if (route==='/admin/analytics/games') {
    reportRequests.push(req.url);
    const days = Number(searchParams.get('days'));
    const daily = Array.from({length:days}, (_, index) => {
      const date = new Date(`${gameDay.date}T00:00:00Z`);
      date.setUTCDate(date.getUTCDate() + index - days + 1);
      return {...gameDay, date:date.toISOString().slice(0,10), game_runs:index % 3};
    });
    result={...gameDay,start_date:daily[0].date,end_date:gameDay.date,daily,most_missed_words:[{word:'cat',misses:2}]};
  }
  else if(route==='/admin/users') result=users;
  else if(route==='/admin/users/2/lock' && req.method==='PATCH') {users[1].is_locked=data.is_locked;result=users[1];writes.push({route,data});}
  else if(route==='/admin/users/2' && req.method==='DELETE') {assert.equal(data.username,'learner');users.splice(1,1);result={message:'User deleted'};writes.push({route,data});}
  else if(/^\/admin\/users\/[12]$/.test(route) && req.method==='GET') result={...users.find(u=>u.user_id===Number(route.split('/').at(-1))),created_at:'2026-11-01T00:00:00Z',cefr_level:'A1',game_runs:1,game_score:100,vocabulary_names:{1:'cat'},learning:{today_count:1,daily_goal:10,current_streak:1,longest_streak:2,saved_count:1,mastered_count:1,needs_review:0,due_count:0,review_count:1,quiz_runs:0,quiz_correct:0,quiz_total:0,days:[{date:'2026-11-25',count:1}],progress:[{vocabulary_id:1,status:'MASTERED',correct_count:1,incorrect_count:0,last_reviewed_at:'2026-11-25T00:00:00Z',next_review_at:null}]}};
  else if(route==='/admin/topics' && req.method==='GET') result=topics;
  else if(route==='/admin/vocabularies' && req.method==='GET') result=words;
  else if(route==='/admin/topics' && req.method==='POST') {result={...data,topic_id:ident++,vocabulary_count:0};topics.push(result);writes.push({route,data});}
  else if(route.startsWith('/admin/topics/') && req.method==='DELETE') {const index=topics.findIndex(t=>t.topic_id===Number(route.split('/').at(-1)));topics.splice(index,1);result={message:'Topic deleted'};writes.push({route});}
  else if(route==='/admin/vocabularies' && req.method==='POST') {result={...data,...wordContent(data),vocabulary_id:ident++,level:'BEGINNER',topics:topics.filter(t=>data.topic_ids.includes(t.topic_id)),relations:[]};words.push(result);writes.push({route,data});}
  else if(route.startsWith('/admin/vocabularies/') && req.method==='PUT') {const word=words.find(w=>w.vocabulary_id===Number(route.split('/').at(-1)));Object.assign(word,data,wordContent(data));result=word;writes.push({route,data});}
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
  await click('[data-edit="1"]');await fill('[name=meaning_vi]','mèo nhà');
  await click('[data-content-kind="meaning"] [data-add-content]');
  await fill('[data-content-kind="meaning"] .word-content-row:last-child [name=meaning_vi]','mèo lớn');
  await fill('[data-content-kind="meaning"] .word-content-row:last-child [name=definition_en]','A large cat.');
  await click('[data-content-kind="example"] [data-add-content]');
  await fill('[data-content-kind="example"] .word-content-row:last-child [name=sentence_en]','The cat is asleep.');
  await click('[data-content-kind="example"] .word-content-row:first-child [data-remove-content]');
  await submit('#edit-form');
  await wait("!document.querySelector('#editor').open && document.querySelector('#rows').textContent.includes('mèo nhà')");
  assert.equal(writes.at(-1).data.meanings[0].meaning_id,1);
  assert.equal(writes.at(-1).data.meanings[1].definition_en,'A large cat.');
  assert.deepEqual(writes.at(-1).data.examples,[{sentence_en:'The cat is asleep.',sentence_vi:''}]);
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
  assert.equal(await evaluate("Boolean(document.querySelector('[data-user-lock=\"1\"]'))"),false);
  assert.equal(await evaluate("Boolean(document.querySelector('[data-user-delete=\"1\"]'))"),false);
  await click('[data-user-detail="2"]');await wait("document.querySelector('#editor').open && document.querySelector('#editor').textContent.includes('Hoạt động 7 ngày')");
  const progressImage=await cdp('Page.captureScreenshot',{format:'png'});
  await writeFile(path.join(os.tmpdir(),'english-admin-user-progress.png'),Buffer.from(progressImage.data,'base64'));
  assert.ok(await evaluate("document.querySelector('#editor').textContent.includes('cat')"));await click('[data-close]');
  await click('[data-user-lock="2"]');await click('#confirm-user-lock');
  await wait("!document.querySelector('#editor').open && document.querySelector('[data-user-lock=\"2\"]').textContent==='Mở khóa'");
  await click('[data-user-lock="2"]');await click('#confirm-user-lock');
  await wait("!document.querySelector('#editor').open && document.querySelector('[data-user-lock=\"2\"]').textContent==='Khóa'");
  await click('[data-user-delete="2"]');await fill('#delete-user-form [name=username]','wrong');await submit('#delete-user-form');
  assert.match(await evaluate("document.querySelector('#form-error').textContent"),/chưa khớp/);
  assert.equal(users.length,2);
  await fill('#delete-user-form [name=username]','learner');await submit('#delete-user-form');
  await wait("!document.querySelector('#editor').open && document.querySelectorAll('tbody tr').length===1");
  assert.equal(users.length,1);
  await evaluate("document.querySelector('#filter').value='ADMIN';document.querySelector('#filter').dispatchEvent(new Event('change'))");
  assert.equal(await evaluate("document.querySelectorAll('tbody tr').length"),1);
  await evaluate("location.hash='quizzes'");
  await wait("Boolean(document.querySelector('[data-quiz-details=\"1\"]'))");
  await click('[data-quiz-details="1"]');
  await wait("document.querySelector('#quiz-dialog').open && document.querySelector('#quiz-dialog').textContent.includes('con mèo')");
  await click('#quiz-dialog button[type=submit]');
  await fill('#quiz-status','ABORTED');
  await evaluate("document.querySelector('#quiz-status').dispatchEvent(new Event('change',{bubbles:true}))");
  await wait("document.querySelector('#quiz-attempts').textContent.includes('Không tìm thấy lượt quiz')");
  await evaluate("location.hash='learning'");
  await wait("document.querySelectorAll('.analytics-point').length===2");
  assert.equal(await evaluate("document.querySelector('.analytics-bar').style.height"),'100%');
  await fill('#daily-metric','next_day_return_rate');
  await evaluate("document.querySelector('#daily-metric').dispatchEvent(new Event('change'))");
  await click('.analytics-point');
  assert.match(await evaluate("document.querySelector('.analytics-chart-value').textContent"),/50%/);
  assert.equal(await evaluate("document.querySelectorAll('.analytics-bar.missing').length"),1);
  await evaluate("document.querySelector('.analytics-point.selected').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))");
  assert.match(await evaluate("document.querySelector('.analytics-chart-value').textContent"),/Chưa đủ dữ liệu/);
  await fill('[name=days]','7');
  await evaluate("document.querySelector('[name=days]').dispatchEvent(new Event('change',{bubbles:true}))");
  await wait("Boolean(document.querySelector('#hardest-heading'))");
  assert.equal(reportRequests.at(-1),'/admin/analytics/learning?days=7');
  const analyticsImage=await cdp('Page.captureScreenshot',{format:'png'});
  await writeFile(path.join(os.tmpdir(),'english-admin-learning.png'),Buffer.from(analyticsImage.data,'base64'));
  await cdp('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await evaluate("location.hash='games'");
  await wait("Boolean(document.querySelector('#missed-heading'))");
  await fill('[name=game_type]','WORD_DEFENSE');
  await evaluate("document.querySelector('[name=game_type]').dispatchEvent(new Event('change',{bubbles:true}))");
  await wait("Boolean(document.querySelector('#missed-heading'))");
  assert.equal(reportRequests.at(-1),'/admin/analytics/games?days=30&game_type=WORD_DEFENSE');
  await fill('[name=days]','90');
  await evaluate("document.querySelector('[name=days]').dispatchEvent(new Event('change',{bubbles:true}))");
  await wait("document.querySelectorAll('.analytics-point').length===90");
  assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));
  assert.ok(await evaluate("document.querySelector('.analytics-chart-scroll').scrollWidth > document.querySelector('.analytics-chart-scroll').clientWidth"));
  await evaluate("location.hash='dashboard'");await wait("document.querySelectorAll('.stat-number').length===4");
  assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));
  await click('#open-menu');assert.equal(await evaluate("document.querySelector('#sidebar').classList.contains('open')"),true);await click('#close-menu');
  const mobileImage=await cdp('Page.captureScreenshot',{format:'png'});const mobilePath=path.join(os.tmpdir(),'english-admin-mobile.png');await writeFile(mobilePath,Buffer.from(mobileImage.data,'base64'));
  await click('#logout');await wait("Boolean(document.querySelector('#login-form'))");assert.equal(await evaluate("sessionStorage.getItem('admin_token')"),null);
  assert.deepEqual(errors,[]);
  console.log('PASS: admin permissions, vocabulary and user management, quiz filtering and detail, learning charts, game filters, mobile and logout.');
  console.log(`Desktop screenshot: ${dashboardPath}\nMobile screenshot: ${mobilePath}`);
} finally {
  socket?.close();
  if(browser && browser.exitCode===null){browser.kill();await Promise.race([once(browser,'exit'),new Promise(resolve=>setTimeout(resolve,3000))]);}
  server.closeAllConnections();backend.closeAllConnections();await Promise.all([new Promise(resolve=>server.close(resolve)),new Promise(resolve=>backend.close(resolve))]);
  // Only remove the dedicated temporary profile, after verifying its resolved parent and name.
  const resolved=path.resolve(profile);
  if(path.dirname(resolved)===path.resolve(os.tmpdir()) && path.basename(resolved).startsWith('english-admin-browser-')) await rm(resolved,{recursive:true,force:true,maxRetries:3,retryDelay:200}).catch(()=>{});
}
