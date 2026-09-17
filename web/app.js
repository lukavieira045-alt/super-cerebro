const chat=document.getElementById('chat'),message=document.getElementById('message'),send=document.getElementById('send'),newChat=document.getElementById('newChat'),typing=document.getElementById('typing'),brainStage=document.getElementById('brainStage'),brainState=document.getElementById('brainState'),voice=document.getElementById('voice');
const GATEWAY='https://super-cerebro.hatchable.site/api/chat';
let recognition=null,history=[],speakTimer=null;

const visualFix=document.createElement('style');visualFix.textContent=`
.chat-mode .brain-stage{position:fixed!important;inset:66px 0 0!important;width:100vw!important;height:calc(100dvh - 66px)!important;min-height:0!important;z-index:2!important;pointer-events:none!important;background:radial-gradient(circle at 50% 45%,rgba(2,3,8,.08),rgba(2,3,8,.38) 55%,rgba(2,3,8,.7) 100%)!important}
.chat-mode .cyber-brain{width:min(96vw,1100px)!important;height:min(82vh,820px)!important;min-height:520px!important;opacity:.62!important;transform:scale(1.05)!important;animation:brainIdle 4s ease-in-out infinite!important;transform-origin:center!important}
.chat-mode .message-row{position:relative;z-index:25!important}
.chat-mode .message-row .bubble{backdrop-filter:blur(18px)!important;background:rgba(9,13,24,.88)!important}
.chat-mode .message-row.user .bubble{background:rgba(23,36,60,.92)!important}
.chat-mode .chat{background:transparent!important}
@keyframes brainIdle{0%,100%{transform:scale(1.05) translateY(0) rotate(0deg)}50%{transform:scale(1.075) translateY(-7px) rotate(.35deg)}}
.brain-stage.thinking .cyber-brain{animation:brainThink .7s ease-in-out infinite!important;filter:brightness(1.15) saturate(1.12) drop-shadow(0 0 28px rgba(255,80,190,.42))!important}
.brain-stage.listening .cyber-brain{animation:brainListen 1.1s ease-in-out infinite!important;filter:brightness(1.12) saturate(1.15) drop-shadow(0 0 32px rgba(80,170,255,.45))!important}
.brain-stage.speaking .cyber-brain{animation:brainSpeak .22s ease-in-out infinite!important;filter:brightness(1.2) saturate(1.2) drop-shadow(0 0 42px rgba(255,70,190,.62))!important}
@keyframes brainThink{0%,100%{transform:scale(1.05) rotate(-.5deg)}50%{transform:scale(1.095) rotate(.5deg)}}
@keyframes brainListen{0%,100%{transform:scale(1.05)}50%{transform:scale(1.09)}}
@keyframes brainSpeak{0%{transform:scale(1.055) translateY(0)}50%{transform:scale(1.115) translateY(-5px)}100%{transform:scale(1.055) translateY(0)}}
@media(max-width:700px){.chat-mode .cyber-brain{width:120vw!important;height:72vh!important;min-height:470px!important;opacity:.48!important}.chat-mode .message-row{max-width:96vw!important}.chat-mode .bubble{max-width:92%!important}}
`;document.head.appendChild(visualFix);

function setBrainState(s){brainStage.classList.remove('thinking','listening','speaking');if(s)brainStage.classList.add(s);brainState.textContent=({listening:'Ouvindo...',thinking:'Pensando...',speaking:'Falando...'}[s]||'Pronto para pensar')}
function enterChatMode(){document.body.classList.add('chat-mode');chat.classList.add('has-messages')}
function addMessage(role,text){enterChatMode();const row=document.createElement('div');row.className=`message-row ${role}`;const box=document.createElement('div');box.className='bubble';const label=document.createElement('div');label.className='message-label';label.textContent=role==='user'?'Você':'Super Cérebro';const content=document.createElement('div');content.textContent=text;box.append(label,content);row.appendChild(box);chat.appendChild(row);requestAnimationFrame(()=>row.scrollIntoView({behavior:'smooth',block:'end'}))}
function setTyping(on){typing.innerHTML=on?'<span class="typing"><i></i><i></i><i></i></span>':''}
function speakAnswer(text){if(!('speechSynthesis'in window)){setBrainState('');return}window.speechSynthesis.cancel();clearTimeout(speakTimer);const u=new SpeechSynthesisUtterance(text);u.lang='pt-BR';u.rate=.98;u.pitch=.95;u.onstart=()=>setBrainState('speaking');u.onboundary=()=>{brainStage.classList.remove('speaking');void brainStage.offsetWidth;brainStage.classList.add('speaking');clearTimeout(speakTimer);speakTimer=setTimeout(()=>setBrainState('speaking'),180)};u.onend=()=>setBrainState('');u.onerror=()=>setBrainState('');window.speechSynthesis.speak(u)}

