import os, subprocess, psutil, base64, re, logging, socket, uuid
import threading, time, urllib.request
from urllib.error import URLError, HTTPError
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import BACKEND_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

STARTUP_URL_FILE = os.path.expanduser("~/kiosko_startup.url")
CACHE_DIR = os.path.expanduser("~/.config/chromium-kiosko-hsi/Default/Cache/*")

# =================================================================
# WATCHDOG FAILOVER: Auto-curación ante caída de HSI
# =================================================================
hsi_is_down = False

def watchdog_hsi():
    global hsi_is_down
    maint_url = f"file://{os.path.expanduser('~/control_remoto/mantenimiento.html')}"
    sh_path = os.path.expanduser('~/iniciar_kiosko.sh')
    tts_dir = os.path.expanduser('~/control_remoto/miki_tts')
    
    while True:
        time.sleep(15) # Escaneo cada 15 segundos
        try:
            with open(STARTUP_URL_FILE, 'r') as f: target_url = f.read().strip()
        except:
            continue
            
        # Ignoramos si la placa de mantenimiento fue puesta manualmente o no es web
        if "mantenimiento.html" in target_url or not target_url.startswith("http"):
            continue

        current_status_down = False
        try:
            req = urllib.request.Request(target_url, headers={'User-Agent': 'Miki/Failover'})
            with urllib.request.urlopen(req, timeout=7) as response:
                if response.status >= 500:
                    current_status_down = True
        except HTTPError as e:
            if e.code >= 500: current_status_down = True
        except URLError:
            current_status_down = True # Timeout, sin internet, DNS roto
        except Exception:
            current_status_down = True

        if current_status_down and not hsi_is_down:
            hsi_is_down = True
            logging.info("HSI CAÍDA: Failover visual activado.")
            cmd = f"export DISPLAY=:0 && pkill chromium && sleep 2 && chromium --kiosk --no-first-run --autoplay-policy=no-user-gesture-required --load-extension={tts_dir} {maint_url} > /dev/null 2>&1 &"
            subprocess.Popen(cmd, shell=True)
            
        elif not current_status_down and hsi_is_down:
            hsi_is_down = False
            logging.info("HSI RECUPERADA: Restaurando turnero.")
            subprocess.Popen(f"export DISPLAY=:0 && nohup bash {sh_path} > /dev/null 2>&1 &", shell=True)

# Iniciar el guardián en segundo plano
threading.Thread(target=watchdog_hsi, daemon=True).start()
# =================================================================

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def verificar_auth(req):
    token = req.headers.get('Authorization')
    if token and "Bearer" in token:
        return token.split(" ")[1] == BACKEND_TOKEN
    return False

def run_cmd(cmd):
    try:
        uid = os.getuid()
        full_cmd = f"export DISPLAY=:0 && export XDG_RUNTIME_DIR=/run/user/{uid} && {cmd}"
        subprocess.run(full_cmd, shell=True, check=True)
        return True
    except Exception as e:
        logging.error(f"Error ejecutando {cmd}: {e}")
        return False

def get_mac():
    try:
        mac_num = hex(uuid.getnode()).replace('0x', '').upper()
        mac_num = mac_num.zfill(12)
        return ':'.join(mac_num[i: i + 2] for i in range(0, 11, 2))
    except: return "00:00:00:00:00:00"

def send_wol(macaddress):
    try:
        macaddress = macaddress.replace(':', '').replace('-', '')
        data = bytes.fromhex('FF' * 6 + macaddress * 16)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(data, ('255.255.255.255', 9))
        return True
    except: return False

@app.route('/speak', methods=['POST'])
def speak():
    if request.remote_addr not in ['127.0.0.1', 'localhost']:
        if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    texto = request.json.get('texto', '')
    if texto:
        texto_limpio = texto.replace("'", "").replace('"', "")
        run_cmd(f"espeak -v es-la -s 140 '{texto_limpio}'")
    return jsonify({"status": "ok"})

