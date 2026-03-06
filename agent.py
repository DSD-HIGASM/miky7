import os, subprocess, psutil, base64, re, logging, socket, uuid, json
import threading, time, urllib.request
from urllib.error import URLError, HTTPError
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import BACKEND_TOKEN

try:
    from config import HOSPITAL_NAME
except ImportError:
    HOSPITAL_NAME = "Establecimiento de Salud"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =================================================================
# INYECCIÓN AUTOMÁTICA OTA: PANTALLA MANTENIMIENTO INSTITUCIONAL
# =================================================================
def setup_mantenimiento_ui():
    html_path = os.path.expanduser("~/control_remoto/mantenimiento.html")
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atención en Curso - {HOSPITAL_NAME}</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap" rel="stylesheet">

    <style>
        :root {
            --pba-pink: #e81f76;
            --pba-blue: #417099;
            --pba-cyan: #00aec3;
            --bg-main: #f1f5f9;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
        }
        
        * { box-sizing: border-box; }
        
        body, html {
            margin: 0; padding: 0; 
            height: 100vh; width: 100vw;
            background-color: var(--bg-main);
            font-family: 'Roboto', system-ui, -apple-system, sans-serif;
            overflow: hidden; 
            display: flex; flex-direction: column;
        }
        
        .pba-gradient-bar {
            height: 22px;
            width: 100%;
            background: linear-gradient(90deg, var(--pba-pink) 0%, var(--pba-blue) 50%, var(--pba-cyan) 100%);
            flex-shrink: 0;
        }

        .content-wrapper {
            flex: 1; display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            padding: 3rem 4rem;
        }

        .glass-card {
            background: var(--card-bg);
            border-radius: 2.5rem;
            padding: 6rem 8rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(0,0,0,0.02);
            text-align: center;
            max-width: 85vw;
            display: flex; flex-direction: column; align-items: center;
        }

        .icon-container {
            background-color: rgba(232, 31, 118, 0.08); 
            border-radius: 50%;
            padding: 2.5rem;
            margin-bottom: 2.5rem;
            animation: pulse-soft 3s ease-in-out infinite;
        }

        .warning-icon {
            width: 100px; height: 100px; 
            color: var(--pba-pink);
        }

        h1 {
            font-size: 5.2rem; font-weight: 900;
            color: var(--text-main);
            margin: 0 0 1.5rem 0;
            text-transform: uppercase; 
            letter-spacing: -1px; line-height: 1.1;
        }

        .subtitle {
            font-size: 3.2rem; font-weight: 400;
            color: var(--text-muted);
            margin: 0 0 4.5rem 0;
            line-height: 1.3;
        }

        .instruction-box {
            background: rgba(65, 112, 153, 0.06); 
            border: 2px solid rgba(65, 112, 153, 0.15);
            border-left: 14px solid var(--pba-blue);
            padding: 4rem 5.5rem;
            border-radius: 1rem 2rem 2rem 1rem;
            display: inline-block;
        }

        .instruction-box p {
            font-size: 3.8rem; font-weight: 500;
            color: var(--text-main);
            margin: 0; line-height: 1.35;
        }

        .highlight { 
            color: var(--pba-blue); 
            font-weight: 900; 
        }

        .footer-bar {
            background-color: var(--card-bg);
            padding: 0 5rem;
            height: 160px;
            display: flex; justify-content: space-between; align-items: center;
            border-top: 1px solid rgba(0,0,0,0.08);
            box-shadow: 0 -4px 20px rgba(0,0,0,0.03);
            flex-shrink: 0;
        }

        .footer-logos {
            display: flex; align-items: center; gap: 3rem;
            height: 100%;
        }

        .logo-separator {
            height: 65px;
            width: 2px;
            background-color: #cbd5e1;
            border-radius: 2px;
        }

        .logo-provincia {
            height: 85px; width: auto;
            object-fit: contain;
            mix-blend-mode: multiply;
        }

        .logo-hospital {
            height: 90px; width: auto;
            object-fit: contain;
            mix-blend-mode: multiply;
        }

        .reconnect-status {
            display: flex; align-items: center; gap: 1.5rem;
            background: var(--bg-main);
            padding: 1.8rem 3.5rem; border-radius: 100px;
            border: 1px solid rgba(0,0,0,0.05);
        }

        .spinner {
            width: 32px; height: 32px;
            border: 5px solid rgba(0, 174, 195, 0.2);
            border-top-color: var(--pba-cyan);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        .reconnect-status span {
            font-size: 1.6rem; font-weight: 700; color: var(--pba-cyan); text-transform: uppercase; letter-spacing: 1.5px;
        }

        @keyframes pulse-soft {
            0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(232, 31, 118, 0.2); }
            50% { transform: scale(1.02); box-shadow: 0 0 0 20px rgba(232, 31, 118, 0); }
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="pba-gradient-bar"></div>
    
    <main class="content-wrapper">
        <div class="glass-card">
            <div class="icon-container">
                <svg class="warning-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>
            </div>
            <h1>Pantalla en Mantenimiento</h1>
            <p class="subtitle">La atención de pacientes continúa desarrollándose con normalidad.</p>
            
            <div class="instruction-box">
                <p>Aguarde en la sala de espera.<br>Será llamado <span class="highlight">a viva voz por su nombre.</span></p>
            </div>
        </div>
    </main>

    <footer class="footer-bar">
        <div class="footer-logos">
            <img src="ministerio.svg" alt="Ministerio de Salud PBA" class="logo-provincia" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iODAiPjx0ZXh0IHk9IjQwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIyNCIgZmlsbD0iIzQxNzA5OSIgZm9udC13ZWlnaHQ9ImJvbGQiPk1JTklTVEVSSU8gREUgU0FMVUQ8L3RleHQ+PC9zdmc+'">
            <div class="logo-separator"></div>
            <img src="logo_hospital.jpg" alt="{HOSPITAL_NAME}" class="logo-hospital">
        </div>
        <div class="reconnect-status">
            <div class="spinner"></div>
            <span>Restableciendo sistema visual...</span>
        </div>
    </footer>
</body>
</html>"""

    # Inyección de variable python dentro del string de forma segura
    html_content = html_content.replace("{HOSPITAL_NAME}", HOSPITAL_NAME)

    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f: 
        f.write(html_content)

try:
    setup_mantenimiento_ui()
except Exception as e:
    logging.error(f"Fallo inicial: {e}")

# =================================================================
# BASE DE DATOS Y RED
# =================================================================
STARTUP_URL_FILE = os.path.expanduser("~/kiosko_startup.url")
CACHE_DIR = os.path.expanduser("~/.config/chromium-kiosko-hsi/Default/Cache/*")
DB_FILE = os.path.expanduser("~/miki_db.json")

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"pcs": [], "tgToken": "", "tgChat": "", "sectors": [], "globalDefault": ""}

def save_db(data):
    try:
        with open(DB_FILE, 'w') as f: json.dump(data, f)
    except: pass

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except: ip = '127.0.0.1'
    finally: s.close()
    return ip

# =================================================================
# WATCHDOG FAILOVER
# =================================================================
hsi_is_down = False
def watchdog_hsi():
    global hsi_is_down
    maint_url = f"file://{os.path.expanduser('~/control_remoto/mantenimiento.html')}"
    sh_path = os.path.expanduser('~/iniciar_kiosko.sh')
    
    while True:
        time.sleep(15) 
        try:
            with open(STARTUP_URL_FILE, 'r') as f: target_url = f.read().strip()
        except: continue
            
        if "mantenimiento.html" in target_url or not target_url.startswith("http"): continue
        current_status_down = False
        try:
            req = urllib.request.Request(target_url, headers={'User-Agent': 'Miki/Failover'})
            with urllib.request.urlopen(req, timeout=7) as response:
                if response.status >= 500: current_status_down = True
        except HTTPError as e:
            if e.code >= 500: current_status_down = True
        except URLError: current_status_down = True
        except Exception: current_status_down = True

        if current_status_down and not hsi_is_down:
            hsi_is_down = True
            cmd = f"export DISPLAY=:0 && pkill chromium && sleep 2 && chromium --kiosk --no-first-run --autoplay-policy=no-user-gesture-required {maint_url} > /dev/null 2>&1 &"
            subprocess.Popen(cmd, shell=True)
        elif not current_status_down and hsi_is_down:
            hsi_is_down = False
            subprocess.Popen(f"export DISPLAY=:0 && nohup bash {sh_path} > /dev/null 2>&1 &", shell=True)

threading.Thread(target=watchdog_hsi, daemon=True).start()

# =================================================================
# CLÚSTER MESH: V3.1 - Liderazgo Estricto
# =================================================================
current_leader = None
offline_counters = {}
known_status = {}

def get_tg_timestamp(): return time.strftime("%d/%m/%Y %H:%M:%S")

def send_telegram(token, chat, text):
    if not token or not chat: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat, "text": text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req, timeout=5)
    except: pass

def mesh_network_engine():
    global current_leader, offline_counters, known_status
    first_run = True
    while True:
        time.sleep(10)
        db = load_db()
        pcs = db.get("pcs", [])
        if not pcs: continue

        my_ip = get_local_ip()
        alive_ips = [my_ip]
        
        for pc in pcs:
            ip = pc.get("ip")
            if not ip or ip == my_ip: continue
            try:
                req = urllib.request.Request(f"http://{ip}:5000/status")
                with urllib.request.urlopen(req, timeout=3) as response:
                    if response.status == 200: alive_ips.append(ip)
            except: pass

        try:
            sorted_ips = sorted(alive_ips, key=lambda x: [int(p) for p in x.split('.')])
            current_leader = sorted_ips[0]
        except:
            current_leader = my_ip

        for pc in pcs:
            ip = pc.get("ip")
            if not ip or ip == my_ip: continue

            if ip in alive_ips:
                offline_counters[ip] = 0
                if known_status.get(ip, True) is False:
                    known_status[ip] = True
                    if current_leader == my_ip and not first_run:
                        msg = f"✅ <b>SISTEMA RESTAURADO</b>\n🖥️ {pc.get('name')}\n🌐 <code>{ip}</code>\n🕒 {get_tg_timestamp()}"
                        send_telegram(db.get("tgToken"), db.get("tgChat"), msg)
            else:
                offline_counters[ip] = offline_counters.get(ip, 0) + 1
                if offline_counters[ip] >= 3 and known_status.get(ip, True) is True:
                    known_status[ip] = False
                    if current_leader == my_ip and not first_run:
                        msg = f"🚨 <b>ALERTA CRÍTICA: OFFLINE</b>\n🖥️ {pc.get('name')}\n🌐 <code>{ip}</code>\n🕒 {get_tg_timestamp()}"
                        send_telegram(db.get("tgToken"), db.get("tgChat"), msg)
        
        first_run = False

threading.Thread(target=mesh_network_engine, daemon=True).start()

# =================================================================
# SERVIDOR FLASK API
# =================================================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def verificar_auth(req):
    token = req.headers.get('Authorization')
    if token and "Bearer" in token: return token.split(" ")[1] == BACKEND_TOKEN
    return False

def run_cmd(cmd):
    try:
        uid = os.getuid()
        full_cmd = f"export DISPLAY=:0 && export XDG_RUNTIME_DIR=/run/user/{uid} && {cmd}"
        subprocess.run(full_cmd, shell=True, check=True)
        return True
    except: return False

def get_mac():
    try:
        mac_num = hex(uuid.getnode()).replace('0x', '').upper()
        return ':'.join(mac_num.zfill(12)[i: i + 2] for i in range(0, 11, 2))
    except: return "00:00:00:00:00:00"

def send_wol(macaddress):
    try:
        data = bytes.fromhex('FF' * 6 + macaddress.replace(':', '').replace('-', '') * 16)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(data, ('255.255.255.255', 9))
        return True
    except: return False

@app.route('/sync', methods=['GET'])
def get_sync():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    return jsonify({"db": load_db(), "current_leader": current_leader, "my_ip": get_local_ip()})

@app.route('/sync', methods=['POST'])
def post_sync():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    save_db(request.json)
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
        output = subprocess.check_output(f"export XDG_RUNTIME_DIR=/run/user/{uid} && pactl get-sink-volume @DEFAULT_SINK@", shell=True, stderr=subprocess.DEVNULL).decode()
        match = re.search(r"(\d+)%", output)
        if match: vol = match.group(1)
    except: vol = "Err"
    return jsonify({"status": "online", "cpu": cpu, "url": url, "vol": vol, "mac": get_mac(), "leader": current_leader})

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
        if target_mac: send_wol(target_mac)
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
    elif acc == 'clear_cron':
        os.system("crontab -l 2>/dev/null | grep -v 'dpms' | crontab -")
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
