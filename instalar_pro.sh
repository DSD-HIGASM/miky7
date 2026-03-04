#!/bin/bash

# =====================================================================
#  MIKI KIOSKO HSI - INSTALADOR ENTERPRISE V8
#  Arquitectura: Systemd + Gunicorn + Zero-Trust + Offline + OTA
# =====================================================================

# Colores para UI de consola
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${GREEN} 🏥 INICIANDO DESPLIEGUE SEGURO: TERMINAL HSI ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo " "

# 1. CAPTURA SEGURA DE CREDENCIALES
echo -e "🔒 ${BLUE}Configuración de Seguridad de la Red LAN${NC}"
read -s -p "➤ Ingrese nueva clave para Acceso Remoto VNC: " VNC_PASS
echo ""
read -s -p "➤ Ingrese Token/Clave para el Panel de Comando Web: " BACKEND_PASS
echo ""
echo " "

USER_HOME=$HOME
INSTALL_DIR="$USER_HOME/control_remoto"

# 2. ACTUALIZACIÓN E INSTALACIÓN DE PAQUETES DE PRODUCCIÓN
echo -e "📦 ${BLUE}Instalando dependencias de grado de producción...${NC}"
sudo apt-get update
# Se usa 'chromium' nativo para evitar conflictos con snapd
sudo apt-get install -y python3-flask python3-flask-cors python3-psutil xdotool unclutter scrot alsa-utils x11vnc net-tools ufw gunicorn wget chromium

# 3. ESTRUCTURA DE CARPETAS Y PERMISOS ESTRICTOS
mkdir -p "$INSTALL_DIR"
mkdir -p "$USER_HOME/.config/autostart"
mkdir -p "$USER_HOME/.vnc"

# Crear archivo de configuración protegido para Python
cat << EOF > "$INSTALL_DIR/config.py"
BACKEND_TOKEN = "$BACKEND_PASS"
EOF
chmod 600 "$INSTALL_DIR/config.py"

# 4. CONFIGURAR VNC SEGURO
echo -e "🖥️ ${BLUE}Encriptando credenciales VNC...${NC}"
x11vnc -storepasswd "$VNC_PASS" "$USER_HOME/.vnc/passwd"

# 5. MOTOR DE NAVEGADOR (CHROMIUM HARDENED)
echo -e "📜 ${BLUE}Generando motor de kiosko...${NC}"
cat << 'EOF' > "$USER_HOME/iniciar_kiosko.sh"
#!/bin/bash
export DISPLAY=:0

xset s noblank
xset s off
xset -dpms
unclutter -idle 0.5 -root &

STARTUP_FILE="$HOME/kiosko_startup.url"
if [ -f "$STARTUP_FILE" ]; then
    TARGET_URL=$(cat "$STARTUP_FILE")
else
    TARGET_URL="https://google.com"
fi

pkill chromium
pkill chrome

chromium \
  --kiosk \
  --no-first-run \
  --password-store=basic \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=Translate \
  --user-data-dir=$HOME/.config/chromium-kiosko-hsi \
  --autoplay-policy=no-user-gesture-required \
  "$TARGET_URL" &

sleep 10
xdotool mousemove 500 500 click 1
xdotool mousemove 0 0
EOF
chmod +x "$USER_HOME/iniciar_kiosko.sh"

# 5.4 CACHÉ LOCAL DEL LOGO INSTITUCIONAL
echo -e "📥 ${BLUE}Descargando logo oficial para caché local...${NC}"
LOGO_URL="https://hospitalsanmartin.ar/wp-content/uploads/2024/02/cropped-WhatsApp-Image-2024-01-29-at-10.39.37.jpeg"
LOGO_PATH="$INSTALL_DIR/logo_higa.jpg"

wget -qO "$LOGO_PATH" "$LOGO_URL"

echo -e "⏰ ${BLUE}Programando sincronización diaria del logo...${NC}"
(crontab -l 2>/dev/null | grep -v "logo_higa"; echo "0 3 * * * wget -qO $LOGO_PATH $LOGO_URL") | crontab -

# 5.5 CREAR PANTALLA DE MANTENIMIENTO LOCAL (OFFLINE)
echo -e "🎨 ${BLUE}Generando placa de mantenimiento institucional offline...${NC}"
cat << 'EOF' > "$INSTALL_DIR/mantenimiento.html"
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema en Mantenimiento</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Encode+Sans:wght@600;800&family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --pba-pink: #e81f76;
            --pba-blue: #417099;
            --pba-cyan: #00aec3;
        }
        body {
            background-color: #f8fafc;
            color: #334155;
            font-family: 'Roboto', sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            text-align: center;
            overflow: hidden;
            position: relative;
        }
        .pba-gradient-bar {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 24px;
            background: linear-gradient(90deg, var(--pba-pink) 0%, var(--pba-blue) 50%, var(--pba-cyan) 100%);
        }
        .logos-container {
            display: flex;
            align-items: center;
            gap: 40px;
            margin-bottom: 50px;
        }
        .logo-higa {
            height: 140px;
            border-radius: 16px;
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
        }
        .icon-alert {
            font-size: 6rem;
        }
        h1 {
            font-family: 'Encode Sans', sans-serif;
            font-weight: 800;
            font-size: 6rem;
            color: var(--pba-blue);
            margin: 0 0 25px 0;
            line-height: 1.1;
            text-transform: uppercase;
        }
        p.instruccion {
            font-size: 3.5rem;
            font-weight: 700;
            color: #0f172a;
            max-width: 85%;
            margin: 0;
            line-height: 1.3;
        }
        .footer {
            position: absolute;
            bottom: 40px;
            font-family: 'Encode Sans', sans-serif;
            font-weight: 600;
            font-size: 1.5rem;
            color: #64748b;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .footer strong {
            color: var(--pba-blue);
        }
    </style>
