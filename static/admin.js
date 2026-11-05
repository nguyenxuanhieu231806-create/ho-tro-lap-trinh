(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  let revision='',batch='',job='',credentialText='',pollController=null,credentialTimer=null;
  const node=(tag,text,className)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;};
  const body=data=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  async function api(path,options={}){
    const {timeoutMs=60000,...requestOptions}=options;
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
    try{
      const response=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:controller.signal,...requestOptions});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error || data.message || 'Không hoàn tất được thao tác quản trị.');
      return data;
    }catch(error){if(error.name==='AbortError')throw new Error('Yêu cầu quá thời gian chờ. Hãy kiểm tra lại trạng thái trước khi thực hiện lại.');throw error;}
    finally{clearTimeout(timer);}
  }
  function status(id,text,error=false){$(id).textContent=text;$(id).classList.toggle('error',error);}
  function summary(counts){
    if(!counts || typeof counts!=='object')return '';
    const names={total:'Tổng',valid:'Hợp lệ',new:'Mới',ready:'Sẵn sàng',success:'Thành công',created:'Đã cấp',failed:'Thất bại',invalid:'Sai dữ liệu',errors:'Lỗi',duplicate:'Trùng',duplicates:'Trùng',conflict:'Xung đột',skipped:'Bỏ qua'};
    return Object.entries(counts).filter(([,value])=>typeof value==='number').map(([key,value])=>(names[key]||key)+': '+value).join(' · ');
  }
  function listOf(data,key){return Array.isArray(data)?data:(data[key]||data.items||[]);}
  function stateLabel(value){return ({staged:'Chờ kiểm tra',draft:'Bản nháp',published:'Đã công bố',completed:'Hoàn tất',committed:'Đã xác nhận',ready:'Sẵn sàng',pending:'Đang chờ',running:'Đang xử lý',success:'Đã cấp',failed:'Thất bại',cancelled:'Đã dừng',valid:'Hợp lệ',new:'Mới',created:'Đã cấp',imported:'Đã nhập',invalid:'Sai dữ liệu',duplicate:'Trùng',conflict:'Xung đột',skipped:'Bỏ qua',error:'Lỗi'})[value]||value||'';}
  async function documents(){
    const data=await api('/api/admin/documents');
    const select=$('admin-document-list');select.replaceChildren(new Option('Chọn bản nạp để xem lại',''));
    const target=$('admin-document-target'),selectedTarget=target.value;target.replaceChildren(new Option('Tài liệu mới',''));
    const seenTargets=new Set();
    for(const doc of listOf(data,'documents')){
      const id=doc.latest_revision_id || doc.revision_id || doc.active_revision_id || doc.id;
      if(id)select.append(new Option((doc.file_name||doc.name||doc.title||'Tài liệu')+' · '+stateLabel(doc.status||doc.state||'Đã nạp'),id));
      if(doc.id&&!seenTargets.has(doc.id)){target.append(new Option('Tạo phiên bản mới của '+(doc.file_name||doc.name||doc.title||'Tài liệu'),doc.id));seenTargets.add(doc.id);}
    }
    target.value=selectedTarget;
  }
  function renderBlocks(values){
    const target=$('admin-document-blocks');target.replaceChildren();
    for(const block of values || []){
      const item=node('div',undefined,'admin-block');
      item.append(node('strong',[block.kind||block.type||'Đoạn',block.locator||block.section_path||''].filter(Boolean).join(' · ')));
      item.append(node('pre',block.text||block.content||''));target.append(item);
    }
    if(!target.childElementCount)target.append(node('p','Chưa trích được nội dung văn bản.'));
  }
  function renderImages(values){
    const target=$('admin-document-images');target.replaceChildren();
    for(const image of values || []){
      const id=image.id || image.image_id;if(!id)continue;
      const imageRevision=revision;
      const card=node('div',undefined,'admin-image');
      const picture=node('img');picture.src='/api/admin/documents/'+encodeURIComponent(imageRevision)+'/images/'+encodeURIComponent(id);picture.alt=image.caption||'Ảnh trong tài liệu';card.append(picture);
      card.append(node('p',[image.caption,image.locator].filter(Boolean).join(' · ')||'Ảnh cần kiểm tra liên kết và nội dung.','admin-note'));
      const label=node('label','Mô tả nội dung đã đối chiếu với ảnh gốc:');
      const description=node('textarea');description.value=image.description||image.reviewed_text||'';description.maxLength=8000;
      label.append(description);card.append(label);
      const decorative=node('input');decorative.type='checkbox';decorative.checked=Boolean(image.decorative);
      const decorativeLabel=node('label');decorativeLabel.append(decorative,document.createTextNode(' Ảnh trang trí, không dùng làm bằng chứng trả lời'));card.append(decorativeLabel);
      const controls=node('div',undefined,'admin-controls'),save=node('button','Lưu xác nhận ảnh');save.type='button';controls.append(save);card.append(controls);
      const feedback=node('p',image.reviewed?'Ảnh đã được xác nhận.':'Chưa được xác nhận.','admin-note');card.append(feedback);
      save.onclick=async()=>{save.disabled=true;try{await api('/api/admin/documents/'+encodeURIComponent(imageRevision)+'/images/'+encodeURIComponent(id)+'/review',body({description:description.value.trim(),decorative:decorative.checked}));feedback.textContent='Đã lưu xác nhận. Hãy bảo đảm mô tả không thêm thông tin ngoài ảnh.';}catch(error){feedback.textContent=error.message;}finally{save.disabled=false;}};
      target.append(card);
    }
  }
  function renderRevision(data){
    const info=data.revision||data;
    revision=info.revision_id||info.id||data.revision_id||revision;
    if(!revision)throw new Error('Bản nạp chưa có mã định danh.');
    $('admin-document-preview').hidden=false;
    $('admin-preview-title').textContent=info.file_name||info.name||data.file_name||'Bản nạp tài liệu';
    const warnings=[...(info.warnings||data.warnings||[]),...(info.unsupported||data.unsupported||[]).map(value=>'Nội dung chưa được hỗ trợ: '+value)];
    $('admin-document-warnings').replaceChildren();
    if(warnings.length){const list=node('ul');for(const warning of warnings)list.append(node('li',typeof warning==='string'?warning:(warning.message||warning.reason||'Cần kiểm tra nội dung.')));$('admin-document-warnings').append(list);}
    renderBlocks(info.blocks||data.blocks||[]);renderImages(info.images||data.images||[]);
  }
  $('admin-document-form').onsubmit=async event=>{
    event.preventDefault();const file=$('admin-document-file').files[0];if(!file)return;
    const button=event.target.querySelector('button');button.disabled=true;revision='';$('admin-document-preview').hidden=true;
    status('admin-document-status','Đang đọc tài liệu và kiểm tra cấu trúc…');
    const form=new FormData();form.append('file',file);
    if($('admin-document-target').value)form.append('document_id',$('admin-document-target').value);
    try{const data=await api('/api/admin/documents/preview',{method:'POST',body:form});const detail=Array.isArray(data.blocks)?data:await api('/api/admin/documents/'+encodeURIComponent(data.revision_id||data.id));renderRevision(detail);status('admin-document-status',data.duplicate?'Tệp này đã được nạp trước đó. Đang hiển thị bản đã có.':'Đã đọc bản xem trước. Kiểm tra nội dung, ảnh và cảnh báo trước khi công bố.');await documents();}
    catch(error){status('admin-document-status',error.message,true);}finally{button.disabled=false;}
  };
  $('admin-refresh-documents').onclick=()=>documents().catch(error=>status('admin-document-status',error.message,true));
  $('admin-document-list').onchange=async()=>{const id=$('admin-document-list').value;if(!id)return;try{revision=id;renderRevision(await api('/api/admin/documents/'+encodeURIComponent(id)));status('admin-document-status','Đã tải bản nạp.');}catch(error){status('admin-document-status',error.message,true);}};
  async function pollJob(id){
    pollController?.abort();const active=new AbortController();pollController=active;
    const deadline=Date.now()+600000;
    while(!active.signal.aborted && Date.now()<deadline){
      const data=await api('/api/admin/jobs/'+encodeURIComponent(id));
      const state=data.status||data.state||'';
      status('admin-document-status',data.message||data.phase||('Trạng thái nạp: '+state));
      if(['completed','published','ready','success'].includes(state)){status('admin-document-status',data.message||'Đã công bố tài liệu vào kho hỏi đáp.');return;}
      if(['failed','cancelled','canceled'].includes(state))throw new Error(data.error||data.message||'Lượt nạp đã dừng hoặc chưa hoàn tất.');
      await new Promise(resolve=>setTimeout(resolve,900));
    }
    if(active.signal.aborted)throw new Error('Đã dừng theo dõi lượt nạp.');
    throw new Error('Lượt nạp vẫn đang xử lý. Hãy làm mới và kiểm tra trạng thái trước khi nạp lại.');
  }
  $('admin-publish').onclick=async()=>{
    if(!revision)return;const button=$('admin-publish');button.disabled=true;
    $('admin-reindex').disabled=true;
    status('admin-document-status','Đang tạo embedding và kiểm tra khả năng truy xuất…');
    try{const data=await api('/api/admin/documents/'+encodeURIComponent(revision)+'/publish',body({}));job=data.job_id||'';if(job){$('admin-cancel-job').hidden=false;await pollJob(job);}else{status('admin-document-status',data.message||'Đã nạp tài liệu vào kho hỏi đáp.');}await documents();}
    catch(error){status('admin-document-status',error.message,true);}finally{button.disabled=false;$('admin-reindex').disabled=false;$('admin-cancel-job').hidden=true;job='';}
  };
  $('admin-reindex').onclick=async()=>{
    const button=$('admin-reindex');button.disabled=true;$('admin-publish').disabled=true;
    status('admin-document-status','Đang dựng và kiểm tra chỉ mục tìm kiếm mới…');
    try{const data=await api('/api/admin/index/reindex',body({}));job=data.job_id||'';if(job){$('admin-cancel-job').hidden=false;await pollJob(job);}else status('admin-document-status',data.message||'Đã dựng lại chỉ mục.');await documents();}
    catch(error){status('admin-document-status',error.message,true);}finally{button.disabled=false;$('admin-publish').disabled=false;$('admin-cancel-job').hidden=true;job='';}
  };
  $('admin-cancel-job').onclick=async()=>{if(!job)return;try{await api('/api/admin/jobs/'+encodeURIComponent(job)+'/cancel',body({}));status('admin-document-status','Đã gửi yêu cầu dừng; đang chờ dọn lượt nạp.');}catch(error){status('admin-document-status',error.message,true);}};
  function clearCredentials(){clearTimeout(credentialTimer);credentialText='';$('admin-credential-text').textContent='';$('admin-credentials').hidden=true;}
  function renderRows(data){
    const rows=data.rows||data.results||[];const target=$('admin-import-rows');target.replaceChildren();
    for(const row of rows){
      const profile=row.profile||row.student||row.normalized||row;
      const tr=node('tr');
      const reason=Array.isArray(row.errors)?row.errors.join('; '):(row.reason||row.message||'');
      for(const value of [row.row||row.row_number||row.index||'',profile.email||profile.username||'',profile.student_id||profile.mssv||'',profile.name||profile.full_name||'',[(profile.class_name||profile.class||''),profile.study_year?'Năm '+profile.study_year:''].filter(Boolean).join(' / '),[stateLabel(row.status||row.action),reason].filter(Boolean).join(' · ')])tr.append(node('td',String(value)));
      target.append(tr);
    }
    $('admin-import-counts').textContent=summary(data.counts||data.summary);
  }
  $('admin-student-form').onsubmit=async event=>{
    event.preventDefault();const file=$('admin-student-file').files[0];if(!file)return;
    const button=event.target.querySelector('button');button.disabled=true;batch='';clearCredentials();$('admin-import-preview').hidden=true;
    status('admin-student-status','Đang kiểm tra định dạng, dữ liệu và tài khoản trùng…');
    const form=new FormData();form.append('file',file);
    try{const data=await api('/api/admin/students/import/preview',{method:'POST',body:form});batch=data.batch_id||'';renderRows(data);$('admin-import-preview').hidden=false;$('admin-import-confirm').disabled=!batch;status('admin-student-status','Đã xem trước. Chưa cấp hoặc đổi tài khoản. Kiểm tra từng dòng trước khi xác nhận.');}
    catch(error){status('admin-student-status',error.message,true);}finally{button.disabled=false;}
  };
  $('admin-import-confirm').onclick=async()=>{
    if(!batch || !confirm('Cấp tài khoản cho các dòng hợp lệ? Những tài khoản đã có sẽ không bị ghi đè.'))return;
    const button=$('admin-import-confirm');button.disabled=true;clearCredentials();status('admin-student-status','Đang xác nhận và cấp tài khoản…');
    try{
      const data=await api('/api/admin/students/import/'+encodeURIComponent(batch)+'/confirm',{...body({}),timeoutMs:180000});renderRows(data);
      const values=data.credentials||[];
      if(values.length){credentialText=values.map(row=>'Email: '+(row.email||row.username||'')+'\nMật khẩu khởi tạo: '+(row.password||'')).join('\n\n');$('admin-credential-text').textContent=credentialText;$('admin-credentials').hidden=false;credentialTimer=setTimeout(clearCredentials,300000);}
      status('admin-student-status',data.message||('Đã hoàn tất. '+summary(data.counts||data.summary)));batch='';
    }catch(error){status('admin-student-status',error.message,true);button.disabled=false;}
  };
  $('admin-clear-credentials').onclick=clearCredentials;
  $('admin-download-credentials').onclick=()=>{if(!credentialText)return;const link=node('a');const url=URL.createObjectURL(new Blob([credentialText+'\n'],{type:'text/plain;charset=utf-8'}));link.href=url;link.download='thong-tin-cap-tai-khoan.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  window.addEventListener('pagehide',()=>{pollController?.abort();clearCredentials();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)clearCredentials();});
  (async()=>{
    try{
      const me=await api('/api/auth/me');
      if(me.role!=='admin')throw new Error('Tài khoản này chưa có quyền quản trị. Chủ dự án cần tạo quản trị cục bộ bằng lệnh: python manage_accounts.py create-admin');
      $('admin-work').hidden=false;status('admin-auth-status','Đã xác thực quản trị: '+(me.name||me.username));await documents();
    }catch(error){status('admin-auth-status',error.message+' · Đăng nhập đúng tài khoản tại Web IDE trước khi mở trang này.',true);}
  })();
})();
