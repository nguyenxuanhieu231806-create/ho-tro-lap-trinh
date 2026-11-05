const fs = require('fs');
const path = require('path');
const http = require('http');
const assert = require('assert/strict');
const { chromium } = require('C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const project = path.resolve(__dirname, '../../..');
const output = __dirname;
const staticDir = path.join(project, 'static');
const report = { checks: [], errors: [] };
const student = {username:'student@example.test',name:'Người học',student_id:'DEMO001',class_name:'CNTT3.K25',study_year:3};
const originalCode = 'def double(x):\n    return x + 1\n';
const fixedCode = 'def double(x):\n    return 2 * x\n';
const result = {reply:'Dòng 2 đang trả về x + 1. Với mục tiêu gấp đôi, hãy trả về 2 * x.',issues:[{line:2,severity:'error',message:'Giá trị trả về chưa khớp mục tiêu gấp đôi.',suggestion:'Dùng return 2 * x.'}],fixed_code:fixedCode};
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css','.png':'image/png','.wasm':'application/wasm'};
function check(name, value) { assert.ok(value, name); report.checks.push(name); }
async function main() {
  const server = http.createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const file = path.resolve(staticDir, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!file.startsWith(staticDir + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, {'Content-Type':types[path.extname(file)] || 'application/octet-stream','Cache-Control':'no-store'});
    fs.createReadStream(file).pipe(res);
  });
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const browser = await chromium.launch({channel:'msedge',headless:true});
  const context = await browser.newContext({viewport:{width:1366,height:768},ignoreHTTPSErrors:true});
  const page = await context.newPage();
  page.on('pageerror', error => report.errors.push(error.message));
  let loggedIn = false;
  await page.route('**/api/**', async route => {
    const pathname = new URL(route.request().url()).pathname;
    let status = 200, body = {};
    if (pathname === '/api/auth/me') { status = loggedIn ? 200 : 401; body = loggedIn ? student : {error:'Chưa đăng nhập'}; }
    else if (pathname === '/api/auth/login') { loggedIn = true; body = student; }
    else if (pathname === '/api/auth/logout') { loggedIn = false; body = {message:'Đã đăng xuất'}; }
    else if (pathname === '/api/auth/change-password') body = {message:'Đã đổi mật khẩu kiểm thử'};
    else if (pathname === '/api/health') body = {ready:true,ollama_connected:true,model:'qwen2.5-coder:7b',message:'Dữ liệu kiểm thử giao diện'};
    else if (pathname === '/api/tutor/complete') body = {completion:''};
    else if (pathname === '/api/tutor/chat') {
      await new Promise(resolve => setTimeout(resolve,600));
      return route.fulfill({status:200,contentType:'application/x-ndjson',body:
        JSON.stringify({delta:result.reply})+'\n'+JSON.stringify({done:true,model:'qwen2.5-coder:7b',result})+'\n'});
    } else { status = 404; body = {error:'Chức năng ngoài phạm vi kiểm thử'}; }
    await route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
  });
  const url = 'http://127.0.0.1:' + server.address().port;
  try {
    await page.goto(url,{waitUntil:'domcontentloaded'});
    await page.screenshot({path:path.join(output,'01-login.png')});
    check('login centered and visible', await page.locator('#login-form').isVisible());
    check('background loaded', await page.evaluate(() => new Promise(resolve => {const i=new Image();i.onload=()=>resolve(true);i.onerror=()=>resolve(false);i.src='/ocean-station-bg.png';})));
    await page.locator('#student-account').fill(student.username);
    await page.locator('#student-password').fill('demo');
    await page.locator('#login-form button[type=submit]').click();
    await page.locator('#intro-screen').waitFor({state:'visible'});
    check('four language beacons',await page.locator('[data-intro-language]').count()===4);
    for (const language of ['c','cpp','java','python']) {
      await page.locator('[data-intro-language='+language+']').click();
      assert.equal(await page.locator('#language').inputValue(),language);
      assert.equal(await page.locator('[data-intro-language='+language+']').getAttribute('aria-pressed'),'true');
    }
    check('all four beacons select matching language',true);
    await page.locator('[data-intro-language=c]').click();
    check('language information', (await page.locator('#intro-language-title').textContent())==='C');
    await page.screenshot({path:path.join(output,'02-welcome.png')});
    await page.locator('#skip-intro').click();
    await page.locator('#ide-screen').waitFor({state:'visible'});
    await page.waitForFunction(() => window.monaco && monaco.editor.getModels().some(m=>m.getLanguageId()==='c'),null,{timeout:60000});
    check('intro language becomes editor language',true);
    const layout = await page.evaluate(() => {const e=document.getElementById('editor-panel').getBoundingClientRect();const c=document.getElementById('chat-panel').getBoundingClientRect();return {ratio:e.width/(e.width+c.width),bottom:Math.max(e.bottom,c.bottom),w:document.documentElement.scrollWidth,v:innerWidth,h:innerHeight};});
    check('desktop ratio 55/45',Math.abs(layout.ratio-.55)<.01);
    check('desktop fits viewport',layout.w<=layout.v && layout.bottom<=layout.h);
    await page.locator('#language').selectOption('python');
    const mainEditor = () => page.evaluate(() => monaco.editor.getModels().find(m=>m.getLanguageId()==='python' && !m.isDisposed()).getValue());
    await page.evaluate(code => monaco.editor.getModels().find(m=>m.getLanguageId()==='python').setValue(code),originalCode);
    await page.locator('#task-mode').selectOption('review');
    await page.locator('#attach-code').check();
    await page.locator('#question').fill('Hàm double cần trả về gấp đôi x. Hãy tìm và sửa lỗi.');
    await page.locator('#send').click();
    await page.locator('.chat-waiting').waitFor({state:'visible'});
    check('waiting dots while pending',await page.locator('.waiting-dots i').count()===3);
    await page.locator('.issue-card button').waitFor();
    await page.locator('.line-error-badge').first().hover();
    await page.locator('.monaco-hover').filter({hasText:'Giá trị trả về'}).first().waitFor({state:'visible'});
    check('end-of-line error tooltip',true);
    check('waiting cleared after response',await page.locator('.chat-waiting').count()===0);
    check('AI avatar faculty logo',await page.locator('.ai-avatar').count()>0);
    await page.locator('.issue-card button').first().click();
    await page.locator('.line-focus-highlight').first().waitFor({state:'attached'});
    check('line focus decoration',await page.locator('.line-focus-highlight').count()>0);
    await page.locator('.code-comparison summary').click();
    await page.locator('.code-diff .monaco-diff-editor').waitFor();
    check('inline diff rendered',await page.locator('.code-diff .monaco-diff-editor').isVisible());
    await page.screenshot({path:path.join(output,'03-workspace.png')});
    await page.locator('[data-apply-fix]').click();
    check('apply exact full fix',(await mainEditor())===fixedCode);
    await page.keyboard.press('Control+z');
    check('undo restores original',(await mainEditor())===originalCode);
    await page.locator('#focus-mode').click();
    check('focus pauses scene',await page.locator('body').evaluate(e=>e.classList.contains('motion-paused')));
    await page.locator('#focus-mode').click();
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.waitForFunction(()=>document.body.classList.contains('motion-paused'));
    check('reduced motion honored',await page.locator('body').evaluate(e=>e.classList.contains('motion-paused')));
    await page.emulateMedia({reducedMotion:'no-preference'});
    await page.waitForFunction(()=>!document.body.classList.contains('motion-paused'));
    await page.setViewportSize({width:390,height:844});
    await page.locator('#tab-chat').click();
    check('mobile chat tab',await page.locator('#chat-panel').isVisible() && !(await page.locator('#editor-panel').isVisible()));
    await page.screenshot({path:path.join(output,'04-mobile-chat.png')});
    await page.locator('#tab-editor').click();
    check('mobile editor preserved',(await mainEditor())===originalCode);
    await page.screenshot({path:path.join(output,'05-mobile-editor.png')});
    check('mobile change-password accessible',await page.locator('#change-password').isVisible());
    const mobile = await page.evaluate(()=>({w:document.documentElement.scrollWidth,v:innerWidth,send:document.getElementById('editor-panel').getBoundingClientRect().bottom,h:innerHeight}));
    check('mobile viewport', mobile.w<=mobile.v && mobile.send<=mobile.h);
    await page.setViewportSize({width:1920,height:1080});
    await page.locator('#clear-chat').click();
    check('diff disposed on clear',await page.evaluate(code=>!monaco.editor.getModels().some(m=>m.getValue()===code),fixedCode));
    await page.locator('#question').fill('Kiểm tra lại hàm double.');
    await page.locator('#send').click();
    await page.locator('.chat-waiting').waitFor({state:'visible'});
    await page.evaluate(()=>monaco.editor.getModels().find(m=>m.getLanguageId()==='python').setValue('print("Mã mới")'));
    await page.locator('[data-apply-fix]').waitFor();
    check('stale patch cannot be applied',await page.locator('[data-apply-fix]').isDisabled());
    await page.locator('#clear-chat').click();
    await page.route('**/api/tutor/chat', async route => route.fulfill({status:200,contentType:'application/x-ndjson',body:JSON.stringify({delta:'```python\nprint("preview")\n```'})+'\n'+JSON.stringify({error:'Phản hồi kiểm thử bị ngắt'})+'\n'}));
    await page.locator('#question').fill('Kiểm tra đường lỗi mạng.');
    await page.locator('#send').click();
    await page.locator('#status').filter({hasText:'Gửi lại'}).waitFor();
    check('rejected preview offers no insertion control',await page.locator('.insert-btn').count()===0);
    await page.locator('#clear-chat').click();
    await page.screenshot({path:path.join(output,'06-desktop-large.png')});
    await page.locator('#logout').click();
    await page.locator('#login-screen').waitFor({state:'visible'});
    await page.locator('#student-account').fill(student.username);
    await page.locator('#student-password').fill('demo');
    await page.locator('#login-form button[type=submit]').click();
    await page.locator('#intro-screen').waitFor({state:'visible'});
    await page.locator('#enter-workspace').click();
    await page.locator('body.is-diving').waitFor({state:'attached'});
    await page.locator('#ide-screen').waitFor({state:'visible'});
    check('dive transition completes',!(await page.locator('body').evaluate(e=>e.classList.contains('is-diving'))));
    const earlyContext = await browser.newContext({viewport:{width:1366,height:768},ignoreHTTPSErrors:true});
    const earlyPage = await earlyContext.newPage();
    let releaseLoader;
    const loaderGate = new Promise(resolve => {releaseLoader=resolve;});
    await earlyPage.route('**/vs/loader.js', async route => {await loaderGate;await route.continue();});
    await earlyPage.route('**/api/**', route => {
      const endpoint=new URL(route.request().url()).pathname;
      return route.fulfill({status:endpoint.endsWith('/me')?401:200,contentType:'application/json',body:JSON.stringify(endpoint.endsWith('/login')?student:{ready:true,ollama_connected:true,model:'ui-fixture'})});
    });
    await earlyPage.goto(url,{waitUntil:'commit'});
    await earlyPage.locator('#student-account').fill(student.username);
    await earlyPage.locator('#student-password').fill('demo');
    await earlyPage.locator('#login-form button[type=submit]').click();
    await earlyPage.locator('[data-intro-language=java]').click();
    await earlyPage.locator('#skip-intro').click();
    releaseLoader();
    await earlyPage.waitForFunction(()=>window.monaco && monaco.editor.getModels().some(m=>m.getLanguageId()==='java'),null,{timeout:60000});
    check('language selected before Monaco loads',true);
    await earlyContext.close();
    check('no runtime page errors',report.errors.length===0);
  } finally {
    fs.writeFileSync(path.join(output,'ui-results.json'),JSON.stringify(report,null,2));
    await browser.close();
    await new Promise(resolve=>server.close(resolve));
  }
  console.log(JSON.stringify(report,null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1;});

