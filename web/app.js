const chat = document.getElementById('chat');
const message = document.getElementById('message');
const send = document.getElementById('send');
const newChat = document.getElementById('newChat');
const typing = document.getElementById('typing');

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

async function ask(text) {
  const value = text.trim();
  if (!value || send.disabled) return;

  const welcome = document.querySelector('.welcome');
  if (welcome) welcome.remove();

  addMessage('user', value);
  message.value = '';
  message.style.height = '42px';
  send.disabled = true;
  setTyping(true);

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: value })
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    addMessage('assistant', data.answer || 'Não recebi uma resposta válida.');
  } catch (error) {
    addMessage('assistant', `Não consegui conectar ao núcleo agora. ${error.message}`);
  } finally {
    setTyping(false);
    send.disabled = false;
    message.focus();
  }
}

send.addEventListener('click', () => ask(message.value));

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

newChat.addEventListener('click', () => window.location.reload());
