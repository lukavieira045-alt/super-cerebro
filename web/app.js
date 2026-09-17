const chat=document.getElementById('chat'),message=document.getElementById('message'),send=document.getElementById('send'),newChat=document.getElementById('newChat'),typing=document.getElementById('typing'),brainStage=document.getElementById('brainStage'),brainState=document.getElementById('brainState'),voice=document.getElementById('voice');
const GATEWAY='https://super-cerebro.hatchable.site/api/chat';
let recognition=null,history=[],speakTimer=null,selectedImage=null;

function cognitiveSystem(text){return window.SuperCerebroCognitive?.buildSystem(text)||'Você é o Super Cérebro. Responda em português do Brasil com precisão, raciocínio cuidadoso e sem inventar informações.'}
function setBrainState(s){brainStage.classList.remove('thinking','listening','speaking');if(s)brainStage.classList.add(s);brainState.textContent=({listening:'Ouvindo...',thinking:'Pensando...',speaking:'Falando...'}[s]||'Pronto para pensar')}
function enterChatMode(){document.body.classList.add('chat-mode');chat.classList.add('has-messages')}
function addMessage(role,text){enterChatMode();const row=document.createElement('div');row.className=`message-row ${role}`;const box=document.createElement('div');box.className='bubble';const label=document.createElement('div');label.className='message-label';label.textContent=role==='user'?'Você':'Super Cérebro';const content=document.createElement('div');content.textContent=text;box.append(label,content);row.appendChild(box);chat.appendChild(row);requestAnimationFrame(()=>row.scrollIntoView({behavior:'smooth',block:'end'}))}
function setTyping(on){typing.innerHTML=on?'<span class="typing"><i></i><i></i><i></i></span>':''}
function speakAnswer(text){if(!('speechSynthesis'in window)){setBrainState('');return}window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang='pt-BR';u.rate=.98;u.pitch=.95;u.onstart=()=>setBrainState('speaking');u.onend=()=>setBrainState('');u.onerror=()=>setBrainState('');window.speechSynthesis.speak(u)}

async function callVireonix(value,extraContext=''){
  const userText=extraContext?`${value}\n\n${extraContext}`:value;
  const messages=[{role:'system',content:cognitiveSystem(userText)},...history,{role:'user',content:userText}];
  let lastError='Falha de conexão com o Vireonix.';
  for(let attempt=0;attempt<3;attempt++){
    try{
      const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),60000);let r;
      try{r=await fetch(GATEWAY,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'auto',messages}),signal:controller.signal,cache:'no-store'})}finally{clearTimeout(timer)}
      const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch{}
      if(!r.ok){lastError=`Gateway HTTP ${r.status}: ${d?.error?.message||d?.error?.type||raw||'erro'}`;if((r.status===429||r.status>=500)&&attempt<2){await new Promise(x=>setTimeout(x,1200*(attempt+1)));continue}throw new Error(lastError)}
      const answer=d?.choices?.[0]?.message?.content||d?.content||d?.result;if(typeof answer!=='string'||!answer.trim())throw new Error('O Vireonix respondeu sem conteúdo.');return answer.trim()
    }catch(e){lastError=e?.name==='AbortError'?'A conexão demorou mais de 60 segundos para responder.':e?.message||lastError;if(attempt<2)await new Promise(x=>setTimeout(x,1200*(attempt+1)))}
  }
  throw new Error(lastError)
}

async function readImageText(file){
  if(!window.Tesseract)throw new Error('Leitor de imagem ainda não carregou. Recarregue o aplicativo e tente novamente.');
  setBrainState('thinking');
  const result=await Tesseract.recognize(file,'por+eng',{logger:m=>{if(m.status==='recognizing text'&&typeof m.progress==='number'){brainState.textContent=`Lendo imagem... ${Math.round(m.progress*100)}%`}}});
  const text=(result?.data?.text||'').replace(/\n{3,}/g,'\n\n').trim();
  if(!text)return '';
  return text;
}

