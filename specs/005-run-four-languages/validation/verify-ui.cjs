const fs = require('fs');
const path = require('path');
const http = require('http');
const assert = require('assert/strict');
const {chromium} = require('C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

const project = path.resolve(__dirname, '../../..');
const staticDir = path.join(project, 'static');
const report = {mode:'controlled API fixture; no student program executed', checks:[], errors:[]};
const student = {username:'student@example.test',name:'Người học',student_id:'DEMO001',class_name:'CNTT3.K25',study_year:3};
const source = 'a, b = map(int, input().split())\nprint("Tổng =", a + b)\n';
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css','.png':'image/png','.wasm':'application/wasm'};
function check(name, condition) {
  assert.ok(condition, name);
  report.checks.push(name);
}
async function main() {
  const server = http.createServer((request,response) => {
    const pathname = decodeURIComponent(new URL(request.url,'http://local').pathname);
    const filename = path.resolve(staticDir, '.'+(pathname==='/'?'/index.html':pathname));
    if (!filename.startsWith(staticDir+path.sep) || !fs.existsSync(filename) || !fs.statSync(filename).isFile()) {
      response.writeHead(404);response.end();return;
    }
    response.writeHead(200,{'Content-Type':types[path.extname(filename)] || 'application/octet-stream','Cache-Control':'no-store'});
    fs.createReadStream(filename).pipe(response);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser = await chromium.launch({channel:'msedge',headless:true});
  const page = await browser.newPage({viewport:{width:1366,height:768},ignoreHTTPSErrors:true});
  page.on('pageerror',error=>report.errors.push(error.message));
  let lastPayload, responseDelay=0, output='Tổng = 8\n';
  await page.route('**/api/**',async route => {
    const endpoint=new URL(route.request().url()).pathname;
    if (endpoint==='/api/tutor/run') {
      lastPayload=route.request().postDataJSON();
      const result={language:lastPayload.language,status:'completed',stdout:output,stderr:'',exit_code:0,duration_ms:18,message:'Đã chạy xong với dữ liệu đã nhập.'};
      if (responseDelay) await new Promise(resolve=>setTimeout(resolve,responseDelay));
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(result)}).catch(()=>{});
    }
    if (endpoint==='/api/auth/me') return route.fulfill({status:401,json:{error:'Chưa đăng nhập'}});
    if (endpoint==='/api/auth/login') return route.fulfill({json:student});
    if (endpoint==='/api/health') return route.fulfill({json:{ready:true,ollama_connected:true,model:'ui-fixture',message:'Dữ liệu kiểm thử giao diện'}});
    if (endpoint==='/api/tutor/runner') return route.fulfill({json:{available:false,reason:'Môi trường chạy chưa sẵn sàng — dữ liệu kiểm thử.',languages:['c','cpp','java','python'],runtime_limit_seconds:3}});
    return route.fulfill({json:{completion:''}});
  });
  try {
    await page.goto('http://127.0.0.1:'+server.address().port,{waitUntil:'domcontentloaded'});
    await page.locator('#student-account').fill(student.username);
    await page.locator('#student-password').fill('demo');
    await page.locator('#login-form button[type=submit]').click();
    await page.locator('#skip-intro').click();
    await page.waitForFunction(()=>window.monaco && monaco.editor.getModels().some(model=>model.getLanguageId()==='python'));
    await page.evaluate(code=>monaco.editor.getModels().find(model=>model.getLanguageId()==='python').setValue(code),source);
    await page.locator('#run-panel summary').click();
    await page.locator('#runner-readiness').filter({hasText:'dữ liệu kiểm thử'}).waitFor();
    check('unavailable readiness allows retry',await page.locator('#code-run').isEnabled());
    await page.locator('#run-input').fill('3 5');
    await page.locator('#code-run').click();
    await page.waitForFunction(()=>document.getElementById('run-status').dataset.kind==='completed');
    check('snapshot contains exact source',lastPayload.current_code===source);
    check('snapshot contains language',lastPayload.language==='python');
    check('snapshot contains stdin',lastPayload.stdin==='3 5');
    check('stdout rendered',await page.locator('#run-output').textContent()==='Tổng = 8\n');
    check('exit code and duration shown',(await page.locator('#run-meta').textContent()).includes('Mã thoát 0') && (await page.locator('#run-meta').textContent()).includes('18 ms'));
    const desktop=await page.evaluate(()=>{
      const e=document.getElementById('editor-panel').getBoundingClientRect(), c=document.getElementById('chat-panel').getBoundingClientRect();
      return {ratio:e.width/(e.width+c.width),bottom:Math.max(e.bottom,c.bottom),width:document.documentElement.scrollWidth,viewport:innerWidth,height:innerHeight};
    });
    check('desktop remains 55/45',Math.abs(desktop.ratio-.55)<.01);
    check('desktop fits viewport',desktop.width<=desktop.viewport && desktop.bottom<=desktop.height);
    await page.screenshot({path:path.join(__dirname,'01-run-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    await page.locator('#tab-editor').click();
    check('mobile Run button accessible',await page.locator('#code-run').isVisible());
    check('mobile no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    check('mobile pane within viewport',await page.locator('#editor-panel').evaluate(element=>element.getBoundingClientRect().bottom<=innerHeight));
    await page.screenshot({path:path.join(__dirname,'02-run-mobile.png')});
    await page.setViewportSize({width:1366,height:768});
    output='<img src=x onerror=alert(1)>';
    await page.locator('#code-run').click();
    await page.waitForFunction(()=>document.getElementById('run-status').dataset.kind==='completed');
    check('stdout remains literal text',await page.locator('#run-output').textContent()===output && await page.locator('#run-output img').count()===0);
    responseDelay=800;
    await page.locator('#code-run').click();
    await page.evaluate(()=>monaco.editor.getModels().find(model=>model.getLanguageId()==='python').setValue('print("Mã mới")\n'));
    await page.waitForFunction(()=>document.getElementById('run-status').dataset.kind==='completed');
    check('source change marks result stale',await page.locator('#run-stale').isVisible());
    await page.locator('#language').selectOption('cpp');
    check('language change keeps stale warning',await page.locator('#run-stale').isVisible());
    await page.locator('#language').selectOption('python');
    responseDelay=2000;
    await page.locator('#code-run').click();
    await page.locator('#code-stop').click();
    await page.waitForFunction(()=>document.getElementById('run-status').dataset.kind==='cancelled');
    check('Stop cancels pending request',await page.locator('#code-stop').isHidden());
    check('Run reenabled after abort',await page.locator('#code-run').isEnabled());
    check('no page runtime errors',report.errors.length===0);
  } finally {
    fs.writeFileSync(path.join(__dirname,'ui-results.json'),JSON.stringify(report,null,2));
    await browser.close();
    await new Promise(resolve=>server.close(resolve));
  }
  console.log(JSON.stringify(report,null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1;});