@app.route('/status', methods=['GET'])
def status():
    try: cpu = psutil.cpu_percent(interval=0.1)
    except: cpu = 0
    try: 
        with open(STARTUP_URL_FILE, 'r') as f: url = f.read().strip()
    except: url = "Sin Configurar"
    vol = "0"
    try:
        uid = os.getuid()
        cmd_vol = f"export XDG_RUNTIME_DIR=/run/user/{uid} && pactl get-sink-volume @DEFAULT_SINK@"
        output = subprocess.check_output(cmd_vol, shell=True, stderr=subprocess.DEVNULL).decode()
        match = re.search(r"(\d+)%", output)
        if match: vol = match.group(1)
    except Exception as e:
        vol = "Err"
    return jsonify({"status": "online", "cpu": cpu, "url": url, "vol": vol, "mac": get_mac()})

@app.route('/set_startup', methods=['POST'])
def set_startup():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    url = request.json.get('url')
    with open(STARTUP_URL_FILE, 'w') as f: f.write(url)
    os.system(f"nohup bash {os.path.expanduser('~/iniciar_kiosko.sh')} > /dev/null 2>&1 &")
    return jsonify({"status": "ok", "url": url})

@app.route('/control', methods=['POST'])
def control():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    acc = request.json.get('accion')
    if acc == 'refresh': run_cmd("xdotool search --onlyvisible --class 'chromium' windowactivate key F5")
    elif acc == 'clear_cache': run_cmd(f"rm -rf {CACHE_DIR} && xdotool search --onlyvisible --class 'chromium' windowactivate key F5")
    elif acc == 'reboot': os.system("sudo reboot")
    elif acc == 'update_agent':
        repo_url = request.json.get('url')
        if repo_url:
            install_path = os.path.dirname(os.path.abspath(__file__))
            cmd = f"sleep 2 && wget -4 -qO /tmp/new_agent.py {repo_url} && mv /tmp/new_agent.py {install_path}/agent.py && sudo reboot"
            subprocess.Popen(cmd, shell=True)
            return jsonify({"status": "ok", "msg": "OTA iniciada"})
        return jsonify({"error": "Falta URL"}), 400
    elif acc == 'wol':
        target_mac = request.json.get('mac')
        if target_mac:
            send_wol(target_mac)
            return jsonify({"status": "ok"})
    elif acc == 'sleep_screen': run_cmd("xset dpms force off")
    elif acc == 'wake_screen': run_cmd("xset dpms force on && xdotool mousemove 500 500 click 1 && xdotool mousemove 0 0")
    elif acc == 'schedule_power':
        on_t = request.json.get('on_time')
        off_t = request.json.get('off_time')
        if on_t and off_t:
            on_h, on_m = on_t.split(':')
            off_h, off_m = off_t.split(':')
            uid = os.getuid()
            os.system(f"crontab -l 2>/dev/null | grep -v 'dpms' > /tmp/mycron")
            os.system(f"echo '{off_m} {off_h} * * * export DISPLAY=:0 && export XDG_RUNTIME_DIR=/run/user/{uid} && xset dpms force off' >> /tmp/mycron")
            os.system(f"echo '{on_m} {on_h} * * * export DISPLAY=:0 && export XDG_RUNTIME_DIR=/run/user/{uid} && xset dpms force on && xdotool mousemove 500 500 click 1 && xdotool mousemove 0 0' >> /tmp/mycron")
            os.system(f"crontab /tmp/mycron")
            return jsonify({"status": "ok"})
    elif acc == 'vol_up': run_cmd("pactl set-sink-volume @DEFAULT_SINK@ +5%")
    elif acc == 'vol_down': run_cmd("pactl set-sink-volume @DEFAULT_SINK@ -5%")
    return jsonify({"status": "ok"})

@app.route('/screenshot', methods=['GET'])
def screenshot():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    p = "/tmp/shot.png"
    if os.path.exists(p): os.remove(p)
    run_cmd(f"scrot -z -q 40 {p}") 
    if os.path.exists(p):
        with open(p, "rb") as f:
            return jsonify({"image": base64.b64encode(f.read()).decode('utf-8')})
    return jsonify({"error": "Fail"}), 500
