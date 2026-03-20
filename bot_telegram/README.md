# 🐄 Bot de Telegram - Ganadería San Juan

Bot de Telegram para registrar actividades diarias de la finca y actualizar automáticamente el dashboard.

## 📋 Contenido

1. [Configuración Inicial](#configuración-inicial)
2. [Crear el Bot de Telegram](#paso-1-crear-el-bot-de-telegram)
3. [Configurar Google Sheets](#paso-2-configurar-google-sheets)
4. [Instalar y Ejecutar](#paso-3-instalar-y-ejecutar)
5. [Desplegar en la Nube (Gratuito)](#paso-4-desplegar-en-la-nube-gratuito)

---

## Configuración Inicial

### Requisitos

- Python 3.9 o superior
- Cuenta de Google (para Sheets)
- Cuenta de Telegram

---

## Paso 1: Crear el Bot de Telegram

1. Abre Telegram y busca `@BotFather`
2. Envía el comando `/newbot`
3. Sigue las instrucciones:
   - **Nombre del bot:** `Ganadería San Juan Bot`
   - **Username del bot:** `ganaderia_sanjuan_bot` (debe terminar en `bot`)
4. BotFather te dará un **TOKEN**. Guárdalo, se ve así:
   ```
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### Obtener Chat IDs

Para obtener los Chat IDs de ti y Adriana:

1. Busca `@userinfobot` en Telegram
2. Envíale `/start`
3. Te dará tu **Chat ID** (un número como `123456789`)
4. Pide a Adriana que haga lo mismo

---

## Paso 2: Configurar Google Sheets

### 2.1 Crear credenciales de Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto: `ganaderia-san-juan`
3. Habilita la API de Google Sheets:
   - Menú → APIs y Servicios → Biblioteca
   - Busca "Google Sheets API" → Habilitar
   - Busca "Google Drive API" → Habilitar
4. Crea una cuenta de servicio:
   - Menú → APIs y Servicios → Credenciales
   - Crear credenciales → Cuenta de servicio
   - Nombre: `bot-ganaderia`
   - Clic en la cuenta creada → Claves → Agregar clave → JSON
   - Se descargará un archivo `.json`
5. Renombra el archivo a `credentials.json` y ponlo en esta carpeta

### 2.2 Crear el Google Sheet

1. Ve a [Google Sheets](https://sheets.google.com)
2. Crea una nueva hoja: `Ganadería San Juan - Datos`
3. Copia el **ID de la hoja** de la URL:
   ```
   https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit
   ```
4. Comparte la hoja con el email de la cuenta de servicio:
   - El email está en `credentials.json` campo `client_email`
   - Se ve así: `bot-ganaderia@proyecto.iam.gserviceaccount.com`
   - Dar permisos de **Editor**

### 2.3 Crear archivo de configuración

Crea un archivo `.env` en esta carpeta con el siguiente contenido:

```env
# Token del bot de Telegram (de @BotFather)
TELEGRAM_BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Chat IDs
ADRIANA_CHAT_ID=123456789
OWNER_CHAT_ID=987654321

# ID del Google Sheet
GOOGLE_SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms

# Hora del recordatorio diario (formato 24h)
HORA_REPORTE=07:00
```

---

## Paso 3: Instalar y Ejecutar

### 3.1 Crear entorno virtual

```bash
cd "/Users/juanpmaldonado/Documents/Documentos - iMac/Python Projectos/Ganaderia San Juan/bot_telegram"

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate  # Mac/Linux
# o en Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3.2 Inicializar Google Sheets

```bash
# Esto creará las hojas necesarias en tu Google Sheet
python sheets_handler.py
```

Deberías ver:
```
Probando conexión con Google Sheets...
✓ Hoja 'JORNALES' creada
✓ Hoja 'TRACTOR' creada
✓ Hoja 'ROTACION' creada
✓ Hoja 'SANITARIO' creada
✓ Hoja 'ASISTENCIA' creada
✓ Hoja 'CONFIG' creada
✓ Inicialización completada
```

### 3.3 Ejecutar el bot

```bash
python bot.py
```

Deberías ver:
```
🚀 Iniciando Bot de Ganadería San Juan...
✅ Bot iniciado. Recordatorio diario a las 07:00
Presiona Ctrl+C para detener.
```

### 3.4 Probar el bot

1. Abre Telegram y busca tu bot por el username que creaste
2. Envía `/start`
3. Envía `/reporte` para probar el cuestionario

---

## Paso 4: Desplegar en la Nube (Gratuito)

Para que el bot funcione 24/7, necesitas desplegarlo en un servidor. Hay varias opciones gratuitas:

### Opción A: Railway (Recomendado)

1. Crea cuenta en [Railway](https://railway.app)
2. Nuevo proyecto → Deploy from GitHub
3. Sube tu código a GitHub
4. Configura las variables de entorno en Railway (las mismas del `.env`)

### Opción B: Render

1. Crea cuenta en [Render](https://render.com)
2. Nuevo → Web Service
3. Conecta tu repositorio de GitHub
4. Configura:
   - Build command: `pip install -r requirements.txt`
   - Start command: `python bot.py`
   - Variables de entorno

### Opción C: PythonAnywhere

1. Crea cuenta gratuita en [PythonAnywhere](https://www.pythonanywhere.com)
2. Sube los archivos
3. Configura una tarea programada

---

## 📱 Cómo usar el bot

### Comandos disponibles

| Comando | Descripción |
|---------|-------------|
| `/start` | Bienvenida y ayuda |
| `/reporte` | Iniciar reporte diario |
| `/estado` | Ver ubicación actual del ganado |
| `/ayuda` | Ver comandos disponibles |
| `/cancelar` | Cancelar reporte en curso |

### Flujo del reporte diario

El bot preguntará en orden:

1. **👷 Jornales** - Cantidad, tipo (Corral, Casa, Cercas, etc.), y lote
2. **🚜 Tractor** - Si trabajó, en qué lote y cuántas hectáreas
3. **🐄 Rotación** - Si el ganado cambió de lote
4. **💉 Sanitario** - Vacunas, purgas, vitaminas, marcaciones
5. **📋 Asistencia** - Si George y Adriana trabajaron

Al final, muestra un resumen para confirmar antes de guardar.

---

## 🔧 Estructura de archivos

```
bot_telegram/
├── bot.py              # Bot principal de Telegram
├── config.py           # Configuración y constantes
├── sheets_handler.py   # Manejo de Google Sheets
├── credentials.json    # Credenciales de Google (NO subir a Git)
├── .env                # Variables de entorno (NO subir a Git)
├── requirements.txt    # Dependencias Python
└── README.md           # Este archivo
```

---

## 🔒 Seguridad

**NUNCA compartas ni subas a Git:**
- `credentials.json`
- `.env`
- El token del bot

Agrega esto a tu `.gitignore`:
```
credentials.json
.env
venv/
__pycache__/
```

---

## ❓ Solución de problemas

### El bot no responde
- Verifica que el token sea correcto
- Verifica que el bot esté corriendo (`python bot.py`)

### Error de Google Sheets
- Verifica que `credentials.json` esté en la carpeta
- Verifica que el Sheet esté compartido con la cuenta de servicio
- Verifica que el ID del Sheet sea correcto

### No llegan los recordatorios
- Verifica que el Chat ID sea correcto
- El bot debe estar corriendo a la hora configurada

---

## 📞 Soporte

Si tienes problemas, revisa:
1. Los logs en la terminal donde corre el bot
2. Que todas las variables de entorno estén configuradas
3. Que las credenciales de Google sean válidas
