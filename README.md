# 🏥 MIKY 7 - Mesh Command Center para Kioskos HSI

![Version](https://img.shields.io/badge/Versi%C3%B3n-7.0%20(V15)-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green.svg)
![License](https://img.shields.io/badge/Licencia-Apache%202.0-red)
![OS](https://img.shields.io/badge/OS-Linux%20Mint%20%7C%20Ubuntu-orange)

**Sistema MDM (Mobile Device Management) y Gestor de Pantallas Kiosko para la Historia de Salud Integrada (HSI).**
Diseñado específicamente para entornos hospitalarios críticos y salas de espera de alta concurrencia. Desarrollado y mantenido por la **División de Salud Digital del HIGA Gral. San Martín**, es una solución escalable para cualquier establecimiento del Ministerio de Salud (Marca Blanca).

---

## 🚀 Descripción General

MIKY 7 es una arquitectura completa para la administración descentralizada de pantallas y terminales llamadoras. 
Reemplaza los costosos sistemas de cartelería digital mediante una red **Mesh** (malla) local. Combina un agente residente en Python (`agent.py`) instalado en cada Mini-PC, con un **Panel de Control (NOC)** en HTML puro que se ejecuta sin necesidad de servidores externos ni bases de datos complejas.

## ✨ Características Principales

### 🧠 Inteligencia en el Borde (Edge Computing)
* **Watchdog de Failover:** Un guardián audita la URL del sistema HSI constantemente. Si detecta una caída de red o un error del servidor, inyecta automáticamente una **Placa de Mantenimiento Institucional** local. Al volver la señal, restaura el llamador de forma invisible.
* **Marca Blanca (White Label):** Permite configurar el nombre del Hospital y descargar su logotipo dinámicamente para las placas de espera, adaptándose a cualquier institución.

### 🌐 Clúster Mesh y Telemetría
* **Auto-Discovery:** Escaneo de red LAN para encontrar y registrar terminales nuevas en el tablero con un solo clic.
* **Líder de Clúster Autónomo:** Los equipos se comunican entre sí. Automáticamente eligen a un "Capitán" encargado de vigilar a los demás y enviar **Alertas por Telegram** si un equipo físico se apaga o pierde conexión. (Diseñado para no saturar el procesador del líder).
* **Telemetría en Tiempo Real:** Monitoreo de uso de CPU, Volumen actual de la TV, URL proyectada y estado de conexión asíncrono.

### ⚡ Control Remoto Absoluto
* **Gestor Multipantalla:** Capturas de pantalla en vivo, Control de Volumen, Forzar recarga (F5), Limpiar Caché de Chromium y Reinicio de Hardware a distancia.
* **Despliegue OTA (Over-The-Air):** Actualización masiva del código fuente de todas las terminales hospitalarias apuntando a la URL *Raw* de GitHub. No requiere ir máquina por máquina.
* **Wake-on-LAN (WoL) Inteligente:** Utiliza terminales encendidas como "puentes" para enviar paquetes mágicos y despertar a los equipos apagados.
* **Gestión Energética (CRON):** Programación de horarios para encender y apagar los monitores de forma automática según el horario del consultorio.
* **Terminal SSH Integrada:** Envío de comandos nativos de Linux directo desde el navegador hacia el equipo remoto.

---

## 🖥️ Requisitos de Hardware

El sistema es ligero, pero el motor de renderizado de Chromium en pantallas de alta resolución requiere una base sólida para funcionar de manera fluida 24/7.
* **Procesador:** Dual-Core o Quad-Core (Intel Celeron/i3 o equivalente).
* **Memoria RAM:** 4 GB mínimo (8 GB recomendados).
* **Almacenamiento:** 16 GB SSD (El sistema operativo base y MIKY ocupan muy poco espacio).
* **Sistema Operativo:** Linux Mint XFCE, Ubuntu Server o derivados (con entorno gráfico X11).

---

## 📦 Instalación (Zero-Touch Provisioning)

Para instalar una nueva terminal desde cero, conecta un teclado a la Mini-PC, abre la terminal Linux y ejecuta este único comando:

```bash
wget -qO instalar.sh "[https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/install.sh](https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/install.sh)" && bash instalar.sh
```

El instalador realizará automáticamente:

Solicitud de Contraseña VNC, Token Maestro y Datos del Hospital.

Instalación de todas las dependencias (Servidor SSH, Chromium, Python).

Configuración del Firewall UFW (Puertos 22, 5900, 5000).

Auto-generación e inyección del agente MIKY como demonio de sistema (systemd).

⚠️ IMPORTANTE SOBRE EL AUDIO: El instalador configura los motores de sonido (PulseAudio y espeak) de forma automática. Sin embargo, recuerda conectar el cable HDMI en la salida principal (Puerto 1) de la Mini-PC y asegurarte de que el volumen del televisor no esté silenciado.

💻 Uso del Panel de Control
El panel de administración no requiere ser instalado, es un archivo portable.

Abre el archivo miky7.html en cualquier navegador web.

Ingresa la IP de cualquier terminal encendida en la red y tu Clave Maestra.

Haz clic en el botón de Administración (⚙️).

Ve a la pestaña Inventario & Agendas y usa el botón Auto-Descubrir Red para armar tu tablero en segundos.

### 🔄 Cómo hacer una Actualización OTA (Remota)
Si publicas una nueva versión del código y necesitas actualizar todas las pantallas del hospital sin ir máquina por máquina:
1. En el Panel de Administración, ve a la pestaña **Despliegue OTA**.
2. Pega la URL *Raw* del archivo `agent.py` de tu repositorio. Por defecto es:
   `https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/agent.py`
3. Haz clic en **DEPLOY**. Todas las terminales encendidas descargarán el nuevo código y se reiniciarán automáticamente en menos de 10 segundos.

🛡️ Seguridad
Protección API: Todos los endpoints rechazan peticiones sin el Bearer Token.

Sin Bases de Datos Expuestas: El clúster intercambia la estructura en memoria. El Panel lee y cifra la información en el navegador del administrador.

Hardening de Interfaz: Modo Kiosko estricto (bloqueo de crash-bubbles, ocultamiento de cursor, bloqueo de traductor).

📩 Contacto y Soporte Institucional
Este proyecto es impulsado para modernizar la infraestructura tecnológica de los efectores de salud pública.
Para solicitar asistencia en la implementación en tu Hospital, resolver dudas técnicas o proponer mejoras, comunícate directamente con nuestro equipo:

División de Salud Digital Hospital Interzonal General de Agudos (HIGA) "Gral. San Martín" - La Plata.

📧 Email: clamas@ms.gba.gov.ar

📄 Licencia
Este proyecto está bajo la Licencia Apache 2.0.
Puedes usarlo y distribuirlo libremente manteniendo los avisos de atribución a la División de Salud Digital del HIGA San Martín.
