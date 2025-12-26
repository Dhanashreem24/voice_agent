from fastapi import APIRouter, UploadFile
from audio.stt import speech_to_text
from audio.tts import text_to_speech
import shutil

router = APIRouter()

@router.post("/voice")
async def voice_chat(file: UploadFile):
    audio_path = f"/tmp/{file.filename}"

    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user_text = speech_to_text(audio_path)

    # Send to Gemini agent (text only)
    agent_reply = f"You said: {user_text}"

    output_audio = text_to_speech(agent_reply)

    return {
        "input_text": user_text,
        "response_text": agent_reply,
        "audio_file": output_audio
    }
