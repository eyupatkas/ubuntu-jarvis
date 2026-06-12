import os
import sys

# Auto-relaunch using virtual environment python if not already running in it
venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python")
if sys.prefix == sys.base_prefix and os.path.exists(venv_python):
    print("\033[93mVirtual environment is not active. Auto-relaunching with virtual environment python...\033[0m")
    os.execv(venv_python, [venv_python] + sys.argv)

import asyncio
from google import genai
from google.genai import types
import tools


async def test():
    tools.load_env()
    
    API_KEY = os.getenv("GEMINI_API_KEY")
    MODEL = "gemini-3.1-flash-live-preview"
    
    if not API_KEY:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)
        
    print(f"Testing Gemini Live connection with model '{MODEL}' using API key '{API_KEY[:6]}...'")
    
    client = genai.Client(api_key=API_KEY)
    
    config = {
        "response_modalities": ["AUDIO"],
        "system_instruction": "Sen yardımcı bir asistansın. Türkçe konuş.",
        "output_audio_transcription": {},
        "input_audio_transcription": {},
    }
    
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("\033[92mSuccessfully connected to Gemini Live API WebSocket!\033[0m")
            
            # Send initial greeting
            print("Sending text greeting: 'Merhaba'")
            await session.send_realtime_input(
                text="Merhaba"
            )
            
            # Receive response
            print("Waiting for response...")
            async for response in session.receive():
                sc = response.server_content
                if sc:
                    if sc.output_transcription:
                        print(f"\033[94mReceived Transcription: {sc.output_transcription.text}\033[0m")
                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data and isinstance(part.inline_data.data, bytes):
                                print(f"\033[92mReceived {len(part.inline_data.data)} bytes of audio data!\033[0m")
                                print("\033[92mTest Succeeded!\033[0m")
                                return
                if sc and sc.turn_complete:
                    break
            
            print("Connection handshake succeeded.")
    except Exception as e:
        print(f"\033[91mConnection test failed: {e}\033[0m", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test())
