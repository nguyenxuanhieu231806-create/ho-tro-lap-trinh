const fs=require('fs'),path=require('path'),http=require('http'),assert=require('assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'../../..'),staticDir=path.join(root,'static');
const report={mode:'controlled API fixtures; no real account/document import',checks:[],errors:[]};
const check=(label,value)=>{assert.ok(value,label);report.checks.push(label);};
const me={username:'ui-admin@example.test',name:'Quản trị kiểm thử',student_id:'TEST001',class_name:'CNTT3.K25',study_year:3,role:'admin'};
const cite={id:'chunk-1',label:'S1',file_name:'Tai-lieu-mau.docx',locator:'Mục 2 · Đoạn 3'};
let authenticated=false,delay=0,asked=null,importConfirmed=false,selectedDocument=false,reindexed=false;
async function main(){
 const server=http.createServer((req,res)=>{const parsed=new URL(req.url,'http://local');const filename=path.resolve(staticDir,'.'+(parsed.pathname==='/'?'/index.html':decodeURIComponent(parsed.pathname)));if(!filename.startsWith(staticDir+path.sep)||!fs.existsSync(filename)){res.writeHead(404);res.end();return;}const ext=path.extname(filename);res.writeHead(200,{'Content-Type':({'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css','.png':'image/png','.wasm':'application/wasm'})[ext]||'application/octet-stream'});fs.createReadStream(filename).pipe(res);});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL || 'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1366,height:768},ignoreHTTPSErrors:true});
 const fixture=async route=>{
  const req=route.request(),endpoint=new URL(req.url()).pathname;
  const ok=data=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)}).catch(()=>{});
  if(endpoint==='/api/auth/me')return authenticated?ok(me):route.fulfill({status:401,json:{error:'Chưa đăng nhập'}});
  if(endpoint==='/api/auth/login'){authenticated=true;return ok(me);}
  if(endpoint==='/api/health')return ok({ready:true,ollama_connected:true,model:'ui-fixture'});
  if(endpoint==='/api/tutor/complete')return ok({completion:''});
  if(endpoint==='/api/rag/documents')return ok({documents:[{file_name:'Tai-lieu-mau.docx'}]});
  if(endpoint==='/api/rag/conversations')return req.method()==='POST'?ok({id:'conversation-1',title:'Câu hỏi kiểm thử'}):ok({conversations:[{id:'conversation-1',title:'Câu hỏi kiểm thử'}]});
  if(endpoint.endsWith('/messages'))return ok({messages:[{role:'user',content:'Câu hỏi cũ'},{role:'assistant',content:'Trả lời có nguồn [S1]',citations:[cite],status:'completed'}]});
  if(endpoint==='/api/rag/sources/chunk-1')return ok({...cite,text:'Đoạn văn thực sự được dùng làm bằng chứng.'});
  if(endpoint==='/api/rag/chat'){
   asked=req.postDataJSON();if(delay)await new Promise(resolve=>setTimeout(resolve,delay));
   const result={reply:'Nội dung theo nguồn [S1]. <img src=x onerror=alert(1)>',citations:[cite]};
   return route.fulfill({contentType:'application/x-ndjson',body:JSON.stringify({status:'Đang kiểm tra bằng chứng'})+'\n'+JSON.stringify({delta:result.reply})+'\n'+JSON.stringify({done:true,result})+'\n'}).catch(()=>{});
  }
  if(endpoint==='/api/admin/documents')return ok({documents:[{id:'document-1',revision_id:'revision-1',file_name:'Tai-lieu-mau.docx',status:'staged'}]});
  if(endpoint==='/api/admin/documents/preview'){selectedDocument=req.postData().includes('document_id')&&req.postData().includes('document-1');return ok({revision_id:'revision-1',file_name:'Tai-lieu-mau.docx',blocks:[{kind:'paragraph',text:'<script>alert(1)</script>',locator:'Đoạn 1'}],images:[],warnings:['Cần đối chiếu nội dung']});}
  if(endpoint==='/api/admin/index/reindex'){reindexed=true;return ok({job_id:'job-1'});}
  if(endpoint.endsWith('/publish'))return ok({job_id:'job-1'});
  if(endpoint==='/api/admin/jobs/job-1')return ok({status:'completed',message:'Đã công bố tài liệu'});
  if(endpoint==='/api/admin/students/import/preview')return ok({batch_id:'batch-1',counts:{total:2,valid:1,invalid:1},rows:[{row:2,email:'student@example.test',student_id:'00123',name:'Sinh viên kiểm thử',class_name:'CNTT3',study_year:3,status:'valid',password:'MUST-NOT-RENDER'},{row:3,email:'wrong',status:'invalid',reason:'Email sai'}]});
  if(endpoint.endsWith('/confirm')){importConfirmed=true;return ok({counts:{total:2,created:1,failed:1},rows:[{row:2,email:'student@example.test',status:'created'}],credentials:[{email:'student@example.test',password:'one-time-secret'}]});}
  return ok({});
 };
 await context.route('**/api/**',fixture);
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 try{
  const base='http://127.0.0.1:'+server.address().port;
  await page.goto(base,{waitUntil:'domcontentloaded'});await page.locator('#student-account').fill(me.username);await page.locator('#student-password').fill('demo');await page.locator('#login-form button[type=submit]').click();await page.locator('#skip-intro').click();
  await page.waitForFunction(()=>window.monaco&&monaco.editor.getModels().length>0);
  check('existing code pane visible',await page.locator('#chat-form').isVisible());
  check('admin link shown only for administrator',await page.locator('#admin-link').isVisible());
  await page.locator('#mode-documents').click();await page.locator('#rag-library-note').filter({hasText:'1 tài liệu'}).waitFor();
  check('document mode hides only code chat',!(await page.locator('#chat-form').isVisible())&&await page.locator('#editor-panel').isVisible());
  delay=1300;await page.locator('#rag-question').fill('Nội dung ở mục 2 là gì?');await page.locator('#rag-send').click();
  await page.waitForFunction(()=>window.tutorRagBusy===true);
  check('RAG active disables code mode',await page.locator('#mode-code').isDisabled());
  check('RAG active disables inline suggestions',await page.evaluate(()=>monaco.editor.getEditors()[0].getRawOptions().inlineSuggest.enabled===false));
  await page.locator('#rag-status').filter({hasText:'Hoàn thành'}).waitFor();
  check('question bound to conversation',asked.question==='Nội dung ở mục 2 là gì?'&&asked.conversation_id==='conversation-1');
  check('answer is safe literal text',(await page.locator('#rag-log').textContent()).includes('<img src=x')&&await page.locator('#rag-log img').count()===0);
  await page.locator('.rag-citation').click();await page.locator('#rag-source-content').filter({hasText:'thực sự'}).waitFor();
  check('source locator uses no fabricated page',(await page.locator('#rag-source-locator').textContent()).includes('Đoạn 3')&&!(await page.locator('#rag-source-locator').textContent()).includes('Trang'));
  await page.locator('#rag-source-close').click();
  await page.screenshot({path:path.join(__dirname,'rag-ui-desktop.png')});
  await page.locator('#rag-new').click();await page.locator('#rag-conversation').selectOption('conversation-1');await page.locator('#rag-log').filter({hasText:'Câu hỏi cũ'}).waitFor();check('server history restored',await page.locator('#rag-log .rag-message').count()===2);
  delay=2500;await page.locator('#rag-question').fill('Dừng yêu cầu');await page.locator('#rag-send').click();await page.locator('#rag-stop').click();await page.locator('#rag-status').filter({hasText:'Đã dừng'}).waitFor();check('Stop resets RAG state',await page.evaluate(()=>window.tutorRagBusy===false));
  await page.locator('#mode-code').click();check('code chat restored',await page.locator('#chat-form').isVisible()&&await page.locator('#code-run').isVisible());
  await page.setViewportSize({width:390,height:844});await page.locator('#tab-chat').click();await page.locator('#mode-documents').click();
  check('mobile document mode remains selected',await page.locator('#mode-documents').getAttribute('aria-pressed')==='true'&&await page.locator('#rag-panel').isVisible()&&!(await page.locator('#chat-form').isVisible()));
  check('mobile RAG fits viewport',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.getElementById('rag-send').getBoundingClientRect().bottom<=innerHeight));
  await page.screenshot({path:path.join(__dirname,'rag-ui-mobile.png')});
  const admin=await context.newPage();admin.on('pageerror',e=>report.errors.push(e.message));await admin.goto(base+'/admin.html');await admin.locator('#admin-work').waitFor({state:'visible'});
  await admin.locator('#admin-document-target').selectOption('document-1');await admin.locator('#admin-document-file').setInputFiles({name:'mau.txt',mimeType:'text/plain',buffer:Buffer.from('Nội dung mẫu')});await admin.locator('#admin-document-form button').click();await admin.locator('#admin-document-preview').waitFor({state:'visible'});
  check('explicit version update sends document ID',selectedDocument);
  check('document preview is safe text',(await admin.locator('#admin-document-blocks').textContent()).includes('<script>')&&await admin.locator('#admin-document-blocks script').count()===0);
  await admin.locator('#admin-publish').click();await admin.locator('#admin-document-status').filter({hasText:'Đã công bố'}).waitFor();check('publish shows confirmed job completion',true);
  await admin.locator('#admin-reindex').click();await admin.locator('#admin-document-status').filter({hasText:'Đã công bố'}).waitFor();check('reindex uses explicit management action',reindexed);
  await admin.locator('#admin-student-file').setInputFiles({name:'sinhvien.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:Buffer.from('fixture')});await admin.locator('#admin-student-form button').click();await admin.locator('#admin-import-preview').waitFor({state:'visible'});
  check('Excel preview renders errors but not passwords',(await admin.locator('#admin-import-rows').textContent()).includes('Email sai')&&!(await admin.locator('#admin-import-rows').textContent()).includes('MUST-NOT-RENDER')&&!importConfirmed);
  admin.on('dialog',dialog=>dialog.accept());await admin.locator('#admin-import-confirm').click();await admin.locator('#admin-credentials').waitFor({state:'visible'});check('private credentials shown only after confirm',importConfirmed&&(await admin.locator('#admin-credential-text').textContent()).includes('one-time-secret'));
  await admin.locator('#admin-clear-credentials').click();check('private credentials clear from DOM',(await admin.locator('#admin-credential-text').textContent())==='');
  await admin.screenshot({path:path.join(__dirname,'rag-admin-preview.png')});
  check('no JavaScript runtime errors',report.errors.length===0);
 }finally{fs.writeFileSync(path.join(__dirname,'ui-rag-results.json'),JSON.stringify(report,null,2));await browser.close();await new Promise(resolve=>server.close(resolve));}
 console.log(JSON.stringify(report,null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
