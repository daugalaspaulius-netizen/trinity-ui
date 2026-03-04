# Trinity Local Integrated Test UI

This project provides a single local interface for:
- Text chat (ChatGPT-like flow)
- Voice recording and speech-to-text (Whisper endpoint)
- Read latest assistant message aloud (browser speech synthesis or server TTS)
- Copy/paste message controls
- Mobile-friendly responsive web layout

## Run

```powershell
# From workspace root
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn trinity_app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:
- Local: `http://127.0.0.1:8000`
- Phone on same network: `http://<YOUR_PC_IP>:8000`

## Optional Engine Integration

If you already have Trinity backend, set:

```powershell
$env:TRINITY_ENGINE_URL = "http://127.0.0.1:9000/api/chat"
```

Request format expected by this UI adapter:

```json
{ "message": "Sveiki" }
```

Response accepted:

```json
{ "reply": "Labas" }
```

## Whisper Model

Whisper is loaded lazily on `/api/stt`.
Set model size if needed:

```powershell
$env:WHISPER_MODEL = "small"  # tiny|base|small|medium|large
```

## Notes

- If server Whisper is unavailable, frontend falls back to browser speech recognition (when supported).
- This keeps end-to-end testing possible before full model fine-tuning.
