const API = '';
const $ = (id) => document.getElementById(id);
let documents = [];
let selectedDocumentIds = [];
let hasStartedChat = false;
let chatHistory = [];

function toast(message) {
  const el = $('toast'); el.textContent = message; el.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove('show'), 3400);
}
async function api(path, options={}) {
  const response = await fetch(`${API}/api${path}`, options);
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(data.detail || 'Something went wrong.');
  return data;
}
async function refreshDocuments() {
  try {
    const data = await api('/documents'); documents = data.documents || [];
    renderDocuments();
    $('docCount').textContent = documents.length;
    $('connectionText').textContent = 'Local server connected';
    document.querySelector('.status-dot').classList.add('online');
    if (documents.length && !hasStartedChat) showChat();
  } catch (err) {
    $('connectionText').textContent = 'Server not connected';
    toast('Cannot connect to the backend. Start the server and refresh.');
  }
}
function renderDocuments() {
  const list = $('documentList');
  if (!documents.length) { list.innerHTML = '<div class="empty-library">No documents yet.<br>Upload a PDF to get started.</div>'; return; }
  list.innerHTML = '';
  documents.forEach(doc => {
    const item = document.createElement('div'); item.className = 'doc-item' + (selectedDocumentIds.includes(doc.id) ? ' selected' : '');
    const icon = document.createElement('div'); icon.className='pdf-icon'; icon.textContent='PDF';
    const meta = document.createElement('div'); meta.className='doc-meta';
    const name = document.createElement('strong'); name.textContent=doc.name;
    const details = document.createElement('small'); details.textContent=`${doc.pages} pages · ${doc.chunks} chunks`;
    meta.append(name, details);
    const del = document.createElement('button'); del.className='delete-doc'; del.title='Remove document'; del.textContent='×';
    del.addEventListener('click', async e => { e.stopPropagation(); if (!confirm(`Remove ${doc.name}?`)) return; try { await api(`/documents/${doc.id}`,{method:'DELETE'}); documents=documents.filter(d=>d.id!==doc.id); selectedDocumentIds=selectedDocumentIds.filter(id=>id!==doc.id); renderDocuments(); $('docCount').textContent=documents.length; toast('Document removed.'); if(!documents.length){$('chatPanel').classList.add('hidden');$('welcomePanel').classList.remove('hidden');hasStartedChat=false;} } catch(err){toast(err.message);} });
    item.append(icon,meta,del);
    item.addEventListener('click',()=>{ if(selectedDocumentIds.includes(doc.id)) selectedDocumentIds=selectedDocumentIds.filter(id=>id!==doc.id); else selectedDocumentIds.push(doc.id); renderDocuments(); updateContext(); });
    list.append(item);
  });
}
function updateContext(){ $('contextLabel').textContent = selectedDocumentIds.length ? `${selectedDocumentIds.length} selected` : 'All documents'; }
function showChat(){ $('welcomePanel').classList.add('hidden'); $('chatPanel').classList.remove('hidden'); hasStartedChat=true; updateContext(); }
function showWelcome(){ $('chatPanel').classList.add('hidden'); $('welcomePanel').classList.remove('hidden'); hasStartedChat=false; }
async function uploadFiles(files) {
  const pdfs = Array.from(files).filter(f => f.type==='application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
  if (!pdfs.length) { toast('Please choose a PDF file.'); return; }
  for (const file of pdfs) {
    const form = new FormData(); form.append('file',file);
    toast(`Uploading and indexing ${file.name}…`);
    try {
      const result = await api('/upload',{method:'POST',body:form});
      documents.push(result.document); selectedDocumentIds=[result.document.id];
      renderDocuments(); $('docCount').textContent=documents.length; showChat();
      addMessage('assistant',`I've processed **${result.document.name}** successfully. It contains ${result.document.pages} pages and ${result.document.chunks} searchable text sections. What would you like to know?`,[]);
      toast(`${file.name} is ready to chat with.`);
    } catch(err) { toast(`${file.name}: ${err.message}`); }
  }
  $('fileInput').value='';
}
function addMessage(role,text,sources=[],persist=true) {
  showChat(); const wrap=document.createElement('div'); wrap.className=role==='user'?'user-message':'assistant-message';
  const avatar=document.createElement('div'); avatar.className='avatar'; avatar.textContent=role==='user'?'Y':'S';
  const body=document.createElement('div'); body.className='message-body';
  const author=document.createElement('div'); author.className='message-author'; author.textContent=role==='user'?'You':'SmartDoc AI';
  const bubble=document.createElement('div'); bubble.className='bubble'; bubble.textContent=text;
  body.append(author,bubble);
  if(role==='assistant' && sources.length){ const sourceWrap=document.createElement('div'); sourceWrap.className='sources'; sources.forEach(s=>{const chip=document.createElement('span');chip.className='source-chip';chip.textContent=`▤ ${s.document} · Page ${s.page}`;sourceWrap.append(chip);});body.append(sourceWrap); }
  if(role==='user'){wrap.append(body,avatar);}else{wrap.append(avatar,body);}
  $('messages').append(wrap); $('messages').scrollTop=$('messages').scrollHeight;
  if (persist) { chatHistory.push({role,text,sources}); try { localStorage.setItem('smartdoc_chat_history', JSON.stringify(chatHistory)); } catch (_) {} }
  return wrap;
}
async function sendQuestion(question) {
  const q=question.trim(); if(!q)return;
  if(!documents.length){toast('Upload a PDF before asking a question.');return;}
  addMessage('user',q); $('questionInput').value=''; $('sendBtn').disabled=true;
  const pending=addMessage('assistant','Searching your documents and preparing an answer…');
  try {
    const result=await api('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,document_ids:selectedDocumentIds})});
    pending.remove(); addMessage('assistant',result.answer,result.sources||[]);
  } catch(err) { pending.remove(); addMessage('assistant',`I couldn't complete that request. ${err.message}`); }
  finally { $('sendBtn').disabled=false; $('questionInput').focus(); }
}
$('browseBtn').addEventListener('click',()=>$('fileInput').click());
$('fileInput').addEventListener('change',e=>uploadFiles(e.target.files));
$('dropZone').addEventListener('dragover',e=>{e.preventDefault();$('dropZone').classList.add('dragover');});
$('dropZone').addEventListener('dragleave',()=>$('dropZone').classList.remove('dragover'));
$('dropZone').addEventListener('drop',e=>{e.preventDefault();$('dropZone').classList.remove('dragover');uploadFiles(e.dataTransfer.files);});
$('sendBtn').addEventListener('click',()=>sendQuestion($('questionInput').value));
$('questionInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendQuestion(e.target.value);}});
$('newChatBtn').addEventListener('click',()=>{ $('messages').innerHTML=''; chatHistory=[]; try{localStorage.removeItem('smartdoc_chat_history');}catch(_){} selectedDocumentIds=[];renderDocuments();updateContext(); if(documents.length)showChat();else showWelcome(); if(documents.length)addMessage('assistant','New conversation started. Ask me anything about your uploaded documents.'); });
$('clearChatBtn').addEventListener('click',()=>{ $('messages').innerHTML=''; chatHistory=[]; try{localStorage.removeItem('smartdoc_chat_history');}catch(_){} if(documents.length)addMessage('assistant','Conversation cleared. What would you like to explore in your documents?'); else showWelcome(); });
document.querySelectorAll('.suggestion').forEach(btn=>btn.addEventListener('click',()=>sendQuestion(btn.dataset.question)));
try { chatHistory = JSON.parse(localStorage.getItem('smartdoc_chat_history') || '[]'); if (chatHistory.length) { showChat(); chatHistory.forEach(m => addMessage(m.role, m.text, m.sources || [], false)); } } catch (_) { chatHistory = []; }
refreshDocuments();
