const chatEl = document.getElementById('chat');
const template = document.getElementById('messageTemplate');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const uploadAudioBtn = document.getElementById('uploadAudioBtn');
const audioFileInput = document.getElementById('audioFileInput');
const readLastBtn = document.getElementById('readLastBtn');
const hintEl = document.getElementById('hint');
const engineBadge = document.getElementById('engineBadge');

let mediaRecorder = null;
let audioChunks = [];
let lastAssistantMessage = '';

function addMessage(role, text) {
  const clone = template.content.firstElementChild.cloneNode(true);
  clone.classList.add(role);
  clone.querySelector('.role').textContent = role === 'user' ? 'Jus' : 'Trinity';
  clone.querySelector('.content').textContent = text;

  const copyBtn = clone.querySelector('.copy-btn');
  copyBtn.addEventListener('click', async () => {
    await navigator.clipboard.writeText(text);
    copyBtn.textContent = 'Copied';
    setTimeout(() => {
      copyBtn.textContent = 'Copy';
    }, 1000);
  });

  chatEl.appendChild(clone);
  chatEl.scrollTop = chatEl.scrollHeight;

  if (role === 'assistant') {
    lastAssistantMessage = text;
  }
}

async function sendMessage(rawText) {
  const text = rawText.trim();
  if (!text) return;

  addMessage('user', text);
  messageInput.value = '';

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    engineBadge.textContent = `engine: ${data.source}`;
    addMessage('assistant', data.reply);
  } catch (error) {
    addMessage('assistant', `Klaida bendraujant su backend: ${error.message}`);
  }
}

sendBtn.addEventListener('click', () => sendMessage(messageInput.value));
messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage(messageInput.value);
  }
});

readLastBtn.addEventListener('click', async () => {
  if (!lastAssistantMessage) return;

  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(lastAssistantMessage);
    utterance.lang = 'lt-LT';
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
    return;
  }

  try {
    const response = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: lastAssistantMessage })
    });
    if (!response.ok) throw new Error('TTS nepasiekiamas');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play();
  } catch (error) {
    hintEl.textContent = `TTS klaida: ${error.message}`;
  }
});

recordBtn.addEventListener('click', async () => {
  if (!window.isSecureContext && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
    hintEl.textContent = 'Mikrofonas uzblokuotas, nes puslapis atidarytas per nesaugia nuoroda (http LAN). Naudokite Ikelti audio arba atidarykite per localhost/https.';
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    fallbackSpeechRecognition();
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());

      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('file', blob, 'recording.webm');

      try {
        const response = await fetch('/api/stt', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          fallbackSpeechRecognition();
          return;
        }

        const data = await response.json();
        if (data.text?.trim()) {
          await sendMessage(data.text);
        }
      } catch {
        fallbackSpeechRecognition();
      }
    };

    mediaRecorder.start();
    recordBtn.disabled = true;
    stopBtn.disabled = false;
    hintEl.textContent = 'Irasymas vyksta... spauskite Stop.';
  } catch (error) {
    if (error && (error.name === 'NotAllowedError' || error.name === 'SecurityError')) {
      hintEl.textContent = 'Naršykle neleido mikrofono (Not Allowed). Patikrinkite Site settings -> Microphone -> Allow, arba naudokite mygtuka Ikelti audio.';
      return;
    }
    hintEl.textContent = `Nepavyko pradeti irasymo: ${error.message}`;
  }
});

stopBtn.addEventListener('click', () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    recordBtn.disabled = false;
    stopBtn.disabled = true;
    hintEl.textContent = 'Irasymas sustabdytas. Vyksta transkripcija...';
  }
});

function fallbackSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    hintEl.textContent = 'Nera nei serverio Whisper, nei narsykles SpeechRecognition.';
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = 'lt-LT';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  hintEl.textContent = 'Narsykles transkripcija aktyvi. Kalbekite...';
  recognition.start();

  recognition.onresult = async (event) => {
    const text = event.results[0][0].transcript;
    hintEl.textContent = `Transkribuota: ${text}`;
    await sendMessage(text);
  };

  recognition.onerror = (event) => {
    hintEl.textContent = `SpeechRecognition klaida: ${event.error}`;
  };
}

uploadAudioBtn.addEventListener('click', () => {
  audioFileInput.click();
});

audioFileInput.addEventListener('change', async (event) => {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file, file.name || 'audio-upload');
  hintEl.textContent = 'Ikelta. Vyksta transkripcija...';

  try {
    const response = await fetch('/api/stt', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const text = (data.text || '').trim();
    if (!text) {
      hintEl.textContent = 'Transkripcija tuscia. Bandykite aiskesni irasa.';
      return;
    }

    hintEl.textContent = `Transkribuota: ${text}`;
    await sendMessage(text);
  } catch (error) {
    hintEl.textContent = `Audio ikelimo/transkripcijos klaida: ${error.message}`;
  } finally {
    audioFileInput.value = '';
  }
});

addMessage('assistant', 'Trinity testavimo aplinka paleista. Galite rasyti arba irasyti balso zinute.');
