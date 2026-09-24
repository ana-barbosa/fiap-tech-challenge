from openai import OpenAI, OpenAIError

from . import config

_client = OpenAI(api_key=config.OPENAI_API_KEY)


class SpeechError(Exception):
    pass


def transcribe(filename: str, audio_bytes: bytes) -> str:
    try:
        result = _client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_bytes),
            language="pt",
        )
    except OpenAIError as exc:
        raise SpeechError(str(exc)) from exc

    return result.text.strip()
