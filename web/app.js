const chat=document.getElementById('chat'),message=document.getElementById('message'),send=document.getElementById('send'),newChat=document.getElementById('newChat'),typing=document.getElementById('typing'),brainStage=document.getElementById('brainStage'),brainState=document.getElementById('brainState'),voice=document.getElementById('voice');
const GATEWAY='https://super-cerebro.hatchable.site/api/chat';
let recognition=null,history=[],selectedImage=null,tesseractPromise=null,sending=false;
function cognitiveSystem(text){return window.SuperCerebroCognitive?.buildSystem(text)||'Você é o Super Cérebro. Responda em português do Brasil com precisão, raciocínio cuidadoso e sem inventar informações.'}
function setBrainState(s){brainStage.classList.remove('thinking','listening','speaking');if(s)brainStage.classList.add(s);brainState.textContent=({listening:'Ouvindo...',thinking:'Pensando...',speaking:'Falando...'}[s]||'Pronto para pensar')}
function enterChatMode(){document.body.classList.add('chat-mode');chat.classList.add('has-messages')}
function addMessage(role,text){enterChatMode();const row=document.createElement('div');row.className=`message-row ${role}`;const box=document.createElement('div');box.className='bubble';const label=document.createElement('div');label.className='message-label';label.textContent=role==='user'?'Você':'Super Cérebro';const content=document.createElement('div');content.textContent=text;box.append(label,content);row.appendChild(box);chat.appendChild(row);requestAnimationFrame(()=>row.scrollIntoView({behavior:'smooth',block:'end'}))}
function setTyping(on){typing.innerHTML=on?'<span class="typing"><i></i><i></i><i></i></span>':''}
function cleanSpeechText(text){return String(text||'').replace(/\\([^)]*\\)/g,' ').replace(/\[[^\]]*\]/g,' ').replace(/\*+/g,' ').replace(/_+/g,' ').replace(/#{1,6}\s*/g,' ').replace(/^[>\-+]\s+/gm,' ').replace(/`+/g,' ').replace(/https?:\/\/\S+/g,' ').replace(/\s{2,}/g,' ').trim()}
let localTTS=null,localTTSLoading=null,ttsAudioContext=null,ttsSource=null,ttsElement=null;
const TTS_MODEL='onnx-community/Supertonic-TTS-2-ONNX';
const TTS_VOICE='https://huggingface.co/onnx-community/Supertonic-TTS-2-ONNX/resolve/main/voices/M1.bin';
async function loadLocalMaleTTS(){
  if(localTTS)return localTTS;
  if(localTTSLoading)return localTTSLoading;
  localTTSLoading=(async()=>{
    const mod=await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.0');
    const options={dtype:'q8'};
    if('gpu' in navigator)options.device='webgpu';
    try{localTTS=await mod.pipeline('text-to-speech',TTS_MODEL,options)}
    catch(firstError){
      delete options.device;
      localTTS=await mod.pipeline('text-to-speech',TTS_MODEL,options)
    }
    return localTTS
  })();
  try{return await localTTSLoading}
  finally{localTTSLoading=null}
}
function prepareAudioElement(){if(!ttsElement){ttsElement=new Audio();ttsElement.preload='auto';ttsElement.playsInline=true;ttsElement.volume=1;document.body.appendChild(ttsElement)}return ttsElement}
function prepareAudioContext(){
  if(!ttsAudioContext)ttsAudioContext=new (window.AudioContext||window.webkitAudioContext)();
  if(ttsAudioContext.state==='suspended')ttsAudioContext.resume().catch(()=>{});
  return ttsAudioContext
}
function primeAudio(){try{const ctx=prepareAudioContext();ctx.resume().catch(()=>{});const a=prepareAudioElement();a.volume=1;}catch(e){console.warn('AudioContext:',e)}}
function audioBlobFromOutput(output){
  if(output?.toBlob)return output.toBlob();
  const data=output?.audio;
  const rate=output?.sampling_rate||44100;
  if(!data)throw new Error('O mecanismo de voz não retornou áudio.');
  const samples=data instanceof Float32Array?data:new Float32Array(data);
  const buffer=new ArrayBuffer(44+samples.length*2),view=new DataView(buffer);
  const ws=(o,str)=>{for(let i=0;i<str.length;i++)view.setUint8(o+i,str.charCodeAt(i))};
  ws(0,'RIFF');view.setUint32(4,36+samples.length*2,true);ws(8,'WAVE');ws(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);ws(36,'data');view.setUint32(40,samples.length*2,true);
  let p=44;for(let i=0;i<samples.length;i++,p+=2){const x=Math.max(-1,Math.min(1,samples[i]));view.setInt16(p,x<0?x*32768:x*32767,true)}
  return new Blob([buffer],{type:'audio/wav'})
}
async function speakAnswer(text){
  const clean=cleanSpeechText(text);
  if(!clean)return;
  setBrainState('speaking');
  try{
    const tts=await loadLocalMaleTTS();
    const output=await tts('<pt>'+clean+'</pt>',{speaker_embeddings:TTS_VOICE,num_inference_steps:5,speed:1.02});
    const blob=audioBlobFromOutput(output);
    const url=URL.createObjectURL(blob);
    const audio=prepareAudioElement();
    audio.pause();
    audio.src=url;
    audio.currentTime=0;
    audio.onended=()=>{URL.revokeObjectURL(url);setBrainState('')};
    try{
      await audio.play();
      return;
    }catch(mediaError){
      console.warn('HTMLAudio bloqueado, tentando WebAudio:',mediaError);
    }
    const ctx=prepareAudioContext();
    await ctx.resume();
    const buffer=await ctx.decodeAudioData(await blob.arrayBuffer());
    if(ttsSource){try{ttsSource.stop()}catch{}}
    ttsSource=ctx.createBufferSource();
    ttsSource.buffer=buffer;
    ttsSource.connect(ctx.destination);
    ttsSource.onended=()=>{if(ttsSource?.buffer===buffer)setBrainState('')};
    ttsSource.start(0);
  }catch(e){
    console.error('TTS local masculino falhou:',e);
    try{await speakBrowserFallback(clean);return}catch(fallbackError){console.error('Fallback de voz falhou:',fallbackError);setBrainState('')}
  }
}
function speakBrowserFallback(text){
  return new Promise((resolve,reject)=>{
    const clean=cleanSpeechText(text); if(!clean||!('speechSynthesis' in window)){reject(new Error('Voz do navegador indisponível'));return}
    const u=new SpeechSynthesisUtterance(clean);u.lang='pt-BR';u.rate=.98;u.pitch=.82;u.volume=1;
    const voices=speechSynthesis.getVoices();
    const preferred=voices.find(v=>/pt-BR|Portuguese|Brasil/i.test(v.lang)&&/male|mascul|homem|Daniel|Felipe|Luciano|Ricardo/i.test(v.name))
      ||voices.find(v=>/pt-BR/i.test(v.lang))||voices.find(v=>/pt/i.test(v.lang));
    if(preferred)u.voice=preferred;
    u.onstart=()=>setBrainState('speaking');u.onend=()=>{setBrainState('');resolve()};u.onerror=e=>{setBrainState('');reject(e)};
    speechSynthesis.cancel();speechSynthesis.speak(u);
  });
}
function getVoiceDebug(){return{engine:'Supertonic 2 local + fallback',voice:'M1 masculino / pt-BR',model:TTS_MODEL,loaded:!!localTTS}}
async function callVireonix(value,extraContext=''){const userText=extraContext?`${value}\n\n${extraContext}`:value;const messages=[{role:'system',content:cognitiveSystem(userText)},...history,{role:'user',content:userText}];let lastError='Falha de conexão com o Vireonix.';for(let attempt=0;attempt<3;attempt++){try{const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),60000);let r;try{r=await fetch(GATEWAY,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'auto',messages}),signal:controller.signal,cache:'no-store'})}finally{clearTimeout(timer)}const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch{}if(!r.ok){lastError=`Gateway HTTP ${r.status}: ${d?.error?.message||d?.error?.type||raw||'erro'}`;if((r.status===429||r.status>=500)&&attempt<2){await new Promise(x=>setTimeout(x,1200*(attempt+1)));continue}throw new Error(lastError)}const answer=d?.choices?.[0]?.message?.content||d?.content||d?.result;if(typeof answer!=='string'||!answer.trim())throw new Error('O Vireonix respondeu sem conteúdo.');return answer.trim()}catch(e){lastError=e?.name==='AbortError'?'A conexão demorou mais de 60 segundos para responder.':e?.message||lastError;if(attempt<2)await new Promise(x=>setTimeout(x,1200*(attempt+1)))}}throw new Error(lastError)}
function loadTesseract(){if(window.Tesseract)return Promise.resolve(window.Tesseract);if(tesseractPromise)return tesseractPromise;tesseractPromise=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js';s.async=true;s.onload=()=>window.Tesseract?resolve(window.Tesseract):reject(new Error('O leitor OCR não carregou.'));s.onerror=()=>reject(new Error('Não foi possível carregar o leitor OCR. Verifique a conexão e tente novamente.'));document.head.appendChild(s)});return tesseractPromise}
async function prepareImage(file){const bitmap=await createImageBitmap(file);const max=2400,scale=Math.min(1,max/Math.max(bitmap.width,bitmap.height));const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();const img=ctx.getImageData(0,0,canvas.width,canvas.height),d=img.data;for(let i=0;i<d.length;i+=4){const y=.299*d[i]+.587*d[i+1]+.114*d[i+2];const v=y<150?Math.max(0,y-12):Math.min(255,y+10);d[i]=d[i+1]=d[i+2]=v}ctx.putImageData(img,0,0);return canvas}
async function readImageText(file){const T=await loadTesseract();setBrainState('thinking');brainState.textContent='Preparando leitura do print...';let source=file;try{source=await prepareImage(file)}catch{}const result=await T.recognize(source,'por+eng',{logger:m=>{if(m.status==='loading language data')brainState.textContent='Carregando idioma do leitor...';else if(m.status==='recognizing text'&&typeof m.progress==='number')brainState.textContent=`Lendo imagem... ${Math.round(m.progress*100)}%`}});return(result?.data?.text||'').replace(/[ \t]+\n/g,'\n').replace(/\n{3,}/g,'\n\n').trim()}
async function ask(text){const value=text.trim(),hasImage=!!selectedImage;if((!value&&!hasImage)||sending)return;document.getElementById('welcome')?.remove();const imageForRead=selectedImage,imageName=imageForRead?.name||'print';addMessage('user',hasImage?`🖼️ ${imageName}${value?'\n'+value:''}`:value);message.value='';message.style.height='48px';sending=true;setTyping(true);setBrainState('thinking');try{let context='';if(imageForRead){let ocr='';let ocrError='';try{ocr=await readImageText(imageForRead)}catch(e){ocrError=e?.message||'falha desconhecida'}context=`ATENÇÃO: O usuário enviou um print/imagem. Você NÃO deve responder que não consegue visualizar imagens. A imagem foi processada localmente por OCR e o texto extraído está abaixo. Responda usando esse texto como a fonte do conteúdo visível. Explique em português do Brasil, com detalhes e sem inventar. Identifique títulos, mensagens, avisos, números, datas, nomes, botões, campos, erros e instruções. Preserve valores e palavras importantes. Se algum trecho estiver incompleto ou estranho, marque como [trecho possivelmente incorreto] e explique o que ainda dá para concluir. Se o usuário não fez uma pergunta específica, primeiro diga claramente o que o print mostra e depois explique cada parte.\n\nNOME DO ARQUIVO: ${imageName}\n\nTEXTO EXTRAÍDO DO PRINT:\n${ocr||'[OCR não conseguiu extrair texto desta imagem. Não diga que você não pode visualizar imagens; informe apenas que a leitura automática falhou e peça um print mais nítido ou com maior resolução.]'}${ocrError?'\n\nDETALHE TÉCNICO DO OCR (não precisa mostrar ao usuário): '+ocrError:''}`}const answer=await callVireonix(value||'Leia e explique este print detalhadamente.',context);history.push({role:'user',content:context?`${value||'Leia e explique este print detalhadamente.'}\n${context}`:value},{role:'assistant',content:answer});if(history.length>30)history=history.slice(-30);addMessage('assistant',answer);speakAnswer(answer).catch(()=>{}); }catch(e){addMessage('assistant',`Não consegui processar a imagem ou conectar ao Vireonix.\n\n${e.message}`);setBrainState('')}finally{selectedImage=null;const f=document.getElementById('fileInput');if(f)f.value='';document.getElementById('attachmentPreview')?.classList.remove('show');const info=document.getElementById('attachmentInfo');if(info)info.textContent='';setTyping(false);sending=false;send.disabled=false;send.style.visibility='visible';send.style.opacity='1';message.focus()}}
function startVoice(){const R=window.SpeechRecognition||window.webkitSpeechRecognition;if(!R){addMessage('assistant','Seu navegador não oferece reconhecimento de voz.');return}recognition?.abort();recognition=new R();recognition.lang='pt-BR';recognition.interimResults=true;recognition.continuous=false;voice.classList.add('active');setBrainState('listening');recognition.onresult=e=>{let t='';for(let i=e.resultIndex;i<e.results.length;i++)t+=e.results[i][0].transcript;message.value=t;message.dispatchEvent(new Event('input'))};recognition.onend=()=>{voice.classList.remove('active');if(message.value.trim())ask(message.value);else setBrainState('')};recognition.onerror=()=>{voice.classList.remove('active');setBrainState('')};recognition.start()}
const fileInput=document.getElementById('fileInput');document.addEventListener('change',e=>{if(e.target!==fileInput)return;const f=e.target.files?.[0];if(!f)return;if(!f.type.startsWith('image/')){alert('Escolha uma imagem ou print.');e.target.value='';return}selectedImage=f;const info=document.getElementById('attachmentInfo'),preview=document.getElementById('attachmentPreview');if(info)info.textContent=`🖼️ ${f.name} • ${Math.round(f.size/1024)} KB • pronto para leitura`;preview?.classList.add('show')},true);document.getElementById('removeAttachment')?.addEventListener('click',()=>{selectedImage=null;if(fileInput)fileInput.value='';document.getElementById('attachmentPreview')?.classList.remove('show')});send.onclick=()=>{primeAudio();ask(message.value)};voice.onclick=()=>{primeAudio();startVoice()};message.oninput=()=>{message.style.height='48px';message.style.height=`${Math.min(message.scrollHeight,180)}px`};message.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask(message.value)}};document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>ask(b.dataset.prompt||''));newChat.onclick=()=>{speechSynthesis?.cancel();history=[];location.reload()};