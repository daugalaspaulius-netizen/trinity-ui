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
const voiceVizWrap = document.getElementById('voiceVizWrap');
const voiceCanvas = document.getElementById('voiceCanvas');

let mediaRecorder = null;
let audioChunks = [];
let lastAssistantMessage = '';
let audioContext = null;
let analyser = null;
let analyserData = null;
let vizFrameId = null;

function startVoiceVisualization(stream) {
  if (!voiceCanvas || !voiceVizWrap) return;
  const canvasCtx = voiceCanvas.getContext('2d');
  if (!canvasCtx) return;

  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(stream);
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 2048;
  analyserData = new Uint8Array(analyser.frequencyBinCount);
  source.connect(analyser);

  voiceVizWrap.hidden = false;

  const draw = () => {
    if (!analyser) return;
    analyser.getByteTimeDomainData(analyserData);

    const w = voiceCanvas.width;
    const h = voiceCanvas.height;
    canvasCtx.clearRect(0, 0, w, h);

    canvasCtx.lineWidth = 2;
    canvasCtx.strokeStyle = '#1f5c4d';
    canvasCtx.beginPath();

    const sliceWidth = w / analyserData.length;
    let x = 0;

    for (let i = 0; i < analyserData.length; i += 1) {
      const v = analyserData[i] / 128.0;
      const y = (v * h) / 2;
      if (i === 0) {
        canvasCtx.moveTo(x, y);
      } else {
        canvasCtx.lineTo(x, y);
      }
      x += sliceWidth;
    }

    canvasCtx.lineTo(w, h / 2);
    canvasCtx.stroke();
    vizFrameId = requestAnimationFrame(draw);
  };

  draw();
}

async function stopVoiceVisualization() {
  if (vizFrameId) {
    cancelAnimationFrame(vizFrameId);
    vizFrameId = null;
  }
  if (audioContext) {
    await audioContext.close();
    audioContext = null;
  }
  analyser = null;
  analyserData = null;
  if (voiceVizWrap) {
    voiceVizWrap.hidden = true;
  }
}

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
      await stopVoiceVisualization();

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
          messageInput.value = data.text.trim();
          messageInput.focus();
          hintEl.textContent = 'Transkribuota. Galite pataisyti teksta ir spausti Siusti.';
        }
      } catch {
        fallbackSpeechRecognition();
      }
    };

    mediaRecorder.start();
    startVoiceVisualization(stream);
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
    hintEl.textContent = 'Irasymas sustabdytas. Vyksta transkripcija i teksto laukeli...';
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
    messageInput.value = text;
    messageInput.focus();
    hintEl.textContent = `Transkribuota: ${text}. Galite pataisyti ir spausti Siusti.`;
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

    messageInput.value = text;
    messageInput.focus();
    hintEl.textContent = `Transkribuota: ${text}. Galite pataisyti ir spausti Siusti.`;
  } catch (error) {
    hintEl.textContent = `Audio ikelimo/transkripcijos klaida: ${error.message}`;
  } finally {
    audioFileInput.value = '';
  }
});

addMessage('assistant', 'Trinity testavimo aplinka paleista. Galite rasyti arba irasyti balso zinute.');
