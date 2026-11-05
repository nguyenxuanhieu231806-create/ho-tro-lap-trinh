(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  if (!$('rag-panel')) return;
  let owner = '', conversation = '', loaded = false, controller = null;
  let mode = 'code';
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  function busy(value) {
    const changed = window.tutorRagBusy !== value;
    window.tutorRagBusy = value;
    if (changed) window.dispatchEvent(new CustomEvent('tutor-rag-busy', {detail:value}));
    $('rag-stop').hidden = !value;
    $('rag-send').disabled = value || Boolean(window.tutorCodeBusy);
    $('rag-new').disabled = value;
    $('rag-delete').disabled = value || !conversation;
    $('rag-conversation').disabled = value;
    $('mode-code').disabled = value || Boolean(window.tutorCodeBusy);
    $('mode-documents').disabled = value || Boolean(window.tutorCodeBusy);
  }
  async function api(path, options={}) {
    const timeout = new AbortController();
    const {signal:externalSignal,...requestOptions}=options;
    const cancel=()=>timeout.abort();
    externalSignal?.addEventListener('abort',cancel,{once:true});
    if(externalSignal?.aborted)timeout.abort();
    const timer = setTimeout(() => timeout.abort(), 20000);
    try {
      const response = await fetch(path, {credentials:'same-origin', signal:timeout.signal, ...requestOptions});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || data.message || 'Không hoàn tất được yêu cầu tài liệu.');
      return data;
    } finally { clearTimeout(timer);externalSignal?.removeEventListener('abort',cancel); }
  }
  const json = body => ({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  function note(text) { $('rag-status').textContent = text; }
  function clearLog() {
    $('rag-log').replaceChildren(node('p','Hỏi nội dung có trong kho tài liệu. Lịch sử chỉ giúp hiểu câu hỏi; câu trả lời vẫn phải có nguồn.','rag-empty'));
  }
  function bubble(role, text) {
    $('rag-log').querySelector('.rag-empty')?.remove();
    const box = node('article',undefined,'rag-message '+(role==='user'?'user':'assistant'));
    box.append(node('span',role==='user'?'Bạn':'Trợ lý tài liệu','rag-message-label'));
    const content = node('div',text,'rag-message-text'); box.append(content);
    $('rag-log').append(box); $('rag-log').scrollTop = $('rag-log').scrollHeight;
    return {box,content};
  }
  async function source(id) {
    $('rag-source-title').textContent = 'Đang tải nguồn…';
    $('rag-source-locator').textContent = '';
    $('rag-source-content').textContent = '';
    if (!$('rag-source-dialog').open) $('rag-source-dialog').showModal();
    try {
      const data = await api('/api/rag/sources/'+encodeURIComponent(id));
      $('rag-source-title').textContent = data.file_name || data.title || 'Nguồn tài liệu';
      $('rag-source-locator').textContent = [data.locator,Number.isInteger(data.page)&&data.page>0?'Trang '+data.page:null].filter(Boolean).join(' · ');
      $('rag-source-content').textContent = data.text || data.content || 'Nguồn không còn khả dụng.';
    } catch(error) { $('rag-source-content').textContent = error.message; }
  }
  function citations(target, values) {
    if (!Array.isArray(values) || !values.length) return;
    const list = node('div',undefined,'rag-citations');
    for (const [index,item] of values.entries()) {
      if (!item || typeof item !== 'object' || !(item.id || item.chunk_id)) continue;
      const id = item.id || item.chunk_id;
      const label = [item.label || item.citation_id || '['+(index+1)+']',item.file_name || item.title || 'Tài liệu',item.locator,Number.isInteger(item.page)&&item.page>0?'trang '+item.page:null].filter(Boolean).join(' · ');
      const button = node('button',label,'rag-citation'); button.type='button';button.onclick=()=>source(id);list.append(button);
    }
    if (list.childElementCount) target.append(list);
  }
  async function refreshConversations(selected=conversation) {
    const requestOwner=owner;
    const data = await api('/api/rag/conversations');
    if(owner!==requestOwner)return;
    const rows = Array.isArray(data)?data:(data.conversations || data.items || []);
    const select = $('rag-conversation'); select.replaceChildren(new Option('Hội thoại mới',''));
    for (const row of rows) {
      const id = row.id || row.conversation_id;
      if (id) select.append(new Option(row.title || 'Hội thoại tài liệu',id));
    }
    select.value = selected || '';
  }
  async function refreshLibrary() {
    const data = await api('/api/rag/documents');
    const rows = Array.isArray(data)?data:(data.documents || data.items || []);
    $('rag-library-note').textContent = rows.length
      ? `${rows.length} tài liệu đã công bố · chỉ trả lời nội dung có bằng chứng và dẫn nguồn.`
      : 'Kho chưa có tài liệu được công bố. Quản trị viên cần nạp tài liệu trước khi hỏi đáp.';
  }
  async function enterMode(next) {
    if (controller || window.tutorCodeBusy) return;
    mode=next;
    $('chat-panel').dataset.assistantMode=next;
    $('rag-panel').hidden=next!=='documents';
    $('mode-code').setAttribute('aria-pressed',String(next==='code'));
    $('mode-documents').setAttribute('aria-pressed',String(next==='documents'));
    if (next==='documents' && !loaded) {
      loaded=true;note('Đang tải kho và hội thoại…');
      try { await Promise.all([refreshConversations(),refreshLibrary()]);note('Sẵn sàng'); }
      catch(error) { loaded=false;note(error.message); }
    }
    window.dispatchEvent(new Event('resize'));
  }
  function sessionChanged(student) {
    if (!student) return;
    $('admin-link').hidden=student.role!=='admin';
    if (student.username===owner) return;
    controller?.abort(); controller=null;owner=student.username || '';conversation='';loaded=false;
    if($('rag-source-dialog').open)$('rag-source-dialog').close();
    $('rag-conversation').replaceChildren(new Option('Hội thoại mới',''));clearLog();busy(false);
    if (mode==='documents') enterMode(mode);
  }
  $('mode-code').onclick=()=>enterMode('code');
  $('mode-documents').onclick=()=>enterMode('documents');
  $('rag-source-close').onclick=()=>$('rag-source-dialog').close();
  $('rag-new').onclick=()=>{if(controller)return;conversation='';$('rag-conversation').value='';$('rag-delete').disabled=true;clearLog();note('Hội thoại mới');$('rag-question').focus();};
  $('rag-delete').onclick=async()=>{
    if (!conversation || controller || !confirm('Xóa hội thoại tài liệu này?')) return;
    try { await api('/api/rag/conversations/'+encodeURIComponent(conversation),{method:'DELETE'});conversation='';await refreshConversations();clearLog();busy(false);note('Đã xóa hội thoại'); }
    catch(error){note(error.message);}
  };
  $('rag-conversation').onchange=async()=>{
    if(controller)return;conversation=$('rag-conversation').value;clearLog();busy(false);
    if(!conversation){note('Hội thoại mới');return;}
    const loadOwner=owner,loadConversation=conversation;
    note('Đang khôi phục hội thoại…');
    try {
      const data=await api('/api/rag/conversations/'+encodeURIComponent(conversation)+'/messages');
      if(owner!==loadOwner || conversation!==loadConversation)return;
      const rows=Array.isArray(data)?data:(data.messages || data.items || []);
      for(const row of rows){const rendered=bubble(row.role,row.content || row.reply || '');citations(rendered.box,row.citations);if(row.status && row.status!=='completed')rendered.box.append(node('p','Lượt này chưa hoàn tất.','rag-message-progress'));}
      note('Đã khôi phục hội thoại');
    }catch(error){note(error.message);}
  };
  $('rag-stop').onclick=()=>controller?.abort();
  $('rag-form').onsubmit=async event=>{
    event.preventDefault();const question=$('rag-question').value.trim();
    if (!question || controller || window.tutorCodeBusy) return;
    const requestOwner=owner;
    controller=new AbortController();const active=controller;busy(true);note('Đang chuẩn bị…');
    let completed=false,answer='',rendered;
    const timer=setTimeout(()=>active.abort(),210000);
    try {
      if(!conversation){const data=await api('/api/rag/conversations',{...json({title:question.slice(0,100)}),signal:active.signal});if(owner!==requestOwner)throw new DOMException('Aborted','AbortError');conversation=data.id || data.conversation_id;if(!conversation)throw new Error('Không tạo được hội thoại.');await refreshConversations();}
      if(active.signal.aborted)throw new DOMException('Aborted','AbortError');
      bubble('user',question);rendered=bubble('assistant','');
      const progress=node('p','Đang truy xuất và kiểm tra dữ liệu trước khi trả lời…','rag-message-progress');rendered.box.append(progress);
      $('rag-question').value='';
      const response=await fetch('/api/rag/chat',{...json({question,conversation_id:conversation}),credentials:'same-origin',signal:active.signal,headers:{'Content-Type':'application/json','Accept':'application/x-ndjson'}});
      if(!response.ok){let error={};try{error=await response.json();}catch(_){}throw new Error(error.error || 'Không thực hiện được câu hỏi tài liệu.');}
      if(!response.body)throw new Error('Trình duyệt không nhận được luồng phản hồi.');
      const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
      const consume=line=>{
        if(owner!==requestOwner)throw new DOMException('Aborted','AbortError');
        if(!line.trim())return;const item=JSON.parse(line);
        if(item.error)throw new Error(typeof item.error==='string'?item.error:'Không hoàn tất được phản hồi.');
        if(item.status){const text=typeof item.status==='string'?item.status:item.message;progress.textContent=text || 'Đang kiểm tra…';note(progress.textContent);}
        if(typeof item.delta==='string'){answer+=item.delta;rendered.content.textContent=answer;$('rag-log').scrollTop=$('rag-log').scrollHeight;}
        if(item.done){const result=item.result || item;answer=result.reply || answer;rendered.content.textContent=answer;citations(rendered.box,result.citations || item.citations);completed=true;progress.remove();}
      };
      try{while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});let end;while((end=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,end));buffer=buffer.slice(end+1);}if(done)break;}consume(buffer);}
      finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
      if(!completed)throw new Error('Phản hồi bị ngắt trước khi hoàn tất.');
      note('Hoàn thành · câu trả lời theo tài liệu đã nạp');
      await refreshConversations();
    }catch(error){
      if(owner!==requestOwner)return;
      const text=active.signal.aborted?'Đã dừng câu hỏi.':error.message;
      if(rendered)rendered.box.append(node('p',text,'rag-message-progress'));
      note(text);if(!completed && !$('rag-question').value)$('rag-question').value=question;
    }finally{clearTimeout(timer);if(owner===requestOwner){controller=null;busy(false);}}
  };
  window.addEventListener('tutor-session',event=>sessionChanged(event.detail));
  window.addEventListener('tutor-code-busy',()=>busy(Boolean(controller)));
  window.addEventListener('pagehide',()=>controller?.abort());
  if(window.tutorStudent)sessionChanged(window.tutorStudent);
})();