async function callVireonix(value){
  const messages=[{role:'system',content:'Você é o Super Cérebro. Responda em português do Brasil. Raciocine com cuidado, não invente fatos, seja útil e direto. Vireonix é o único cérebro do sistema.'},...history,{role:'user',content:value}];
  let lastError='Falha de conexão com o Vireonix.';
  for(let attempt=0;attempt<3;attempt++){
    try{
      const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),45000);let r;
      try{r=await fetch(GATEWAY,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'auto',messages}),signal:controller.signal,cache:'no-store'})}finally{clearTimeout(timer)}
      const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch{}
      if(!r.ok){const detail=d?.error?.message||d?.error?.type||raw||`HTTP ${r.status}`;lastError=`Gateway HTTP ${r.status}: ${detail}`;if((r.status===429||r.status>=500)&&attempt<2){await new Promise(x=>setTimeout(x,1000*(attempt+1)));continue}throw new Error(lastError)}
      const answer=d?.choices?.[0]?.message?.content||d?.content||d?.result;
      if(typeof answer!=='string'||!answer.trim())throw new Error('O Vireonix respondeu sem conteúdo.');
      return answer.trim();
    }catch(e){if(e?.name==='AbortError')lastError='A conexão demorou mais de 45 segundos para responder.';else if(e instanceof TypeError)lastError='Não consegui acessar a ponte do Vireonix.';else lastError=e?.message||lastError;if(attempt<2)await new Promise(x=>setTimeout(x,1000*(attempt+1)))}
  }
  throw new Error(lastError)
}

async function ask(text){const value=text.trim();if(!value||send.disabled)return;document.getElementById('welcome')?.remove();addMessage('user',value);message.value='';message.style.height='48px';send.disabled=true;setTyping(true);setBrainState('thinking');try{const answer=await callVireonix(value);history.push({role:'user',content:value},{role:'assistant',content:answer});if(history.length>20)history=history.slice(-20);addMessage('assistant',answer);speakAnswer(answer)}catch(e){addMessage('assistant',`Não consegui conectar ao Vireonix.\n\n${e.message}`);setBrainState('')}finally{setTyping(false);send.disabled=false;message.focus()}}

function startVoice(){const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R){addMessage('assistant','Seu navegador não oferece reconhecimento de voz.');return}recognition?.abort();recognition=new R();recognition.lang='pt-BR';recognition.interimResults=true;recognition.continuous=false;voice.classList.add('active');setBrainState('listening');recognition.onresult=e=>{let t='';for(let i=e.resultIndex;i<e.results.length;i++)t+=e.results[i][0].transcript;message.value=t;message.dispatchEvent(new Event('input'))};recognition.onend=()=>{voice.classList.remove('active');if(message.value.trim())ask(message.value);else setBrainState('')};recognition.onerror=()=>{voice.classList.remove('active');setBrainState('')};recognition.start()}

send.onclick=()=>ask(message.value);voice.onclick=startVoice;message.oninput=()=>{message.style.height='48px';message.style.height=`${Math.min(message.scrollHeight,180)}px`};message.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask(message.value)}};document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>ask(b.dataset.prompt||''));newChat.onclick=()=>{speechSynthesis?.cancel();history=[];location.reload()};
