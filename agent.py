import os, subprocess, psutil, base64, re, logging, socket, uuid
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import BACKEND_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =================================================================
# INYECCIÓN AUTOMÁTICA OTA: MIKI TTS (Text-To-Speech) V1.2
# =================================================================
def setup_tts_extension():
    home = os.path.expanduser("~")
    tts_dir = os.path.join(home, "control_remoto", "miki_tts")
    
    os.makedirs(tts_dir, exist_ok=True)
    
    manifest = '{"manifest_version": 3, "name": "Miki HSI TTS", "version": "1.2", "content_scripts": [{"matches": ["<all_urls>"], "js": ["content.js"]}]}'
    
    content_js = """let ultimoLlamado = "";
    const hablar = (texto) => {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            let msg = new SpeechSynthesisUtterance(texto);
            msg.lang = 'es-AR';
            msg.rate = 0.85;
            window.speechSynthesis.speak(msg);
        }
    };

    const observar = new MutationObserver(() => {
        // 1. Encontrar el texto "Último llamado" para anclar la búsqueda
        let parrafos = Array.from(document.querySelectorAll('p'));
        let nodoAlerta = parrafos.find(p => p.innerText.trim().toLowerCase() === 'último llamado');

        let bloqueTurno = document; // Fallback al documento completo
        if (nodoAlerta && nodoAlerta.parentElement && nodoAlerta.parentElement.parentElement) {
            // 2. Aislamos el div contenedor exacto de la tarjeta (css-egoftb)
            bloqueTurno = nodoAlerta.parentElement.parentElement;
        }

        // 3. Extraer el H1 de paciente SOLO dentro de esa tarjeta nueva
        let nodoPaciente = bloqueTurno.querySelector('h1');

        if (nodoPaciente) {
            let paciente = nodoPaciente.innerText.trim();

            // 4. Buscar el destino en la misma tarjeta
            let parrafosBloque = Array.from(bloqueTurno.querySelectorAll('p'));
            let nodoDestino = parrafosBloque.find(p => 
                p.innerText.toLowerCase().includes('consultorio') || 
                p.innerText.toLowerCase().includes('triage') || 
                p.innerText.toLowerCase().includes('box')
            );
            
            let destino = nodoDestino ? nodoDestino.innerText.trim() : "su lugar asignado";
            let idLlamado = paciente + destino;
            
            // 5. Filtrar marcadores temporales o duplicados
            if (paciente !== "" && paciente !== "PACIENTE TEMPORAL" && idLlamado !== ultimoLlamado) {
                ultimoLlamado = idLlamado;
                // Reemplazamos guiones por espacios para que la voz fluya mejor
                let destinoHablado = destino.replace('-', ' ');
                
                setTimeout(() => hablar(`Atención. Paciente ${paciente}, por favor dirigirse a ${destinoHablado}`), 1500);
            }
        }
    });

    observar.observe(document.body, { childList: true, subtree: true });"""
    
    with open(os.path.join(tts_dir, "manifest.json"), "w") as f: f.write(manifest)
    with open(os.path.join(tts_dir, "content.js"), "w") as f: f.write(content_js)
        
    sh_path = os.path.join(home, "iniciar_kiosko.sh")
    if os.path.exists(sh_path):
        with open(sh_path, "r") as f: content = f.read()
        if "--load-extension" not in content:
            content = content.replace("--kiosk", f"--kiosk --load-extension={tts_dir}")
            with open(sh_path, "w") as f: f.write(content)
            # Fuerza el reinicio de Chromium solo si la extensión no estaba configurada antes
            subprocess.Popen("export DISPLAY=:0 && pkill chromium && sleep 2 && nohup bash " + sh_path + " > /dev/null 2>&1 &", shell=True)

try:
    setup_tts_extension()
except Exception as e:
    logging.error(f"Fallo en TTS setup: {e}")
# =================================================================

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

STARTUP_URL_FILE = os.path.expanduser("~/kiosko_startup.url")
CACHE_DIR = os.path.expanduser("~/.config/chromium-kiosko-hsi/Default/Cache/*")

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
    except Exception as e:
        logging.error(f"Error WoL: {e}")
        return False

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
            return jsonify({"status": "ok", "msg": f"WoL enviado a {target_mac}"})
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
