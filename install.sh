#!/bin/bash

# =====================================================================
#  MIKY KIOSKO HSI - INSTALADOR MAESTRO (Zero-Touch + SSH + URL Raw)
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

# 1. CAPTURA SEGURA DE CREDENCIALES E IDENTIDAD
echo -e "🔒 ${BLUE}Configuración de Seguridad de la Red LAN${NC}"
read -s -p "➤ Ingrese nueva clave para Acceso Remoto VNC: " VNC_PASS
echo ""
read -s -p "➤ Ingrese Token/Clave para el Panel de Comando Web: " BACKEND_PASS
echo ""
echo " "

echo -e "🏥 ${BLUE}Configuración de la Institución (Marca Blanca)${NC}"
read -p "➤ Ingrese el Nombre del Establecimiento [Ej: HIGA San Martín]: " HOSP_NAME
HOSP_NAME=${HOSP_NAME:-"Establecimiento de Salud"}

read -p "➤ Ingrese la URL del Logo del Establecimiento (JPG/PNG): " LOGO_URL
LOGO_URL=${LOGO_URL:-"https://hospitalsanmartin.ar/wp-content/uploads/2024/02/cropped-WhatsApp-Image-2024-01-29-at-10.39.37.jpeg"}
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
HOSPITAL_NAME = "$HOSP_NAME"
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
    TARGET_URL=""
fi
pkill chromium
pkill chrome
chromium --kiosk --no-first-run --password-store=basic --disable-infobars --disable-session-crashed-bubble --disable-features=Translate --user-data-dir=$HOME/.config/chromium-kiosko-hsi --autoplay-policy=no-user-gesture-required "$TARGET_URL" &
sleep 10
xdotool mousemove 500 500 click 1
xdotool mousemove 0 0
EOF
chmod +x "$USER_HOME/iniciar_kiosko.sh"

# 5.4 DESCARGA DE LOGOS INSTITUCIONALES
echo -e "📥 ${BLUE}Descargando logos oficiales para caché local...${NC}"
LOGO_PATH="$INSTALL_DIR/logo_hospital.jpg"
wget -4 -qO "$LOGO_PATH" "$LOGO_URL"
(crontab -l 2>/dev/null | grep -v "logo_hospital"; echo "0 3 * * * wget -4 -qO $LOGO_PATH \"$LOGO_URL\"") | crontab -

MINISTERIO_URL="https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/ministerio.svg"
wget -4 -qO "$INSTALL_DIR/ministerio.svg" "$MINISTERIO_URL"

# 6. DESCARGA DINÁMICA DEL AGENTE PYTHON DESDE GITHUB
echo -e "🐍 ${BLUE}Descargando última versión del Agente Controlador...${NC}"
AGENT_URL="https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/agent.py"
wget -qO "$INSTALL_DIR/agent.py" "$AGENT_URL"
chmod +x "$INSTALL_DIR/agent.py"

# 7. REGISTRO EN SYSTEMD
echo -e "⚙️  ${BLUE}Inyectando Agente en Systemd Daemon...${NC}"
cat << EOF | sudo tee /etc/systemd/system/miki_agent.service > /dev/null
[Unit]
Description=Miky Kiosk Backend Agent (Gunicorn)
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
Name=Miky Kiosk
Comment=Frontend Web
EOF

cat << EOF > "$USER_HOME/.config/autostart/miki_vnc.desktop"
[Desktop Entry]
Type=Application
Exec=x11vnc -display :0 -forever -usepw -shared -rfbport 5900 -bg
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Miky VNC
Comment=Remote Desktop
EOF

# 10. FIREWALL
echo -e "🛡️  ${BLUE}Aplicando políticas de red (UFW)...${NC}"
sudo ufw allow 5000/tcp comment 'Miky Web Agent'
sudo ufw allow 5900/tcp comment 'Miky VNC'
sudo ufw allow 22/tcp comment 'Miky SSH'

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN} ✅ INSTALACIÓN ZERO-TOUCH FINALIZADA CON ÉXITO ✅ ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo "El Agente ya está corriendo con SSH y Mantenimiento Institucional activos."
echo "Por favor, reinicia la máquina para aplicar todos los cambios de video."
echo " "
