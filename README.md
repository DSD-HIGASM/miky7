# 🏥 MIKI Kiosko HSI - Command Center

**Sistema MDM (Mobile Device Management) y Gestor de Turneros para Historia de Salud Integrada.**
Diseñado específicamente para entornos hospitalarios críticos y salas de espera de alta concurrencia (HIGA Gral. San Martín).

---

## 🚀 Descripción General
MIKI HSI es una arquitectura completa de gestión de pantallas y terminales Kiosko. Combina un agente local en Python (Backend) instalado en cada Mini-PC con un panel de control NOC (Network Operations Center) en HTML/JS (Frontend). Permite el control remoto absoluto, monitoreo en tiempo real, auto-curación de errores y accesibilidad por voz sin depender de servicios externos de pago.

## ✨ Características Principales

### 🧠 Inteligencia en el Borde (Edge Computing)
* **Módulo Miki TTS (Text-to-Speech):** Extensión local de Chromium inyectada dinámicamente que lee la pantalla y envía los datos al hardware mediante `espeak`, logrando llamadas a viva voz en salas de espera y superando los bloqueos de "Autoplay" de los navegadores modernos.
* **Watchdog de Failover:** Un guardián en segundo plano (Python Thread) que audita la URL del turnero cada 15 segundos. Si detecta un Error HTTP (500, 502, 504) o pérdida de conectividad, fuerza el navegador a una placa de mantenimiento local (Modo Claro/Oscuro institucional). Al volver la HSI, restaura el servicio automáticamente.

### 🌐 Panel NOC Centralizado (V13.2)
* **Auto-Discovery:** Escaneo de red LAN (Barrido de subred /24) para encontrar y registrar terminales nuevas automáticamente.
* **Telemetría en Tiempo Real:** Monitoreo de uso de CPU, Volumen actual, URL proyectada y estado de conexión (Online/Offline) con pings asíncronos cada 5 segundos.
* **Control Remoto Activo:** Capturas de pantalla (Screenshots) en vivo, Control de Volumen, Forzar F5, Limpiar Caché, y Reinicio de Hardware.
* **Wake-on-LAN (WoL) Inteligente:** Utiliza terminales encendidas como "puentes" para enviar paquetes mágicos y despertar a los equipos caídos en la misma subred.
* **Gestión Energética (CRON):** Programación individual de horarios para encender y apagar las pantallas (DPMS) según el horario de atención del consultorio.

### 🔔 Alertas Críticas y Despliegue
* **Integración Telegram:** Notificaciones push inmediatas al detectar caídas prolongadas de terminales o recuperaciones de conexión.
* **Despliegue OTA (Over-The-Air):** Actualización masiva de todas las terminales con 1 clic desde el panel web consumiendo código fuente directo desde GitHub.

---

## 🛠️ Arquitectura Técnica
* **Sistema Operativo Base:** Linux Mint / Ubuntu (X11)
* **Motor Web:** Chromium-Browser (Modo Kiosk estricto, sin caché persistente de errores)
* **Agente Backend:** Python 3 + Flask + Gunicorn (Corriendo como demonio `systemd`)
* **Audio y Video:** PulseAudio (`pactl`), `espeak`, `scrot`, `xdotool`
* **Frontend:** HTML5 Single-Page Application, TailwindCSS, Phosphor Icons.

---

## ⚡ Instalación Rápida (Zero-Touch Provisioning)

Para instalar una nueva terminal desde cero (Mini-PC EXO o similar), conecta un teclado, abre la terminal y ejecuta este único comando:

```bash
wget -qO instalar.sh "[[https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/instalar.sh](https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/install.sh)]([https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/instalar.sh](https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/install.sh))" && bash instalar.sh
```

El instalador realizará los siguientes pasos automáticamente:

Solicitará (por única vez) la clave VNC y el Token de API deseado.

Instalará todas las dependencias (OpenSSH-Server, Chromium, Python-Flask, espeak, etc).

Configurará los puertos en el Firewall UFW (22, 5900, 5000).

Generará la placa de mantenimiento local.

Descargará dinámicamente la última versión del Agente (agent.py) desde el repo.

Configurará los servicios de inicio automático y reiniciará el equipo listo para producción.

💻 Uso del Panel de Control
Abre el archivo Dashboard_NOC.html en cualquier navegador web moderno.

Ingresa a la sección de Administración (ícono de engranaje).

En Red & Seguridad, coloca el Bearer Token que definiste durante la instalación.

En Inventario & Discovery, utiliza el botón "Auto-Descubrir Red" para encontrar tus terminales e incorporarlas al tablero.

Para actualizar el sistema, realizarlo desde "DESPLIEGUE OTA" con la siguiente URL:
```bash
https://raw.githubusercontent.com/DSD-HIGASM/miky7/refs/heads/main/agent.py
```

🛡️ Seguridad
Protección de API: Todos los endpoints de control en las terminales físicas (Puerto 5000) están protegidos mediante validación de Bearer Token.

Cifrado de Configuración: Las claves se guardan localmente en el localStorage del navegador que ejecuta el panel NOC, sin necesidad de bases de datos externas.