</head>
<body>
    <div class="pba-gradient-bar"></div>
    <div class="logos-container">
        <div class="icon-alert">🛠️</div>
        <img src="logo_higa.jpg" alt="HIGA Gral San Martín" class="logo-higa" onerror="this.style.display='none'">
    </div>
    <h1>Sistema en mantenimiento</h1>
    <p class="instruccion">Esté atento al llamado e indicaciones<br>del personal para la atención</p>
    <div class="footer">
        <span>Módulo de Llamado a Pacientes</span>
        <strong>HIGA Gral. San Martín | Ministerio de Salud de la Provincia de Buenos Aires</strong>
    </div>
</body>
</html>
EOF

# 6. AGENTE PYTHON (MODULAR Y LOGGABLE)
echo -e "🐍 ${BLUE}Compilando Agente Controlador...${NC}"
cat << 'EOF' > "$INSTALL_DIR/agent.py"
import os, subprocess, psutil, base64, re, logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import BACKEND_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        subprocess.run(f"export DISPLAY=:0 && {cmd}", shell=True, check=True)
        return True
    except Exception as e:
        logging.error(f"Error ejecutando {cmd}: {e}")
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
        output = subprocess.check_output("amixer sget Master", shell=True).decode()
        match = re.search(r"\[(\d+)%\]", output)
        if match: vol = match.group(1)
    except: vol = "Err"

    return jsonify({"status": "online", "cpu": cpu, "url": url, "vol": vol})

@app.route('/set_startup', methods=['POST'])
def set_startup():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    url = request.json.get('url')
    logging.info(f"Comando recibido: set_startup -> {url}")
    with open(STARTUP_URL_FILE, 'w') as f: f.write(url)
    os.system(f"nohup bash {os.path.expanduser('~/iniciar_kiosko.sh')} > /dev/null 2>&1 &")
    return jsonify({"status": "ok", "url": url})

@app.route('/control', methods=['POST'])
def control():
    if not verificar_auth(request): return jsonify({"error": "Auth"}), 401
    acc = request.json.get('accion')
    logging.info(f"Comando recibido: control -> {acc}")
    
    if acc == 'refresh': 
        run_cmd("xdotool search --onlyvisible --class 'chromium' windowactivate key F5")
    elif acc == 'clear_cache':
        run_cmd(f"rm -rf {CACHE_DIR}")
        run_cmd("xdotool search --onlyvisible --class 'chromium' windowactivate key F5")
    elif acc == 'reboot': 
        os.system("sudo reboot")
    elif acc == 'update_agent':
        repo_url = request.json.get('url')
        if repo_url:
            logging.info(f"Iniciando actualización OTA desde: {repo_url}")
            install_path = os.path.dirname(os.path.abspath(__file__))
            cmd = f"sleep 2 && wget -qO /tmp/new_agent.py {repo_url} && mv /tmp/new_agent.py {install_path}/agent.py && sudo systemctl restart miki_agent.service"
            subprocess.Popen(cmd, shell=True)
            return jsonify({"status": "ok", "msg": "Actualización OTA iniciada"})
        return jsonify({"error": "Falta URL"}), 400
    elif acc == 'vol_up': 
        run_cmd("amixer sset Master 5%+")
    elif acc == 'vol_down': 
        run_cmd("amixer sset Master 5%-")
        
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
EOF
chmod +x "$INSTALL_DIR/agent.py"

# 7. REGISTRO EN SYSTEMD (Inmortalidad del servicio)
echo -e "⚙️  ${BLUE}Inyectando Agente en Systemd Daemon...${NC}"
cat << EOF | sudo tee /etc/systemd/system/miki_agent.service > /dev/null
[Unit]
Description=Miki Kiosk Backend Agent (Gunicorn)
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/gunicorn --workers 1 --threads 2 --bind 0.0.0.0:5000 agent:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable miki_agent.service
sudo systemctl restart miki_agent.service

# 8. PERMISOS SUDO SIN PASSWORD PARA REBOOT Y REINICIO DE SERVICIO
echo "$USER ALL=(ALL) NOPASSWD: /usr/sbin/reboot, /bin/systemctl restart miki_agent.service" | sudo tee /etc/sudoers.d/miki_nopass > /dev/null

# 9. AUTOARRANQUE DE FRONTEND (GUI)
echo -e "🚀 ${BLUE}Configurando sesión gráfica...${NC}"
cat << EOF > "$USER_HOME/.config/autostart/miki_kiosk.desktop"
[Desktop Entry]
Type=Application
Exec=/bin/bash $USER_HOME/iniciar_kiosko.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Miki Kiosk
Comment=Frontend Web
EOF

cat << EOF > "$USER_HOME/.config/autostart/miki_vnc.desktop"
[Desktop Entry]
Type=Application
Exec=x11vnc -display :0 -forever -usepw -shared -rfbport 5900 -bg
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Miki VNC
Comment=Remote Desktop
EOF

# 10. REGLAS DE FIREWALL
echo -e "🛡️  ${BLUE}Aplicando políticas de red (UFW)...${NC}"
sudo ufw allow 5000/tcp comment 'Miki Web Agent'
sudo ufw allow 5900/tcp comment 'Miki VNC'

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN} ✅ INSTALACIÓN ENTERPRISE FINALIZADA CON ÉXITO ✅ ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo "El Agente ya está corriendo de forma nativa en Systemd."
echo "Para aplicar los cambios visuales, reinicie la terminal."
echo " "
