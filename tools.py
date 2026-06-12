import os
import subprocess

def load_env():
    """Loads environment variables from local .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key, val = parts
                        os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Load environment on import
load_env()

def execute_command(command: str) -> str:
    """Executes a system shell command on Ubuntu and returns its output.
    Sudo commands are automatically executed using the stored system password.
    
    Args:
        command: The command to execute (e.g. 'ls -la', 'sudo systemctl restart nginx').
    """
    sudo_password = os.getenv("SUDO_PASSWORD", "1998")
    
    # Prevent recursive execution of the voice assistant
    cmd_clean = command.strip().lower()
    if "main.py" in cmd_clean or "screencast_helper.py" in cmd_clean:
        return "Error: Running the assistant itself recursively via shell commands is not allowed."
        
    try:
        import re
        has_sudo = re.search(r'\bsudo\b', command) is not None
        
        if has_sudo:
            # If command uses sudo, make sure it has -S so it reads from stdin
            command = re.sub(r'\bsudo\b', 'sudo -S', command)
            stdin_val = f"{sudo_password}\n"
        else:
            stdin_val = None
            
        # Run the command
        res = subprocess.run(
            command,
            input=stdin_val,
            capture_output=True,
            text=True,
            shell=True,
            timeout=300
        )
        
        result = ""
        if res.stdout:
            result += res.stdout
        if res.stderr:
            # Filter out localized or standard sudo password prompts from stderr
            lines = res.stderr.splitlines()
            clean_lines = []
            for line in lines:
                l_lower = line.lower()
                if "[sudo]" in l_lower or "[sudo:" in l_lower or "parola:" in l_lower or "password:" in l_lower:
                    continue
                clean_lines.append(line)
            
            clean_stderr = "\n".join(clean_lines).strip()
            if clean_stderr:
                result += f"\nError/Stderr:\n{clean_stderr}"
                
        return result.strip() or "Command completed with no output."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def adjust_volume(level: int) -> str:
    """Adjusts the system audio volume level.
    
    Args:
        level: The target volume level percentage (0 to 100).
    """
    if not (0 <= level <= 100):
        return "Error: Volume level must be between 0 and 100."
    try:
        res = subprocess.run(
            f"amixer sset Master {level}%",
            capture_output=True,
            text=True,
            shell=True
        )
        if res.returncode == 0:
            return f"System volume successfully set to {level}%."
        else:
            return f"Error adjusting volume: {res.stderr.strip()}"
    except Exception as e:
        return f"Error adjusting volume: {str(e)}"

def get_system_status() -> str:
    """Retrieves Ubuntu system status including CPU load, memory usage, and disk space."""
    try:
        # Load average
        with open("/proc/loadavg", "r") as f:
            load = f.read().strip()
        
        # Memory usage
        mem_res = subprocess.run("free -h", capture_output=True, text=True, shell=True)
        mem = mem_res.stdout.strip()
        
        # Disk space
        disk_res = subprocess.run("df -h /", capture_output=True, text=True, shell=True)
        disk = disk_res.stdout.strip()
        
        return f"Load Average: {load}\n\nMemory:\n{mem}\n\nDisk Space:\n{disk}"
    except Exception as e:
        return f"Error reading system status: {str(e)}"

def show_desktop_notification(title: str, message: str) -> str:
    """Displays a desktop notification using notify-send.
    
    Args:
        title: The title of the notification.
        message: The main message content.
    """
    try:
        safe_title = title.replace('"', '\\"')
        safe_msg = message.replace('"', '\\"')
        subprocess.run(
            f'notify-send "{safe_title}" "{safe_msg}"',
            shell=True
        )
        return f"Notification '{title}' shown successfully."
    except Exception as e:
        return f"Error showing notification: {str(e)}"

def open_application(app_name: str, arguments: str = "") -> str:
    """Launches a desktop application on Ubuntu in the background with optional arguments.
    
    Args:
        app_name: The name or executable of the application (e.g. 'firefox', 'gnome-terminal', 'code').
        arguments: Optional command line arguments/URLs to pass to the application.
    """
    import shutil
    
    app = app_name.lower().strip()
    
    candidates = {
        "chrome": ["google-chrome", "google-chrome-stable", "chrome"],
        "brave": ["brave", "brave-browser"],
        "brave browser": ["brave", "brave-browser"],
        "brave-browser": ["brave", "brave-browser"],
        "vscode": ["code", "code-insiders"],
        "code": ["code", "code-insiders"],
        "terminal": ["ptyxis", "gnome-terminal", "kgx", "gnome-console", "x-terminal-emulator", "konsole", "xfce4-terminal", "alacritty", "kitty", "xterm"],
        "gnome-terminal": ["gnome-terminal", "ptyxis", "kgx", "gnome-console", "x-terminal-emulator"],
        "gnome-console": ["gnome-console", "kgx", "ptyxis", "gnome-terminal", "x-terminal-emulator"],
        "ptyxis": ["ptyxis", "gnome-terminal", "kgx", "gnome-console", "x-terminal-emulator"],
        "browser": ["firefox", "google-chrome", "brave", "chromium-browser"],
        "firefox": ["firefox"],
        "files": ["nautilus", "dolphin", "thunar", "pcmanfm"],
        "calculator": ["gnome-calculator", "kcalc"]
    }
    
    binary = app_name
    if app in candidates:
        for b in candidates[app]:
            if shutil.which(b):
                binary = b
                break
        else:
            binary = candidates[app][0]
    else:
        if shutil.which(app):
            binary = app
            
    try:
        # Check if the binary is actually installed/available in PATH
        if not shutil.which(binary):
            return f"Error: Application '{app_name}' (binary '{binary}') is not installed or not in PATH."
            
        cmd = [binary]
        if arguments:
            import shlex
            cmd.extend(shlex.split(arguments))
            
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return f"Application '{binary}' launched successfully with arguments: '{arguments}'" if arguments else f"Application '{binary}' launched successfully."
    except Exception as e:
        return f"Error launching application '{binary}': {str(e)}"

def open_url(url: str) -> str:
    """Opens a URL in the default web browser on Ubuntu.
    
    Args:
        url: The website URL to open (e.g. 'https://google.com', 'youtube.com').
    """
    try:
        # Prepend https:// if it is a domain without scheme
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return f"URL '{url}' opened in default browser."
    except Exception as e:
        return f"Error opening URL: {str(e)}"

def ensure_ydotoold_running():
    """Ensures that the ydotoold daemon is running. If not, starts it as root using sudo."""
    import subprocess
    import os
    import time
    
    try:
        res = subprocess.run("pgrep ydotoold", shell=True, capture_output=True)
        if res.returncode == 0:
            return True
            
        # Start ydotoold as root
        sudo_password = os.getenv("SUDO_PASSWORD", "1998")
        socket_path = "/run/user/1000/.ydotool_socket"
        
        # Ensure parent dir exists
        os.makedirs("/run/user/1000", exist_ok=True)
        
        cmd = f"echo {sudo_password} | sudo -S ydotoold --socket-path={socket_path} --socket-own=1000:1000"
        subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"Error ensuring ydotoold is running: {e}")
        return False

def simulate_keyboard(text: str) -> str:
    """Simulates typing the given text on the keyboard.
    
    Args:
        text: The text to type (e.g. 'Hello World').
    """
    ensure_ydotoold_running()
    try:
        import subprocess
        res = subprocess.run(
            ["ydotool", "type", text],
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            return f"Successfully typed text."
        else:
            return f"Error simulating keyboard: {res.stderr.strip()}"
    except Exception as e:
        return f"Error simulating keyboard: {str(e)}"

def simulate_key_combination(combination: str) -> str:
    """Simulates pressing a combination of keys (e.g. 'ctrl+t', 'alt+tab', 'enter', 'escape', 'super+d').
    
    Args:
        combination: Key combination string, lowercase, separated by '+' (e.g. 'ctrl+t', 'enter').
    """
    ensure_ydotoold_running()
    
    KEY_MAP = {
        "ctrl": 29, "leftctrl": 29, "rightctrl": 97,
        "shift": 42, "leftshift": 42, "rightshift": 54,
        "alt": 56, "leftalt": 56, "rightalt": 100,
        "meta": 125, "super": 125, "win": 125,
        "enter": 28, "return": 28, "esc": 1, "escape": 1,
        "backspace": 14, "tab": 15, "space": 57,
        "up": 103, "down": 108, "left": 105, "right": 106,
        "pgup": 104, "pgdn": 109, "home": 102, "end": 107,
        "ins": 110, "del": 111, "delete": 111,
        "a": 30, "b": 48, "c": 46, "d": 32, "e": 18, "f": 33, "g": 34, "h": 35,
        "i": 23, "j": 36, "k": 37, "l": 38, "m": 50, "n": 49, "o": 24, "p": 25,
        "q": 16, "r": 19, "s": 31, "t": 20, "u": 22, "v": 47, "w": 17, "x": 45,
        "y": 21, "z": 44,
        "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
        "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64,
        "f7": 65, "f8": 66, "f9": 67, "f10": 68, "f11": 87, "f12": 88
    }
    
    parts = [p.strip().lower() for p in combination.split("+") if p.strip()]
    if not parts:
        return "Error: Empty key combination."
        
    keycodes = []
    for p in parts:
        if p in KEY_MAP:
            keycodes.append(KEY_MAP[p])
        else:
            return f"Error: Key '{p}' is not supported in mapping."
            
    args = []
    for kc in keycodes[:-1]:
        args.append(f"{kc}:1")
        
    last_kc = keycodes[-1]
    args.append(f"{last_kc}:1")
    args.append(f"{last_kc}:0")
    
    for kc in reversed(keycodes[:-1]):
        args.append(f"{kc}:0")
        
    try:
        import subprocess
        res = subprocess.run(
            ["ydotool", "key"] + args,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            return f"Successfully triggered key combination '{combination}'."
        else:
            return f"Error simulating key combination: {res.stderr.strip()}"
    except Exception as e:
        return f"Error simulating key combination: {str(e)}"

def click_mouse(button: str = "left", action: str = "click") -> str:
    """Simulates clicking, pressing down, or releasing a mouse button.
    
    Args:
        button: The mouse button ('left', 'right', 'middle'). Default is 'left'.
        action: The action to perform ('click' for a full click, 'down' to hold button down, 'up' to release). Default is 'click'.
    """
    ensure_ydotoold_running()
    
    btn_map = {
        "left": {"click": "0xC0", "down": "0x40", "up": "0x80"},
        "right": {"click": "0xC1", "down": "0x41", "up": "0x81"},
        "middle": {"click": "0xC2", "down": "0x42", "up": "0x82"}
    }
    
    btn = button.lower().strip()
    act = action.lower().strip()
    if btn not in btn_map:
        return f"Error: Mouse button '{button}' is not supported. Choose from 'left', 'right', 'middle'."
    if act not in btn_map[btn]:
        return f"Error: Action '{action}' is not supported. Choose from 'click', 'down', 'up'."
        
    try:
        import subprocess
        res = subprocess.run(
            ["ydotool", "click", btn_map[btn][act]],
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            return f"Successfully performed mouse {act} on {button} button."
        else:
            return f"Error simulating mouse click: {res.stderr.strip()}"
    except Exception as e:
        return f"Error simulating mouse click: {str(e)}"

def move_mouse(x: int, y: int, absolute: bool = True) -> str:
    """Simulates moving the mouse cursor to a specific coordinate or relatively.
    
    Args:
        x: The horizontal coordinate/offset.
        y: The vertical coordinate/offset.
        absolute: True to move to absolute coordinates, False for relative offset.
    """
    ensure_ydotoold_running()
    
    args = ["ydotool", "mousemove"]
    if absolute:
        args.append("-a")
    args.extend([str(x), str(y)])
    
    try:
        import subprocess
        res = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            return f"Successfully moved mouse to ({x}, {y}) (absolute={absolute})."
        else:
            return f"Error simulating mouse movement: {res.stderr.strip()}"
    except Exception as e:
        return f"Error simulating mouse movement: {str(e)}"

def drag_mouse(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    """Simulates dragging and dropping the mouse from a start coordinate to an end coordinate.
    Useful for dragging windows, dragging sliders, or selecting text.
    
    Args:
        start_x: The starting horizontal coordinate.
        start_y: The starting vertical coordinate.
        end_x: The ending horizontal coordinate.
        end_y: The ending vertical coordinate.
    """
    ensure_ydotoold_running()
    try:
        import subprocess
        # 1. Move to start
        res = subprocess.run(["ydotool", "mousemove", "-a", str(start_x), str(start_y)], capture_output=True, timeout=5)
        if res.returncode != 0:
            return f"Error moving to start position: {res.stderr.strip()}"
            
        # 2. Mouse down (0x40 for left mouse down)
        res = subprocess.run(["ydotool", "click", "0x40"], capture_output=True, timeout=5)
        if res.returncode != 0:
            return f"Error pressing mouse down: {res.stderr.strip()}"
            
        # 3. Move to end
        res = subprocess.run(["ydotool", "mousemove", "-a", str(end_x), str(end_y)], capture_output=True, timeout=5)
        if res.returncode != 0:
            # Try to release anyway to not lock the mouse
            subprocess.run(["ydotool", "click", "0x80"], capture_output=True)
            return f"Error moving to end position: {res.stderr.strip()}"
            
        # 4. Mouse up (0x80 for left mouse up)
        res = subprocess.run(["ydotool", "click", "0x80"], capture_output=True, timeout=5)
        if res.returncode != 0:
            return f"Error releasing mouse: {res.stderr.strip()}"
            
        return f"Successfully dragged mouse from ({start_x}, {start_y}) to ({end_x}, {end_y})."
    except Exception as e:
        # Try to release anyway
        try:
            subprocess.run(["ydotool", "click", "0x80"], capture_output=True)
        except:
            pass
        return f"Error dragging mouse: {str(e)}"

def load_memory_context() -> str:
    """Hatırlanan tüm gerçekleri sistem talimatı için okunabilir bir metin olarak döner."""
    import json
    memory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")
    if os.path.exists(memory_path):
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            facts = data.get("facts", [])
            if facts:
                return "\nKullanıcı hakkında hatırladığın kalıcı bilgiler:\n" + "\n".join([f"- {fact}" for fact in facts])
        except Exception:
            pass
    return ""

def remember_fact(fact: str) -> str:
    """Kullanıcı hakkında yeni bir bilgiyi (ad, tercih, alışkanlık vb.) kalıcı hafızaya kaydeder.
    Böylece sonraki oturumlarda kullanıcıyı ve tercihlerini unutmazsın.
    
    Args:
        fact: Hatırlanacak bilgi/gerçek (örn. 'Kullanıcının adı Eyüp', 'Kullanıcı Brave tarayıcıyı tercih ediyor').
    """
    import json
    memory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")
    
    data = {"facts": []}
    if os.path.exists(memory_path):
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "facts" not in data:
                data["facts"] = []
        except:
            pass
            
    if fact not in data["facts"]:
        data["facts"].append(fact)
        try:
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return f"Bilgi başarıyla hafızaya kaydedildi: '{fact}'"
        except Exception as e:
            return f"Hafızaya yazılırken hata oluştu: {str(e)}"
    else:
        return "Bu bilgi zaten hafızada kayıtlı."

def forget_fact(fact: str) -> str:
    """Daha önce hafızaya kaydedilmiş bir bilgiyi kalıcı hafızadan siler.
    
    Args:
        fact: Silinecek bilginin tam metni.
    """
    import json
    memory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")
    
    if not os.path.exists(memory_path):
        return "Hafıza dosyası bulunamadı."
        
    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "facts" in data and fact in data["facts"]:
            data["facts"].remove(fact)
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return f"Bilgi hafızadan başarıyla silindi: '{fact}'"
        else:
            return f"Belirtilen bilgi hafızada bulunamadı: '{fact}'"
    except Exception as e:
        return f"Hafızadan silinirken hata oluştu: {str(e)}"

def get_memory() -> str:
    """Kalıcı hafızadaki tüm kayıtlı bilgileri okur ve listeler."""
    import json
    memory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")
    if not os.path.exists(memory_path):
        return "Kalıcı hafıza henüz boş."
    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        facts = data.get("facts", [])
        if not facts:
            return "Kalıcı hafızada kayıtlı bilgi yok."
        return "\n".join([f"- {fact}" for fact in facts])
    except Exception as e:
        return f"Hafıza okunurken hata oluştu: {str(e)}"

def configure_auto_updates(enabled: bool, check_interval_days: int = 1) -> str:
    """Ubuntu üzerinde otomatik sistem güncellemelerini (unattended-upgrades) etkinleştirir veya devre dışı bırakır.
    
    Args:
        enabled: Otomatik güncellemeleri açmak için True, kapatmak için False.
        check_interval_days: Güncellemelerin kaç günde bir kontrol edileceği (varsayılan: 1, yani her gün).
    """
    import os
    import subprocess
    
    sudo_password = os.getenv("SUDO_PASSWORD", "1998")
    
    # 1. Paket yüklü mü kontrol et
    try:
        res = subprocess.run(
            "dpkg-query -W -f='${Status}' unattended-upgrades",
            shell=True,
            capture_output=True,
            text=True
        )
        if "ok installed" not in res.stdout:
            # Yükle
            install_cmd = f"echo {sudo_password} | sudo -S apt-get update && echo {sudo_password} | sudo -S apt-get install -y unattended-upgrades"
            inst_res = subprocess.run(install_cmd, shell=True, capture_output=True, text=True)
            if inst_res.returncode != 0:
                return f"Hata: unattended-upgrades paketi kurulu değil ve kurulurken hata oluştu: {inst_res.stderr.strip()}"
    except Exception as e:
        return f"unattended-upgrades kontrol/kurulum hatası: {str(e)}"
        
    # 2. /etc/apt/apt.conf.d/20auto-upgrades dosyasına yaz
    interval = str(check_interval_days) if enabled else "0"
    config_content = (
        f'APT::Periodic::Update-Package-Lists "{interval}";\n'
        f'APT::Periodic::Unattended-Upgrade "{interval}";\n'
    )
    
    try:
        temp_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_auto_upgrades")
        with open(temp_file_path, "w") as f:
            f.write(config_content)
            
        write_cmd = f"echo {sudo_password} | sudo -S cp {temp_file_path} /etc/apt/apt.conf.d/20auto-upgrades && echo {sudo_password} | sudo -S chmod 644 /etc/apt/apt.conf.d/20auto-upgrades"
        write_res = subprocess.run(write_cmd, shell=True, capture_output=True, text=True)
        
        try:
            os.remove(temp_file_path)
        except:
            pass
            
        if write_res.returncode == 0:
            status_str = f"günlük (her {check_interval_days} günde bir) olarak etkinleştirildi" if enabled else "devre dışı bırakıldı"
            return f"Otomatik sistem güncellemeleri başarıyla {status_str}."
        else:
            return f"Yapılandırma yazılırken hata oluştu: {write_res.stderr.strip()}"
            
    except Exception as e:
        return f"Otomatik güncellemeleri yapılandırırken hata oluştu: {str(e)}"

def get_auto_updates_status() -> str:
    """Ubuntu üzerinde otomatik sistem güncellemelerinin aktiflik durumunu ve sıklığını okur."""
    import os
    import re
    
    config_path = "/etc/apt/apt.conf.d/20auto-upgrades"
    if not os.path.exists(config_path):
        return "Otomatik sistem güncelleme yapılandırma dosyası bulunamadı (varsayılan olarak devre dışı)."
        
    try:
        with open(config_path, "r") as f:
            content = f.read()
            
        update_match = re.search(r'APT::Periodic::Update-Package-Lists\s+"(\d+)"', content)
        upgrade_match = re.search(r'APT::Periodic::Unattended-Upgrade\s+"(\d+)"', content)
        
        update_interval = update_match.group(1) if update_match else None
        upgrade_interval = upgrade_match.group(1) if upgrade_match else None
        
        if upgrade_interval == "0" or not upgrade_interval:
            return "Otomatik sistem güncellemeleri şu anda devre dışı."
        else:
            return f"Otomatik güncellemeler ETKİN. Paket listesi güncelleme sıklığı: {update_interval} günde bir, Otomatik yükseltme (unattended-upgrade) sıklığı: {upgrade_interval} günde bir."
    except Exception as e:
        return f"Otomatik güncelleme durumu okunurken hata oluştu: {str(e)}"

def shutdown_assistant() -> str:
    """Sesli asistan uygulamasını tamamen kapatır ve sonlandırır (Çıkış yapar)."""
    import os
    import signal
    import time
    import threading
    
    def trigger_shutdown():
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)
        
    threading.Thread(target=trigger_shutdown, daemon=True).start()
    return "Asistan başarıyla kapatılıyor. Görüşmek üzere!"

# Expose tools list for the model config
TOOLS_LIST = [
    execute_command,
    adjust_volume,
    get_system_status,
    show_desktop_notification,
    open_application,
    open_url,
    simulate_keyboard,
    simulate_key_combination,
    click_mouse,
    move_mouse,
    drag_mouse,
    remember_fact,
    forget_fact,
    get_memory,
    configure_auto_updates,
    get_auto_updates_status,
    shutdown_assistant
]
