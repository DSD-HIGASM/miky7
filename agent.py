import os, subprocess, psutil, base64, re, logging, socket, uuid
import threading, time, urllib.request
from urllib.error import URLError, HTTPError
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import BACKEND_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =================================================================
# INYECCIÓN AUTOMÁTICA OTA: PANTALLA MANTENIMIENTO PRO V2
# =================================================================
def setup_mantenimiento_ui():
    html_path = os.path.expanduser("~/control_remoto/mantenimiento.html")
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema Interrumpido</title>
    <style>
        :root { --bg: #0f172a; --text: #f8fafc; --accent: #0284c7; --warn: #00aec3; }
        body, html { margin: 0; padding: 0; height: 100vh; background-color: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; overflow: hidden; display: flex; flex-direction: column; }
        .top-bar { height: 16px; background: linear-gradient(90deg, #0ea5e9, #0284c7, #00aec3); width: 100%; }
        .main { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 2rem; }
        .card { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 3rem; padding: 6rem 5rem; max-width: 85%; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); position: relative; backdrop-filter: blur(10px); }
        .card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 6px; background: var(--warn); border-radius: 3rem 3rem 0 0; }
        .icon { width: 130px; height: 130px; color: var(--warn); margin-bottom: 3rem; animation: pulse 3s infinite ease-in-out; }
        @keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.05); opacity: 1; } }
        h1 { font-size: 5.5rem; font-weight: 900; margin: 0 0 1.5rem; letter-spacing: -2px; text-transform: uppercase; line-height: 1; }
        .lead { font-size: 3.5rem; font-weight: 600; color: #cbd5e1; margin: 0 0 3rem; line-height: 1.2; }
        .sub { font-size: 2.2rem; font-weight: 500; color: #94a3b8; background: rgba(0,0,0,0.4); padding: 1.5rem 3.5rem; border-radius: 100px; display: inline-block; margin: 0; border: 1px solid rgba(255,255,255,0.05); }
        .footer { padding: 3.5rem 5rem; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); background: rgba(0,0,0,0.2); }
        .higa { text-align: left; }
        .higa-title { font-size: 2.2rem; font-weight: 800; margin: 0; }
        .higa-sub { font-size: 1.6rem; font-weight: 500; color: #94a3b8; margin: 0.5rem 0 0; }
        .status { display: flex; align-items: center; gap: 1.5rem; background: rgba(2,132,199,0.15); border: 2px solid var(--accent); padding: 1.5rem 3rem; border-radius: 100px; }
        .spinner { width: 32px; height: 32px; border: 4px solid rgba(255,255,255,0.2); border-top-color: #fff; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .status-text { font-size: 1.6rem; font-weight: 700; letter-spacing: 0.5px; }
    </style>
</head>
<body>
    <div class="top-bar"></div>
    <div class="main">
        <div class="card">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
            <h1>SISTEMA INTERRUMPIDO</h1>
            <p class="lead">Esté atento al llamado a viva voz<br>de los profesionales médicos</p>
            <p class="sub">La atención a pacientes continúa con normalidad</p>
        </div>
    </div>
    <div class="footer">
        <div class="higa">
            <p class="higa-title">HIGA Gral. San Martín</p>
            <p class="higa-sub">Ministerio de Salud | Provincia de Buenos Aires</p>
        </div>
        <div class="status">
            <div class="spinner"></div>
            <span class="status-text">Reconectando con HSI...</span>
        </div>
    </div>
</body>
</html>"""
    with open(html_path, "w", encoding="utf-8") as f: 
        f.write(html_content)

try:
    setup_tts_extension()
    setup_mantenimiento_ui()
except Exception as e:
    logging.error(f"Fallo en configuraciones iniciales: {e}")
# =================================================================

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
        time.sleep(15) 
        try:
            with open(STARTUP_URL_FILE, 'r') as f: target_url = f.read().strip()
        except:
            continue
            
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
            current_status_down = True
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
