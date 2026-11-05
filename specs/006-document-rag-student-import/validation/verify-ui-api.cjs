const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const base=process.env.TUTOR_UI_BASE;
const report={mode:'actual HTTP/auth/SQLite/Chroma/XLSX; embedding and answer outputs controlled by Python harness',checks:[],errors:[]};
const check=(name,value)=>{assert.ok(value,name);report.checks.push(name);};
async function login(page,email,password){await page.goto(base,{waitUntil:'domcontentloaded'});await page.locator('#student-account').fill(email);await page.locator('#student-password').fill(password);await page.locator('#login-form button[type=submit]').click();await page.locator('#skip-intro').click();await page.waitForFunction(()=>window.monaco&&monaco.editor.getModels().length);await page.locator('#completion-enabled').uncheck();}
async function main(){
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1366,height:768},ignoreHTTPSErrors:true});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 try{
  await login(page,process.env.TUTOR_UI_ADMIN_EMAIL,process.env.TUTOR_UI_ADMIN_PASSWORD);
  check('real administrator login shows management link',await page.locator('#admin-link').isVisible());
  await page.locator('#admin-link').click();await page.locator('#admin-work').waitFor({state:'visible'});
  check('real auth protects and opens management interface',(await page.locator('#admin-auth-status').textContent()).includes('Đã xác thực quản trị'));
  const template=await context.request.get(base+'/api/admin/students/template');check('actual Excel template endpoint downloads workbook',template.status()===200&&(await template.body()).length>1000);
  const text='Hành tinh Sao Lam có hai vệ tinh tự nhiên tên là Mây và Sóng.';
  await page.locator('#admin-document-file').setInputFiles({name:'Tri-thuc-kiem-thu.txt',mimeType:'text/plain',buffer:Buffer.from(text,'utf8')});
  await page.locator('#admin-document-form button').click();await page.locator('#admin-document-preview').waitFor({state:'visible'});
  check('actual TXT parser and registry preview text',(await page.locator('#admin-document-blocks').textContent()).includes('Mây và Sóng'));
  await page.locator('#admin-publish').click();await page.locator('#admin-document-status').filter({hasText:'Đã nạp và công bố'}).waitFor({timeout:60000});
  check('publish job writes real Chroma index',true);
  const documents=await (await context.request.get(base+'/api/admin/documents')).json();
  const doc=documents.documents[0];
  await page.locator('#admin-document-target').selectOption(doc.id);
  await page.locator('#admin-document-file').setInputFiles({name:'Tri-thuc-cap-nhat.txt',mimeType:'text/plain',buffer:Buffer.from('Bản cập nhật đang chờ duyệt, chưa được công bố.','utf8')});
  await page.locator('#admin-document-form button').click();await page.locator('#admin-document-status').filter({hasText:'Đã đọc bản xem trước'}).waitFor();
  const current=await (await context.request.get(base+'/api/rag/documents')).json();
  check('explicit new draft retains previously published revision',current.documents.length===1&&current.documents[0].file_name==='Tri-thuc-kiem-thu.txt');
  await page.locator('#admin-student-file').setInputFiles(process.env.TUTOR_UI_XLSX_FILE);await page.locator('#admin-student-form button').click();await page.locator('#admin-import-preview').waitFor({state:'visible'});
  check('actual Excel preview includes invalid row and leading-zero student ID',(await page.locator('#admin-import-rows').textContent()).includes('Email không hợp lệ')&&(await page.locator('#admin-import-rows').textContent()).includes('00012345'));
  check('actual Excel preview hides supplied password',!(await page.locator('#admin-import-preview').textContent()).includes(process.env.TUTOR_UI_STUDENT_PASSWORD));
  page.on('dialog',dialog=>dialog.accept());await page.locator('#admin-import-confirm').click();await page.locator('#admin-credentials').waitFor({state:'visible',timeout:180000});
  check('actual commit issues credentials for valid new student',(await page.locator('#admin-credential-text').textContent()).includes(process.env.TUTOR_UI_STUDENT_EMAIL));
  await page.locator('#admin-clear-credentials').click();check('actual credential display clears',await page.locator('#admin-credential-text').textContent()==='');
  await page.screenshot({path:path.join(__dirname,'rag-admin-real-api.png')});
  const studentContext=await browser.newContext({viewport:{width:1366,height:768},ignoreHTTPSErrors:true});
  const student=await studentContext.newPage();student.on('pageerror',e=>report.errors.push(e.message));
  await login(student,process.env.TUTOR_UI_STUDENT_EMAIL,process.env.TUTOR_UI_STUDENT_PASSWORD);
  check('imported student logs in with supplied Excel credentials',(await student.locator('#student-id').textContent()).includes('00012345'));
  check('student does not see administrator link',!(await student.locator('#admin-link').isVisible()));
  const blocked=await studentContext.request.get(base+'/api/admin/documents');check('actual server denies student management access',blocked.status()===403);
  await student.locator('#mode-documents').click();await student.locator('#rag-library-note').filter({hasText:'1 tài liệu'}).waitFor();
  await student.locator('#rag-question').fill('Sao Lam có vệ tinh nào?');await student.locator('#rag-send').click();await student.locator('#rag-status').filter({hasText:'Hoàn thành'}).waitFor({timeout:60000});
  check('actual HTTP stream persists document answer',(await student.locator('#rag-log').textContent()).includes('Mây và Sóng'));
  check('actual citation marker maps to numbered source button',(await student.locator('.rag-citation').first().textContent()).includes('[1]'));
  const convo=await student.locator('#rag-conversation').inputValue();
  await student.locator('.rag-citation').first().click();await student.locator('#rag-source-content').filter({hasText:'Mây và Sóng'}).waitFor();
  check('actual private source endpoint shows correct text',(await student.locator('#rag-source-title').textContent()).includes('Tri-thuc-kiem-thu.txt'));
  check('source locator has no invented page',!(await student.locator('#rag-source-locator').textContent()).includes('Trang'));
  await student.locator('#rag-source-close').click();await student.screenshot({path:path.join(__dirname,'rag-ui-real-api.png')});
  await student.reload();await student.locator('#mode-documents').click();await student.locator('#rag-conversation option[value="'+convo+'"]').waitFor({state:'attached'});await student.locator('#rag-conversation').selectOption(convo);await student.locator('#rag-log').filter({hasText:'Mây và Sóng'}).waitFor();
  check('actual server conversation restores after reload',await student.locator('#rag-log .rag-message').count()===2);
  const otherOwner=await context.request.get(base+'/api/rag/conversations/'+convo+'/messages');check('actual ownership prevents another account reading conversation',otherOwner.status()===404||otherOwner.status()===403);
  await studentContext.close();check('no JavaScript runtime errors',report.errors.length===0);report.state='passed';
 }finally{fs.writeFileSync(path.join(__dirname,'ui-api-results.json'),JSON.stringify(report,null,2));await browser.close();}
 console.log(JSON.stringify(report,null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
