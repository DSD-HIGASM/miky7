#!/bin/bash

# =====================================================================
#  MIKI KIOSKO HSI - INSTALADOR MAESTRO V15 (Zero-Touch + SSH + URL Raw)
#  Arquitectura: Limpieza total + Systemd + Gunicorn + OTA + Failover
# =====================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${GREEN} 🚀 INICIANDO INSTALACIÓN MAESTRA HSI KIOSK ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo " "

USER_HOME=$HOME
INSTALL_DIR="$USER_HOME/control_remoto"

# 0. LIMPIEZA DE INSTALACIÓN ANTERIOR
echo -e "🗑️ ${BLUE}Borrando servicios y archivos previos...${NC}"
sudo systemctl stop miki_agent.service 2>/dev/null
sudo systemctl disable miki_agent.service 2>/dev/null
sudo rm -f /etc/systemd/system/miki_agent.service
sudo systemctl daemon-reload

rm -rf "$INSTALL_DIR"
rm -f "$USER_HOME/.config/autostart/miki_kiosk.desktop"
rm -f "$USER_HOME/.config/autostart/miki_vnc.desktop"
rm -f "$USER_HOME/iniciar_kiosko.sh"
sudo rm -f /etc/sudoers.d/miki_nopass

# 1. CAPTURA SEGURA DE CREDENCIALES
echo -e "🔒 ${BLUE}Configuración de Seguridad de la Red LAN${NC}"
read -s -p "➤ Ingrese nueva clave para Acceso Remoto VNC: " VNC_PASS
echo ""
read -s -p "➤ Ingrese Token/Clave para el Panel de Comando Web: " BACKEND_PASS
echo ""
echo " "

# 2. ACTUALIZACIÓN E INSTALACIÓN DE PAQUETES (INCLUYE SSH)
echo -e "📦 ${BLUE}Instalando dependencias de grado de producción...${NC}"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-flask python3-flask-cors python3-psutil xdotool unclutter scrot alsa-utils x11vnc net-tools ufw gunicorn wget chromium openssh-server espeak

# Habilitar SSH desde el arranque
sudo systemctl enable ssh
sudo systemctl start ssh

# 3. ESTRUCTURA DE CARPETAS Y PERMISOS ESTRICTOS
mkdir -p "$INSTALL_DIR"
mkdir -p "$USER_HOME/.config/autostart"
mkdir -p "$USER_HOME/.vnc"

cat << EOF > "$INSTALL_DIR/config.py"
BACKEND_TOKEN = "$BACKEND_PASS"
EOF
chmod 600 "$INSTALL_DIR/config.py"

# 4. CONFIGURAR VNC SEGURO
echo -e "🖥️ ${BLUE}Encriptando credenciales VNC...${NC}"
x11vnc -storepasswd "$VNC_PASS" "$USER_HOME/.vnc/passwd"

# 5. MOTOR DE NAVEGADOR
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
    TARGET_URL="https://llamador-shc.ms.gba.gov.ar"
fi
pkill chromium
pkill chrome
chromium --kiosk --no-first-run --password-store=basic --disable-infobars --disable-session-crashed-bubble --disable-features=Translate --user-data-dir=$HOME/.config/chromium-kiosko-hsi --autoplay-policy=no-user-gesture-required "$TARGET_URL" &
sleep 10
xdotool mousemove 500 500 click 1
xdotool mousemove 0 0
EOF
chmod +x "$USER_HOME/iniciar_kiosko.sh"

# 5.4 CACHÉ LOCAL DEL LOGO
echo -e "📥 ${BLUE}Descargando logo oficial para caché local...${NC}"
LOGO_URL="https://hospitalsanmartin.ar/wp-content/uploads/2024/02/cropped-WhatsApp-Image-2024-01-29-at-10.39.37.jpeg"
LOGO_PATH="$INSTALL_DIR/logo_higa.jpg"
wget -4 -qO "$LOGO_PATH" "$LOGO_URL"
(crontab -l 2>/dev/null | grep -v "logo_higa"; echo "0 3 * * * wget -4 -qO $LOGO_PATH $LOGO_URL") | crontab -

# 5.5 CREAR PANTALLA DE MANTENIMIENTO (MODO CLARO)
echo -e "🎨 ${BLUE}Generando placa de mantenimiento offline pro (Light Mode)...${NC}"
cat << 'EOF' > "$INSTALL_DIR/mantenimiento.html"
<!DOCTYPE html>
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
</html>
EOF

# 6. DESCARGA DINÁMICA DEL AGENTE PYTHON DESDE GITHUB
echo -e "🐍 ${BLUE}Descargando última versión del Agente Controlador...${NC}"
AGENT_URL="https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/agent.py"
wget -qO "$INSTALL_DIR/agent.py" "$AGENT_URL"
chmod +x "$INSTALL_DIR/agent.py"

# 7. REGISTRO EN SYSTEMD
echo -e "⚙️  ${BLUE}Inyectando Agente en Systemd Daemon...${NC}"
cat << EOF | sudo tee /etc/systemd/system/miki_agent.service > /dev/null
[Unit]
Description=Miki Kiosk Backend Agent (Gunicorn)
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/gunicorn --workers 1 --threads 3 --bind 0.0.0.0:5000 agent:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable miki_agent.service
sudo systemctl restart miki_agent.service

# 8. PERMISOS SUDO
echo "$USER ALL=(ALL) NOPASSWD: /usr/sbin/reboot, /bin/systemctl restart miki_agent.service" | sudo tee /etc/sudoers.d/miki_nopass > /dev/null

# 9. AUTOARRANQUE DE FRONTEND
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

# 10. FIREWALL
echo -e "🛡️  ${BLUE}Aplicando políticas de red (UFW)...${NC}"
sudo ufw allow 5000/tcp comment 'Miki Web Agent'
sudo ufw allow 5900/tcp comment 'Miki VNC'
sudo ufw allow 22/tcp comment 'Miki SSH'

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN} ✅ INSTALACIÓN ZERO-TOUCH FINALIZADA CON ÉXITO ✅ ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo "El Agente ya está corriendo con SSH y Mantenimiento Light Mode activos."
echo "Por favor, reinicia la máquina para aplicar todos los cambios de video."
echo " "
