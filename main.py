import os
import sys

# Auto-relaunch using virtual environment python if not already running in it
venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python")
if sys.prefix == sys.base_prefix and os.path.exists(venv_python):
    print("\033[93mVirtual environment is not active. Auto-relaunching with virtual environment python...\033[0m")
    os.execv(venv_python, [venv_python] + sys.argv)

import asyncio
import array
import math
from google import genai
from google.genai import types
import tools

def calculate_rms(data: bytes) -> float:
    if not data:
        return 0.0
    try:
        shorts = array.array('h', data)
        sum_squares = 0.0
        for sample in shorts:
            n_sample = sample / 32768.0
            sum_squares += n_sample * n_sample
        return math.sqrt(sum_squares / len(shorts))
    except Exception:
        return 0.0

class AppState:
    def __init__(self):
        self.is_playing = False
        self.last_audio_time = 0.0
        self.last_activity_time = 0.0


# Load environment variables
tools.load_env()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("\033[91mError: GEMINI_API_KEY is not set in .env file.\033[0m", file=sys.stderr)
    print("Please add your key to the .env file first.", file=sys.stderr)
    sys.exit(1)

# Initialize GenAI client
client = genai.Client(api_key=API_KEY)

# Define tool declarations for Gemini Live API
TOOLS_DECLARATIONS = [
    {
        "function_declarations": [
            {
                "name": "execute_command",
                "description": "Executes a system shell command on Ubuntu and returns its output. Sudo commands can be run.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "command": {
                            "type": "STRING",
                            "description": "The shell command to run (e.g. 'ls -la', 'sudo systemctl restart nginx')."
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "adjust_volume",
                "description": "Adjusts the system audio volume level.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "level": {
                            "type": "INTEGER",
                            "description": "The volume level percentage (0 to 100)."
                        }
                    },
                    "required": ["level"]
                }
            },
            {
                "name": "get_system_status",
                "description": "Retrieves Ubuntu system status including CPU load, memory usage, and disk space.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "show_desktop_notification",
                "description": "Displays a desktop notification using notify-send.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {
                            "type": "STRING",
                            "description": "The title of the notification."
                        },
                        "message": {
                            "type": "STRING",
                            "description": "The main message content."
                        }
                    },
                    "required": ["title", "message"]
                }
            },
            {
                "name": "open_application",
                "description": "Launches a desktop application on Ubuntu in the background with optional command line arguments.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "app_name": {
                            "type": "STRING",
                            "description": "The name or executable of the application (e.g. 'firefox', 'gnome-terminal', 'code', 'brave')."
                        },
                        "arguments": {
                            "type": "STRING",
                            "description": "Optional arguments/URLs to pass to the application (e.g. 'https://youtube.com')."
                        }
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "open_url",
                "description": "Opens a URL in the default web browser on Ubuntu.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "url": {
                            "type": "STRING",
                            "description": "The website URL to open (e.g. 'https://google.com', 'youtube.com')."
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "simulate_keyboard",
                "description": "Simulates typing the given text on the keyboard.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "text": {
                            "type": "STRING",
                            "description": "The text to type."
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "simulate_key_combination",
                "description": "Simulates pressing a combination of keys (e.g. 'ctrl+t', 'alt+tab', 'enter', 'escape', 'super+d').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "combination": {
                            "type": "STRING",
                            "description": "Key combination string (e.g. 'ctrl+t', 'alt+tab', 'enter', 'escape', 'win+d')."
                        }
                    },
                    "required": ["combination"]
                }
            },
            {
                "name": "click_mouse",
                "description": "Simulates clicking, pressing down (holding), or releasing a mouse button.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "button": {
                            "type": "STRING",
                            "description": "The mouse button ('left', 'right', 'middle'). Default is 'left'."
                        },
                        "action": {
                            "type": "STRING",
                            "description": "The mouse action ('click' for normal click, 'down' to hold button down, 'up' to release). Default is 'click'."
                        }
                    }
                }
            },
            {
                "name": "move_mouse",
                "description": "Simulates moving the mouse cursor to a specific coordinate or relatively.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "x": {
                            "type": "INTEGER",
                            "description": "The horizontal coordinate/offset."
                        },
                        "y": {
                            "type": "INTEGER",
                            "description": "The vertical coordinate/offset."
                        },
                        "absolute": {
                            "type": "BOOLEAN",
                            "description": "True to move to absolute coordinates, False for relative offset. Default is True."
                        }
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "name": "drag_mouse",
                "description": "Simulates dragging and dropping the mouse from a start coordinate to an end coordinate. Extremely useful for dragging windows, dragging sliders, or selecting text.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "start_x": {
                            "type": "INTEGER",
                            "description": "The starting horizontal coordinate."
                        },
                        "start_y": {
                            "type": "INTEGER",
                            "description": "The starting vertical coordinate."
                        },
                        "end_x": {
                            "type": "INTEGER",
                            "description": "The ending horizontal coordinate."
                        },
                        "end_y": {
                            "type": "INTEGER",
                            "description": "The ending vertical coordinate."
                        }
                    },
                    "required": ["start_x", "start_y", "end_x", "end_y"]
                }
            },
            {
                "name": "remember_fact",
                "description": "Kullanıcı hakkında yeni bir bilgiyi (ad, tercih, alışkanlık vb.) kalıcı hafızaya kaydeder.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "fact": {
                            "type": "STRING",
                            "description": "Hatırlanacak bilgi/gerçek (örn. 'Kullanıcının adı Eyüp', 'Kullanıcı Brave tarayıcıyı tercih ediyor')."
                        }
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "forget_fact",
                "description": "Daha önce kaydedilmiş bir bilgiyi kalıcı hafızadan siler.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "fact": {
                            "type": "STRING",
                            "description": "Silinecek bilginin tam metni."
                        }
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "get_memory",
                "description": "Kalıcı hafızadaki tüm kayıtlı bilgileri okur ve listeler.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "configure_auto_updates",
                "description": "Ubuntu üzerinde otomatik sistem güncellemelerini (unattended-upgrades) etkinleştirir veya devre dışı bırakır.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "enabled": {
                            "type": "BOOLEAN",
                            "description": "Otomatik güncellemeleri açmak için true, kapatmak için false."
                        },
                        "check_interval_days": {
                            "type": "INTEGER",
                            "description": "Güncellemelerin kaç günde bir kontrol edileceği (varsayılan: 1, yani her gün)."
                        }
                    },
                    "required": ["enabled"]
                }
            },
            {
                "name": "get_auto_updates_status",
                "description": "Ubuntu üzerinde otomatik sistem güncellemelerinin aktiflik durumunu ve sıklığını okur.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            }
        ]
    }
]

