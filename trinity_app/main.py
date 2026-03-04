from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Trinity Local UI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    source: str


class TrinityEngine:
    """Adapter for local Trinity model backend.

    If TRINITY_ENGINE_URL is provided, requests are proxied there.
    Otherwise, a local deterministic fallback keeps the UI fully testable.
    """

    def __init__(self) -> None:
        self.remote_url = os.getenv("TRINITY_ENGINE_URL", "").strip()

    def ask(self, message: str) -> tuple[str, str]:
        message = message.strip()
        if not message:
            return ("Parasykite zinute, ir as atsakysiu.", "fallback")

        if self.remote_url:
            try:
                import requests

                response = requests.post(
                    self.remote_url,
                    json={"message": message},
                    timeout=60,
                )
                response.raise_for_status()
                payload = response.json()
                reply = payload.get("reply") or payload.get("response") or "Negauta atsakymo"
                return (str(reply), "remote")
            except Exception as exc:  # noqa: BLE001
                return (
                    f"Nepavyko susisiekti su Trinity varikliu ({exc}). Naudoju lokalu rezima.",
                    "fallback",
                )

        return (self._fallback_reply(message), "fallback")

    @staticmethod
    def _fallback_reply(message: str) -> str:
        lower = message.lower()
        if "kas tu" in lower:
            return "As esu Trinity testine autonomine aplinka. Integravimas veikia, toliau jungsime pilna modeli."
        if "blockchain" in lower:
            return "Blockchain sluoksnis turetu registruoti svarbius ivykius. Siame etape testuojame sąsaja ir srautus."
        if "whisper" in lower or "transkr" in lower:
            return "Balso transkripcijai naudokite iraso mygtuka. Jei serverio Whisper neaktyvus, ijungiamas narsykles rezimas."
        return (
            "Trinity UI veikia. Sitas atsakymas yra is lokalaus fallback variklio. "
            "Toliau prijunkime jusu pilna Mistral/Trinity backend endpointa."
        )


engine = TrinityEngine()


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html_path = TEMPLATES_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    reply, source = engine.ask(payload.message)
    return ChatResponse(reply=reply, source=source)


@app.post("/api/stt")
def speech_to_text(file: UploadFile = File(...)) -> dict[str, Any]:
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        temp_path = Path(tmp.name)

    try:
        text = _transcribe_with_whisper(temp_path)
        return {"text": text, "source": "whisper"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=(
                "Whisper transkripcija nepasiekiama siame kompiuteryje. "
                "Frontend naudos narsykles transkribavima, jei palaikoma. "
                f"Detale: {exc}"
            ),
        ) from exc
    finally:
        temp_path.unlink(missing_ok=True)


@app.post("/api/tts")
def text_to_speech(payload: ChatRequest) -> FileResponse:
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Tuscia zinute")

    wav_file = _synthesize_tts(text)
    return FileResponse(path=wav_file, media_type="audio/wav", filename="trinity.wav")


def _transcribe_with_whisper(audio_path: Path) -> str:
    # Lazy import keeps startup light; model loads only when endpoint is used.
    import whisper

    model_name = os.getenv("WHISPER_MODEL", "small")
    model = whisper.load_model(model_name)
    result = model.transcribe(str(audio_path), language="lt", task="transcribe")
    return str(result.get("text", "")).strip()


def _synthesize_tts(text: str) -> str:
    """Generate WAV using pyttsx3 (offline) when available."""
    import pyttsx3

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        out_path = tmp.name

    engine_tts = pyttsx3.init()
    engine_tts.setProperty("rate", 165)
    engine_tts.save_to_file(text, out_path)
    engine_tts.runAndWait()
    return out_path
