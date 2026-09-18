(() => {
  const VOICE_ID='pt_BR-faber-medium';
  let piper=null,piperLoading=null,currentAudio=null;
  const clean=t=>String(t||'').replace(/\\([^)]*\\)/g,' ').replace(/\[[^\]]*\]/g,' ').replace(/\*+/g,' ').replace(/_+/g,' ').replace(/#{1,6}\s*/g,' ').replace(/^[>\-+]\s+/gm,' ').replace(/`+/g,' ').replace(/https?:\/\/\S+/g,' ').replace(/\s{2,}/g,' ').trim();
  const state=s=>{try{if(typeof setBrainState==='function')setBrainState(s)}catch{}};
  const status=t=>{try{const e=document.getElementById('voiceStatus');if(e){e.textContent=t;e.classList.add('show');clearTimeout(status.t);status.t=setTimeout(()=>e.classList.remove('show'),8000)}}catch{}};
  async function engine(){
    if(piper)return piper;
    if(piperLoading)return piperLoading;
    piperLoading=(async()=>{
      const m=await import('https://cdn.jsdelivr.net/npm/@mintplex-labs/piper-tts-web@1.0.5/+esm');
      return m;
    })();
    try{piper=await piperLoading;return piper}catch(e){piperLoading=null;throw e}
  }
  async function speak(text){
    const t=clean(text);if(!t)return;
    state('speaking');
    try{
      const e=await engine();
      if(!e?.predict)throw new Error('Piper TTS Web não carregou.');
      const wav=await e.predict({text:t,voiceId:VOICE_ID});
      if(!(wav instanceof Blob))throw new Error('Piper não retornou áudio WAV.');
      if(currentAudio){try{currentAudio.pause();currentAudio.removeAttribute('src')}catch{}}
      const url=URL.createObjectURL(wav);
      const audio=new Audio(url);currentAudio=audio;audio.volume=1;audio.preload='auto';
      audio.onended=()=>{URL.revokeObjectURL(url);if(currentAudio===audio)currentAudio=null;state('')};
      await audio.play();
      status('Voz masculina: Piper • pt_BR-faber-medium');
    }catch(e){state('');console.error('Piper masculino:',e);status('Falha na voz masculina: '+(e?.message||'erro desconhecido'));throw e}
  }
  window.speakAnswer=speak;
  window.testMaleVoice=async()=>{try{await speak('Olá. Eu sou o Super Cérebro. Esta é a minha voz masculina.');status('Teste concluído: Piper pt_BR-faber-medium')}catch{}};
  window.getVoiceDebug=async()=>({engine:'Piper TTS Web',voice:VOICE_ID,ready:!!piper});
})();