class AudioPlayer:
    """Manages audio playback via aplay subprocess."""
    def __init__(self):
        self.process = None

    async def start(self):
        if self.process:
            await self.stop()
        output_device = os.getenv("OUTPUT_DEVICE", "default")
        # S16_LE = 16-bit Signed Little-Endian PCM, 24000Hz, 1 channel (mono)
        self.process = await asyncio.create_subprocess_exec(
            "aplay", "-D", output_device, "-t", "raw", "-f", "S16_LE", "-r", "24000", "-c", "1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

    async def write(self, data: bytes):
        if not self.process or self.process.returncode is not None:
            await self.start()
        try:
            self.process.stdin.write(data)
            await self.process.stdin.drain()
        except Exception as e:
            # If standard write fails, restart the process and try again
            await self.start()
            try:
                self.process.stdin.write(data)
                await self.process.stdin.drain()
            except:
                pass

    async def stop(self):
        if self.process:
            try:
                self.process.kill()
            except:
                pass
            self.process = None

class AudioRecorder:
    """Manages microphone audio capture via arecord subprocess."""
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self.process = None
        self.task = None

    async def start(self):
        if self.process:
            await self.stop()
        input_device = os.getenv("INPUT_DEVICE", "default")
        # S16_LE = 16-bit Signed Little-Endian PCM, 16000Hz, 1 channel (mono)
        self.process = await asyncio.create_subprocess_exec(
            "arecord", "-D", input_device, "-t", "raw", "-f", "S16_LE", "-r", "16000", "-c", "1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        self.task = asyncio.create_task(self._read_loop())

    async def _read_loop(self):
        # 1024 samples = 2048 bytes (since each sample is 2 bytes for 16-bit)
        # 1024 samples at 16000Hz is ~64ms of audio data
        chunk_size = 2048
        try:
            while self.process and self.process.returncode is None:
                data = await self.process.stdout.read(chunk_size)
                if not data:
                    await asyncio.sleep(0.01)
                    continue
                # Put raw audio chunk into the queue
                await self.queue.put(data)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        if self.task:
            self.task.cancel()
            self.task = None
        if self.process:
            try:
                self.process.kill()
            except:
                pass
            self.process = None
async def run():
    model = os.getenv("MODEL_NAME", "gemini-2.0-flash-exp")
    
    # Load memory context from persistent storage
    memory_context = tools.load_memory_context()
    
    # Configure Gemini Live Session
    config = {
        "response_modalities": ["AUDIO"],
        "context_window_compression": {
            "sliding_window": {}
        },
        "speech_config": {
            "voice_config": {
                "prebuilt_voice_config": {
                    "voice_name": os.getenv("VOICE_NAME", "Orus")
                }
            }
        },
        "system_instruction": (
            "Sen bir Ubuntu sesli yapay zeka asistanısın. Kullanıcının bilgisayarını yönetmesine yardımcı oluyorsun. "
            "Sana verilen bilgisayar yönetim ve otomasyon araçlarını kullanarak kullanıcının isteklerini yerine getirmelisin. "
            "ÖNEMLİ (Ajan ve Planlama Yeteneği): Karmaşık, çok adımlı veya doğrudan tek bir araçla yapılamayacak görevler aldığında (örn. sunucuya bağlanıp şifre değiştirmek, konfigürasyon dosyalarını bulmak, veritabanı sorgulamak, sistem sorunlarını çözmek vb.), önce içsel düşünme (reasoning/thinking) yeteneğini kullanarak adım adım bir plan yapmalısın. "
            "Hemen aceleyle tek bir rastgele komut çalıştırmak yerine, önce neyi araştırman gerektiğini, hangi dosyaları kontrol etmen gerektiğini planla, ardından bu adımları sırayla çalıştır ve her adımın çıktısına göre planını dinamik olarak güncelle. "
            "Kullanıcı bir web sitesini açmak veya internette arama yapmak isterse her zaman `open_url` aracını kullan. "
            "Konuşurken gizemli, havalı ve bilgili bir hacker (hacker gibi kalın, derin ve karizmatik bir ses tonuyla konuştuğunu hayal et) edasıyla konuşmalısın. "
            "Yanıtların kısa, öz, esprili ve yardımsever olmalı. Türkçe konuşmalısın.\n"
            f"{memory_context}"
        ),
        "tools": TOOLS_DECLARATIONS,
        "thinking_config": {
            "thinking_budget": 2048
        },
        "output_audio_transcription": {},
        "input_audio_transcription": {},
        "realtime_input_config": {
            "automatic_activity_detection": {
                "disabled": False,
                "silence_duration_ms": 1000,
                "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
                "end_of_speech_sensitivity": "END_SENSITIVITY_HIGH",
            }
        }
    }
    
    app_state = AppState()
    BARGE_IN_THRESHOLD = float(os.getenv("BARGE_IN_THRESHOLD", "0.06"))
    DEBUG_RMS = os.getenv("DEBUG_RMS", "false").lower() == "true"

    mic_queue = asyncio.Queue(maxsize=15)
    speaker_queue = asyncio.Queue()
    
    recorder = AudioRecorder(mic_queue)
    player = AudioPlayer()
    
    restore_event_sounds = False
    try:
        # Temporarily mute screenshot camera shutter sound in GNOME by disabling event-sounds
        try:
            proc = await asyncio.create_subprocess_exec(
                "gsettings", "get", "org.gnome.desktop.sound", "event-sounds",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await proc.communicate()
            if stdout and b"true" in stdout.lower():
                proc_set = await asyncio.create_subprocess_exec(
                    "gsettings", "set", "org.gnome.desktop.sound", "event-sounds", "false",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc_set.wait()
                restore_event_sounds = True
                print("\033[94mTemporarily muted GNOME screenshot shutter sound.\033[0m")
        except:
            pass

        await recorder.start()
        await player.start()
        
        print(f"\033[93mConnecting to Gemini Live API ({model})...\033[0m")
        async with client.aio.live.connect(model=model, config=config) as session:
            print("\033[92mConnected successfully! Start speaking to the assistant.\033[0m")
            app_state.last_activity_time = asyncio.get_event_loop().time()
            print("Say 'Sistem sesini yüzde 50 yap' or 'Firefox aç' or 'CPU kontrol et' to test tools.")
            print("Press Ctrl+C to stop.")
            
            def check_is_playing():
                if not app_state.is_playing:
                    return False
                if speaker_queue.empty():
                    now = asyncio.get_event_loop().time()
                    if now - app_state.last_audio_time > 0.4:
                        app_state.is_playing = False
                return app_state.is_playing

            # Worker to send audio from mic queue to Gemini session
            async def send_mic_task():
                try:
                    send_mic_task.last_debug_time = 0.0
                    while True:
                        data = await mic_queue.get()
                        
                        rms = calculate_rms(data)
                        currently_playing = check_is_playing()
                        
                        now = asyncio.get_event_loop().time()
                        if rms > BARGE_IN_THRESHOLD:
                            app_state.last_activity_time = now
                        if DEBUG_RMS and (now - send_mic_task.last_debug_time > 0.5):
                            send_mic_task.last_debug_time = now
                            print(f"\n[DEBUG RMS] Mic RMS: {rms:.4f} (Threshold: {BARGE_IN_THRESHOLD}, Playing: {currently_playing})", flush=True)
                        
                        if currently_playing:
                            if rms > BARGE_IN_THRESHOLD:
                                print(f"\n\033[91m[Barge-in Detected: RMS {rms:.4f} > {BARGE_IN_THRESHOLD}]\033[0m", flush=True)
                                # Clear output queue immediately
                                while not speaker_queue.empty():
                                    try:
                                        speaker_queue.get_nowait()
                                        speaker_queue.task_done()
                                    except asyncio.QueueEmpty:
                                        break
                                # Stop player to kill current aplay process
                                await player.stop()
                                app_state.is_playing = False
                                
                                # Send the loud user chunk
                                await session.send_realtime_input(
                                    audio=types.Blob(
                                        data=data,
                                        mime_type="audio/pcm;rate=16000"
                                    )
                                )
                            else:
                                # Send silence chunk to suppress echo
                                silence_data = b'\x00' * len(data)
                                await session.send_realtime_input(
                                    audio=types.Blob(
                                        data=silence_data,
                                        mime_type="audio/pcm;rate=16000"
                                    )
                                )
                        else:
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=data,
                                    mime_type="audio/pcm;rate=16000"
                                )
                            )
                        mic_queue.task_done()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error in mic sending task: {e}", file=sys.stderr)
            
            # Worker to write audio chunks to speaker subprocess
            async def play_speaker_task():
                try:
                    while True:
                        data = await speaker_queue.get()
                        app_state.is_playing = True
                        now = asyncio.get_event_loop().time()
                        app_state.last_audio_time = now
                        app_state.last_activity_time = now
                        await player.write(data)
                        speaker_queue.task_done()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error in audio playback task: {e}", file=sys.stderr)
            
            # Worker to capture and send screen frames to Gemini session
            async def send_screen_task():
                SCREEN_SHARE = os.getenv("SCREEN_SHARE", "true").lower() == "true"
                SCREEN_SHARE_FPS = float(os.getenv("SCREEN_SHARE_FPS", "1.0"))
                
                if not SCREEN_SHARE:
                    return
                    
                print(f"\033[94mScreen sharing is active. Sharing screen with Gemini at {SCREEN_SHARE_FPS} FPS.\033[0m")
                helper_proc = None
                try:
                    # Start the helper process to create a Mutter ScreenCast session
                    helper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screencast_helper.py")
                    helper_proc = await asyncio.create_subprocess_exec(
                        "/usr/bin/python3", helper_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    node_id = None
                    # Read helper output to get the PipeWire Node ID
                    while True:
                        line_bytes = await helper_proc.stdout.readline()
                        if not line_bytes:
                            break
                        line = line_bytes.decode().strip()
                        if line.startswith("NODE_ID:"):
                            node_id = line.split(":")[1]
                            break
                    
                    if not node_id:
                        print("\033[91mError: Screencast helper failed to provide a PipeWire Node ID.\033[0m", file=sys.stderr)
                        return
                    
                    print(f"\033[94mSuccessfully established PipeWire screencast session. Node ID: {node_id}\033[0m")
                    
                    while True:
                        start_time = asyncio.get_event_loop().time()
                        
                        # Grab frame from the PipeWire stream using GStreamer quiet mode
                        proc = await asyncio.create_subprocess_exec(
                            "gst-launch-1.0", "-q", "pipewiresrc", f"path={node_id}", "num-buffers=1",
                            "!", "videoconvert", "!", "pngenc", "!", "filesink", "location=/dev/stdout",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        stdout, _ = await proc.communicate()
                        
                        if stdout and stdout.startswith(b'\x89PNG'):
                            # Send frame to the live session
                            await session.send_realtime_input(
                                video=types.Blob(
                                    data=stdout,
                                    mime_type="image/png"
                                )
                            )
                            
                        # Sleep to match target FPS
                        elapsed = asyncio.get_event_loop().time() - start_time
                        sleep_time = max(0.01, (1.0 / SCREEN_SHARE_FPS) - elapsed)
                        await asyncio.sleep(sleep_time)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error in screen sharing task: {e}", file=sys.stderr)
                finally:
                    if helper_proc:
                        try:
                            helper_proc.kill()
                        except:
                            pass

            # Worker to receive responses from Gemini session
            async def receive_task():
                try:
                    last_was_input = False
                    while True:
                        async for response in session.receive():
                            # Handle server content (audio output and text transcription)
                            sc = response.server_content
                            if sc:
                                app_state.last_activity_time = asyncio.get_event_loop().time()
                                # Handle interruption (user speaks while bot is speaking)
                                if sc.interrupted:
                                    print("\n\033[91m[Interrupted by User]\033[0m", flush=True)
                                    app_state.is_playing = False
                                    # Clear the output queue immediately
                                    while not speaker_queue.empty():
                                        try:
                                            speaker_queue.get_nowait()
                                            speaker_queue.task_done()
                                        except asyncio.QueueEmpty:
                                            break
                                    # Restart the player to flush its internal buffers
                                    await player.stop()
                                    await player.start()
                                    continue
                                
                                # Put incoming audio into speaker queue
                                if sc.model_turn:
                                    for part in sc.model_turn.parts:
                                        if part.inline_data and isinstance(part.inline_data.data, bytes):
                                            speaker_queue.put_nowait(part.inline_data.data)
                                
                                # Print transcribed user speech
                                if sc.input_transcription:
                                    if not last_was_input:
                                        print()
                                        last_was_input = True
                                    print(f"\033[94mUser: {sc.input_transcription.text}\033[0m", flush=True)
                                
                                # Print transcribed model speech
                                if sc.output_transcription:
                                    if last_was_input:
                                        print()
                                        last_was_input = False
                                    print(f"\033[92mGemini: {sc.output_transcription.text}\033[0m", end="", flush=True)
                            
                            # Handle tool calls requested by Gemini
                            if response.tool_call:
                                app_state.last_activity_time = asyncio.get_event_loop().time()
                                function_calls = response.tool_call.function_calls
                                for call in function_calls:
                                    name = call.name
                                    args = call.args
                                    call_id = call.id
                                    
                                    print(f"\n\033[95m[Tool Call] Executing '{name}' with arguments: {args}...\033[0m")
                                    
                                    # Execute the requested tool in a background thread to avoid blocking the event loop
                                    result = ""
                                    if name == "execute_command":
                                        result = await asyncio.to_thread(tools.execute_command, args.get("command", ""))
                                    elif name == "adjust_volume":
                                        result = await asyncio.to_thread(tools.adjust_volume, int(args.get("level", 0)))
                                    elif name == "get_system_status":
                                        result = await asyncio.to_thread(tools.get_system_status)
                                    elif name == "show_desktop_notification":
                                        result = await asyncio.to_thread(
                                            tools.show_desktop_notification,
                                            args.get("title", ""), args.get("message", "")
                                        )
                                    elif name == "open_application":
                                        result = await asyncio.to_thread(
                                            tools.open_application, 
                                            args.get("app_name", ""),
                                            args.get("arguments", "")
                                        )
                                    elif name == "open_url":
                                        result = await asyncio.to_thread(tools.open_url, args.get("url", ""))
                                    elif name == "simulate_keyboard":
                                        result = await asyncio.to_thread(tools.simulate_keyboard, args.get("text", ""))
                                    elif name == "simulate_key_combination":
                                        result = await asyncio.to_thread(tools.simulate_key_combination, args.get("combination", ""))
                                    elif name == "click_mouse":
                                        result = await asyncio.to_thread(
                                            tools.click_mouse,
                                            args.get("button", "left"),
                                            args.get("action", "click")
                                        )
                                    elif name == "move_mouse":
                                        result = await asyncio.to_thread(
                                            tools.move_mouse,
                                            int(args.get("x", 0)),
                                            int(args.get("y", 0)),
                                            bool(args.get("absolute", True))
                                        )
                                    elif name == "drag_mouse":
                                        result = await asyncio.to_thread(
                                            tools.drag_mouse,
                                            int(args.get("start_x", 0)),
                                            int(args.get("start_y", 0)),
                                            int(args.get("end_x", 0)),
                                            int(args.get("end_y", 0))
                                        )
                                    elif name == "remember_fact":
                                        result = await asyncio.to_thread(tools.remember_fact, args.get("fact", ""))
                                    elif name == "forget_fact":
                                        result = await asyncio.to_thread(tools.forget_fact, args.get("fact", ""))
                                    elif name == "get_memory":
                                        result = await asyncio.to_thread(tools.get_memory)
                                    elif name == "configure_auto_updates":
                                        result = await asyncio.to_thread(
                                            tools.configure_auto_updates,
                                            bool(args.get("enabled", False)),
                                            int(args.get("check_interval_days", 1))
                                        )
                                    elif name == "get_auto_updates_status":
                                        result = await asyncio.to_thread(tools.get_auto_updates_status)
                                    else:
                                        result = f"Error: Tool '{name}' not found."
                                    
                                    print(f"\033[96m[Tool Result] {result}\033[0m")
                                    
                                    # Send tool response back to the session
                                    function_response = types.FunctionResponse(
                                        name=name,
                                        response={"result": result},
                                        id=call_id
                                    )
                                    await session.send_tool_response(function_responses=function_response)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error in receiving loop task: {e}", file=sys.stderr)
            
            # Worker to periodically make proactive comments on screen contents if idle
            async def proactive_comment_task():
                proactive_interval = float(os.getenv("PROACTIVE_VISION_INTERVAL", "45.0"))
                if proactive_interval <= 0:
                    return
                print(f"\033[94mProactive Screen Advisor is active (checks screen every {proactive_interval} seconds of idle time).\033[0m")
                try:
                    while True:
                        await asyncio.sleep(5.0)  # Check status every 5 seconds
                        
                        now = asyncio.get_event_loop().time()
                        time_since_last_activity = now - app_state.last_activity_time
                        
                        # Check conditions:
                        # 1. Screen sharing must be active (the task is running and SCREEN_SHARE is true)
                        # 2. Enough time has passed since last activity (user speaking or model speaking)
                        # 3. Model is not currently playing audio
                        # 4. Speaker queue is empty
                        if (time_since_last_activity >= proactive_interval and 
                            not app_state.is_playing and 
                            speaker_queue.empty()):
                            
                            # Reset activity time first so we don't double trigger
                            app_state.last_activity_time = now
                            
                            print("\n\033[95m[Proactive Event] Triggering spontaneous screen commentary...\033[0m")
                            # Send proactive prompt to the session
                            prompt_text = (
                                "[Sistem Olayı: Canlı Ekran Danışmanı aktif. Kullanıcının şu an ekranında açık olan uygulamaya, "
                                "koda, tarayıcı sekmelerine veya içeriğe bakarak hacker edasıyla proaktif, zekice veya "
                                "eğlenceli/esprili çok kısa bir yorum yap ya da takıldığı/incelediği bir yer varsa tavsiye ver! "
                                "Eğer ekranda ilginç veya yeni bir şey yoksa, sessiz kalabilir veya hafifçe takılabilirsin. "
                                "Yanıtın en fazla 1-2 cümle olsun.]"
                            )
                            await session.send_realtime_input(text=prompt_text)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error in proactive comment task: {e}", file=sys.stderr)
            
            # Start mic, speaker, receiver, and proactive advisor tasks
            tasks = [
                asyncio.create_task(send_mic_task()),
                asyncio.create_task(play_speaker_task()),
                asyncio.create_task(send_screen_task()),
                asyncio.create_task(receive_task()),
                asyncio.create_task(proactive_comment_task())
            ]
            
            try:
                await asyncio.gather(*tasks)
            finally:
                # Cancel all tasks to prevent "destroyed but pending" warning
                for t in tasks:
                    if not t.done():
                        t.cancel()
                # Wait for all tasks to be cancelled
                await asyncio.gather(*tasks, return_exceptions=True)
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        if "loop is closed" not in str(e).lower():
            print(f"\n\033[91mSession error: {e}\033[0m", file=sys.stderr)
    finally:
        if restore_event_sounds:
            try:
                import subprocess
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.sound", "event-sounds", "true"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("\033[94mRestored GNOME event sounds to original state.\033[0m")
            except:
                pass
        print("\nStopping recorder and playback player...")
        try:
            await recorder.stop()
            await player.stop()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nExited by user.")
