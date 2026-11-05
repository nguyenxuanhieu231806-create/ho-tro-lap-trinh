// Uses a temporary live API server supplied by verify-api-live.py; no API mocks.
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const {chromium} = require('C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const report = {mode:'actual browser, actual HTTP runner, actual Docker; temporary auth DB; Ollama warmup/health omitted',checks:[],errors:[]};
function check(name, condition) {assert.ok(condition,name);report.checks.push(name);}
async function main() {
  assert.ok(process.env.FIT_RUN_TEST_BASE_URL,'Run via verify-api-live.py');
  const browser = await chromium.launch({channel:'msedge',headless:true});
  const page = await browser.newPage({viewport:{width:1366,height:768},ignoreHTTPSErrors:true});
  page.on('pageerror',error=>report.errors.push(error.message));
  try {
    await page.goto(process.env.FIT_RUN_TEST_BASE_URL,{waitUntil:'domcontentloaded'});
    await page.locator('#student-account').fill(process.env.FIT_RUN_TEST_EMAIL);
    await page.locator('#student-password').fill(process.env.FIT_RUN_TEST_PASSWORD);
    await page.locator('#login-form button[type=submit]').click();
    await page.locator('#skip-intro').click();
    await page.waitForFunction(()=>window.monaco && monaco.editor.getModels().some(model=>model.getLanguageId()==='python'));
    await page.locator('#completion-enabled').uncheck();
    const original='a, b = map(int, input().split())\nprint(a + b)\n';
    await page.evaluate(code=>monaco.editor.getModels().find(model=>model.getLanguageId()==='python').setValue(code),original);
    await page.locator('#run-panel summary').click();
    await page.locator('#runner-readiness').filter({hasText:'sẵn sàng'}).waitFor();
    check('live runner readiness displayed',true);
    await page.locator('#run-input').fill('7 5');
    await page.locator('#code-run').click();
    await page.waitForFunction(()=>document.getElementById('run-status').dataset.kind==='completed',null,{timeout:45000});
    check('real Python stdin prints sum in Run pane',await page.locator('#run-output').textContent()==='12\n');
    check('actual exit code displayed',(await page.locator('#run-meta').textContent()).includes('Mã thoát 0'));
    await page.screenshot({path:path.join(__dirname,'03-run-real-desktop.png')});
    await page.evaluate(()=>{
      const editor=monaco.editor.getEditors().find(editor=>editor.getModel()?.getLanguageId()==='python');
      editor.pushUndoStop();
      editor.executeEdits('validation-edit',[{range:editor.getModel().getFullModelRange(),text:'a, b = map(int, input().split())\nprint(a * b)\n',forceMoveMarkers:true}]);
      editor.pushUndoStop();
    });
    check('changed code marks actual earlier result stale',await page.locator('#run-stale').isVisible());
    await page.locator('#code-run').click();
    await page.waitForFunction(()=>document.getElementById('run-status').dataset.kind==='completed',null,{timeout:45000});
    check('next click executes changed source',await page.locator('#run-output').textContent()==='35\n');
    await page.evaluate(()=>monaco.editor.getEditors().find(editor=>editor.getModel()?.getLanguageId()==='python').trigger('validation','undo',null));
    check('editor Undo remains available',await page.evaluate(()=>monaco.editor.getModels().find(model=>model.getLanguageId()==='python').getValue())===original);
    check('no page runtime errors',report.errors.length===0);
    report.state='passed';
  } catch(error) {
    report.state='failed';report.error=error.message;throw error;
  } finally {
    fs.writeFileSync(path.join(__dirname,'ui-live-results.json'),JSON.stringify(report,null,2));
    await browser.close();
  }
  console.log(JSON.stringify(report,null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