async function ask(text){
  const value=text.trim();
  const hasImage=!!selectedImage;
  if((!value&&!hasImage)||send.disabled)return;
  document.getElementById('welcome')?.remove();
  const imageForRead=selectedImage;
  const imageName=imageForRead?.name||'print';
  addMessage('user',hasImage?`🖼️ ${imageName}${value?'\n'+value:''}`:value);
  message.value='';message.style.height='48px';send.disabled=true;setTyping(true);setBrainState('thinking');
  try{
    let context='';
    if(imageForRead){
      let ocr='';
      try{ocr=await readImageText(imageForRead)}catch(e){ocr=''}
      context=`O usuário enviou uma imagem/print. Você deve tratar o conteúdo abaixo como texto extraído da imagem por OCR. Analise com atenção e explique em português do Brasil, com detalhes, o que aparece escrito, organizando títulos, avisos, números, datas, botões, erros e instruções quando existirem. Não invente palavras que o OCR não encontrou. Se houver trecho duvidoso, marque como [trecho possivelmente incorreto]. Se o usuário não fez uma pergunta específica, faça primeiro uma descrição clara do que o print mostra e depois explique o significado de cada parte.\n\nNOME DO ARQUIVO: ${imageName}\n\nTEXTO EXTRAÍDO DO PRINT:\n${ocr||'[Não foi possível extrair texto da imagem. Informe que a leitura automática falhou e peça um print mais nítido.]'}`;
    }
    const answer=await callVireonix(value||'Leia e explique este print detalhadamente.',context);
    history.push({role:'user',content:context?`${value||'Leia e explique este print detalhadamente.'}\n${context}`:value},{role:'assistant',content:answer});
    if(history.length>30)history=history.slice(-30);
    addMessage('assistant',answer);speakAnswer(answer)
  }catch(e){addMessage('assistant',`Não consegui processar a imagem ou conectar ao Vireonix.\n\n${e.message}`);setBrainState('')}
  finally{selectedImage=null;const f=document.getElementById('fileInput');if(f)f.value='';document.getElementById('attachmentPreview')?.classList.remove('show');document.getElementById('attachmentInfo').textContent='';setTyping(false);send.disabled=false;message.focus()}
}

function startVoice(){const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R){addMessage('assistant','Seu navegador não oferece reconhecimento de voz.');return}recognition?.abort();recognition=new R();recognition.lang='pt-BR';recognition.interimResults=true;recognition.continuous=false;voice.classList.add('active');setBrainState('listening');recognition.onresult=e=>{let t='';for(let i=e.resultIndex;i<e.results.length;i++)t+=e.results[i][0].transcript;message.value=t;message.dispatchEvent(new Event('input'))};recognition.onend=()=>{voice.classList.remove('active');if(message.value.trim())ask(message.value);else setBrainState('')};recognition.onerror=()=>{voice.classList.remove('active');setBrainState('')};recognition.start()}

const fileInput=document.getElementById('fileInput');
fileInput?.addEventListener('change',e=>{const f=e.target.files?.[0];if(!f)return;if(!f.type.startsWith('image/')){alert('Escolha uma imagem ou print.');e.target.value='';return}selectedImage=f;const info=document.getElementById('attachmentInfo');const preview=document.getElementById('attachmentPreview');if(info)info.textContent=`🖼️ ${f.name} • ${Math.round(f.size/1024)} KB • pronto para leitura`;preview?.classList.add('show');message.focus()});

document.getElementById('removeAttachment')?.addEventListener('click',()=>{selectedImage=null;if(fileInput)fileInput.value='';document.getElementById('attachmentPreview')?.classList.remove('show')});
send.onclick=()=>ask(message.value);voice.onclick=startVoice;message.oninput=()=>{message.style.height='48px';message.style.height=`${Math.min(message.scrollHeight,180)}px`};message.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask(message.value)}};document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>ask(b.dataset.prompt||''));newChat.onclick=()=>{speechSynthesis?.cancel();history=[];location.reload()};
