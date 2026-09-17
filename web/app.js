const chat = document.getElementById('chat');
const message = document.getElementById('message');
const send = document.getElementById('send');
const newChat = document.getElementById('newChat');
const typing = document.getElementById('typing');
const brainStage = document.getElementById('brainStage');
const brainState = document.getElementById('brainState');
const voice = document.getElementById('voice');

let recognition = null;
let speakingTimer = null;

function setBrainState(state) {
  brainStage.classList.remove('thinking', 'listening', 'speaking');
  if (state) brainStage.classList.add(state);
  const labels = { listening: 'Ouvindo...', thinking: 'Pensando...', speaking: 'Falando...' };
  brainState.textContent = labels[state] || 'Pronto para pensar';
}

function addMessage(role, text) {
  const row = document.createElement('div');
  row.className = `message-row ${role}`;
  const box = document.createElement('div');
  box.className = 'bubble';
  const label = document.createElement('div');
  label.className = 'message-label';
  label.textContent = role === 'user' ? 'Você' : 'Super Cérebro';
  const content = document.createElement('div');
  content.textContent = text;
  box.append(label, content);
  row.appendChild(box);
  chat.appendChild(row);
  row.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function setTyping(active) {
  typing.innerHTML = active ? '<span class="typing"><i></i><i></i><i></i></span>' : '';
}

function speakAnswer(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'pt-BR';
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.onstart = () => setBrainState('speaking');
  utterance.onend = () => setBrainState('');
  utterance.onerror = () => setBrainState('');
  window.speechSynthesis.speak(utterance);
}

async function ask(text) {
  const value = text.trim();
  if (!value || send.disabled) return;
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.remove();
  addMessage('user', value);
  message.value = '';
  message.style.height = '42px';
  send.disabled = true;
  setTyping(true);
  setBrainState('thinking');

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: value })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    const answer = data.answer || 'Não recebi uma resposta válida.';
    addMessage('assistant', answer);
    speakAnswer(answer);
  } catch (error) {
    setBrainState('');
    addMessage('assistant', `Não consegui conectar ao núcleo agora. ${error.message}`);
  } finally {
    setTyping(false);
    send.disabled = false;
    message.focus();
  }
}

function startVoice() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    addMessage('assistant', 'Seu navegador não oferece reconhecimento de voz nesta versão.');
    return;
  }
  if (recognition) recognition.abort();
  recognition = new Recognition();
  recognition.lang = 'pt-BR';
  recognition.interimResults = true;
  recognition.continuous = false;
  voice.classList.add('active');
  setBrainState('listening');
  recognition.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      transcript += event.results[i][0].transcript;
    }
    message.value = transcript;
    message.dispatchEvent(new Event('input'));
  };
  recognition.onend = () => {
    voice.classList.remove('active');
    setBrainState('');
    if (message.value.trim()) ask(message.value);
  };
  recognition.onerror = () => {
    voice.classList.remove('active');
    setBrainState('');
  };
  recognition.start();
}

send.addEventListener('click', () => ask(message.value));
voice.addEventListener('click', startVoice);
message.addEventListener('input', () => {
  message.style.height = '42px';
  message.style.height = `${Math.min(message.scrollHeight, 150)}px`;
});
message.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    ask(message.value);
  }
});
document.querySelectorAll('[data-prompt]').forEach((button) => {
  button.addEventListener('click', () => ask(button.dataset.prompt || ''));
});
newChat.addEventListener('click', () => {
  window.speechSynthesis?.cancel();
  window.location.reload();
});

void speakingTimer;
