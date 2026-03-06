import os, subprocess, psutil, base64, re, logging, socket, uuid, json
import threading, time, urllib.request
from urllib.error import URLError, HTTPError
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import BACKEND_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =================================================================
# INYECCIÓN AUTOMÁTICA OTA: PANTALLA MANTENIMIENTO CLARA
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
        :root { --pba-pink: #e81f76; --pba-blue: #417099; --pba-cyan: #00aec3; --bg: #f8fafc; --text: #0f172a; }
        body, html { background-color: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; overflow: hidden; }
        .pba-gradient-bar { position: absolute; top: 0; left: 0; width: 100%; height: 16px; background: linear-gradient(90deg, var(--pba-pink) 0%, var(--pba-blue) 50%, var(--pba-cyan) 100%); }
        .card { background: #ffffff; border: 1px solid rgba(0,0,0,0.05); border-radius: 2rem; padding: 5rem; max-width: 85%; box-shadow: 0 20px 40px -10px rgba(0,0,0,0.08); display: flex; flex-direction: column; align-items: center; }
        .logos-container { display: flex; align-items: center; gap: 40px; margin-bottom: 40px; }
        .logo-higa { height: 120px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
        .icon-alert { width: 100px; height: 100px; color: var(--pba-cyan); animation: pulse 2.5s infinite ease-in-out; }
        @keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.05); opacity: 1; } }
        h1 { font-weight: 900; font-size: 5rem; color: #1e293b; margin: 0 0 20px 0; text-transform: uppercase; letter-spacing: -1px; }
        p.instruccion { font-size: 3rem; font-weight: 600; color: #475569; margin: 0; line-height: 1.3; }
        .highlight { color: var(--pba-blue); font-weight: 800; }
        .footer { position: absolute; bottom: 0; left: 0; width: 100%; padding: 2.5rem 0; background: #ffffff; border-top: 1px solid rgba(0,0,0,0.05); display: flex; justify-content: space-around; align-items: center; box-shadow: 0 -10px 20px rgba(0,0,0,0.02); }
        .footer-text { display: flex; flex-direction: column; text-align: left; }
        .footer-text strong { font-size: 1.8rem; color: var(--pba-blue); font-weight: 800; }
        .footer-text span { font-size: 1.2rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
        .spinner-container { display: flex; align-items: center; gap: 15px; background: rgba(65,112,153,0.05); padding: 1rem 2rem; border-radius: 50px; border: 1px solid rgba(65,112,153,0.15); }
        .spinner { width: 24px; height: 24px; border: 3px solid rgba(65,112,153,0.2); border-top-color: var(--pba-blue); border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .spinner-text { font-size: 1.2rem; font-weight: 700; color: var(--pba-blue); }
    </style>
</head>
<body>
    <div class="pba-gradient-bar"></div>
    <div class="card">
        <div class="logos-container">
            <svg class="icon-alert" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
            <img src="logo_higa.jpg" alt="HIGA Gral San Martín" class="logo-higa" onerror="this.style.display='none'">
        </div>
        <h1>Sistema temporalmente interrumpido</h1>
        <p class="instruccion">Esté atento al <span class="highlight">llamado a viva voz</span> e indicaciones<br>del personal para su atención</p>
    </div>
    <div class="footer">
        <div class="footer-text">
            <strong>HIGA Gral. San Martín</strong>
            <span>Ministerio de Salud | Provincia de Buenos Aires</span>
        </div>
        <div class="spinner-container">
            <div class="spinner"></div>
            <span class="spinner-text">Reconectando con HSI...</span>
        </div>
    </div>
</body>
</html>"""
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f: 
        f.write(html_content)

try:
    setup_mantenimiento_ui()
except Exception as e:
    logging.error(f"Fallo en configuraciones iniciales: {e}")

# =================================================================
# VARIABLES Y BASE DE DATOS LOCAL
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
    except Exception as e:
        logging.error(f"Error guardando DB: {e}")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# =================================================================
# WATCHDOG FAILOVER: Auto-curación ante caída de HSI
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
            cmd = f"export DISPLAY=:0 && pkill chromium && sleep 2 && chromium --kiosk --no-first-run --autoplay-policy=no-user-gesture-required {maint_url} > /dev/null 2>&1 &"
            subprocess.Popen(cmd, shell=True)
            
        elif not current_status_down and hsi_is_down:
            hsi_is_down = False
            logging.info("HSI RECUPERADA: Restaurando turnero.")
            subprocess.Popen(f"export DISPLAY=:0 && nohup bash {sh_path} > /dev/null 2>&1 &", shell=True)

threading.Thread(target=watchdog_hsi, daemon=True).start()

# =================================================================
# CLÚSTER MESH: Elección de Líder y Notificaciones
# =================================================================
current_leader = None
offline_counters = {}
known_status = {}

def get_tg_timestamp():
    return time.strftime("%d/%m/%Y %H:%M:%S")

def send_telegram(token, chat, text):
    if not token or not chat: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat, "text": text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logging.error(f"Fallo Telegram: {e}")

def mesh_network_engine():
    global current_leader, offline_counters, known_status
    while True:
        time.sleep(10)
        db = load_db()
        pcs = db.get("pcs", [])
        if not pcs: continue

        my_ip = get_local_ip()
        alive_ips = []
        
        for pc in pcs:
            ip = pc.get("ip")
            if not ip: continue
            
            # Ping interno
            try:
                if ip == my_ip:
                    alive_ips.append(ip)
                    continue
                    
                req = urllib.request.Request(f"http://{ip}:5000/status")
                with urllib.request.urlopen(req, timeout=3) as response:
                    if response.status == 200:
                        alive_ips.append(ip)
                        offline_counters[ip] = 0
                        if known_status.get(ip) is False:
                            known_status[ip] = True
                            if current_leader == my_ip:
                                msg = f"✅ <b>SISTEMA RESTAURADO</b>\n🖥️ {pc.get('name', 'Desc')}\n🌐 <code>{ip}</code>\n🕒 {get_tg_timestamp()}"
                                send_telegram(db.get("tgToken"), db.get("tgChat"), msg)
            except:
                offline_counters[ip] = offline_counters.get(ip, 0) + 1
                if offline_counters[ip] >= 4 and known_status.get(ip, True) is True:
                    known_status[ip] = False
                    if current_leader == my_ip:
                        msg = f"🚨 <b>ALERTA CRÍTICA: OFFLINE</b>\n🖥️ {pc.get('name', 'Desc')}\n🌐 <code>{ip}</code>\n🕒 {get_tg_timestamp()}"
                        send_telegram(db.get("tgToken"), db.get("tgChat"), msg)

        # Regla determinista de elección de líder por IP más baja
        if alive_ips:
            try:
                sorted_ips = sorted(alive_ips, key=lambda x: [int(p) for p in x.split('.')])
                current_leader = sorted_ips[0]
            except:
                current_leader = my_ip
        else:
            current_leader = my_ip

threading.Thread(target=mesh_network_engine, daemon=True).start()

# =================================================================
# SERVIDOR FLASK API
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

@app.route('/sync', methods=['GET'])
def get_sync():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    db_data = load_db()
    return jsonify({"db": db_data, "current_leader": current_leader, "my_ip": get_local_ip()})

@app.route('/sync', methods=['POST'])
def post_sync():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    new_db = request.json
    save_db(new_db)
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
