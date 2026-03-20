# 🔄 Sistema de Sincronización Automática

Este sistema sincroniza automáticamente los datos de Google Sheets con el dashboard HTML.

## 📋 Arquitectura Propuesta

### Opción 1: Google Sheets como Base de Datos (Recomendada) ✅

**Ventajas:**
- ✅ Ya lo tienes configurado
- ✅ Gratis y sin límites razonables
- ✅ Fácil de editar manualmente
- ✅ Accesible desde cualquier lugar
- ✅ Historial completo de cambios

**Cómo funciona:**
1. El bot de Telegram registra actividades → Google Sheets
2. Script Python sincroniza Sheets → Dashboard HTML
3. Se ejecuta automáticamente cada día (cron job)

### Opción 2: Firebase Firestore (Más robusto, pero requiere setup)

**Ventajas:**
- ✅ Tiempo real
- ✅ Más escalable
- ✅ Mejor para apps móviles

**Desventajas:**
- ❌ Requiere configuración adicional
- ❌ Puede tener costos con mucho uso

## 🚀 Implementación Recomendada: Google Sheets + Sincronización Automática

### Paso 1: Configurar el Script de Sincronización

El script `sync_dashboard.py` ya está creado. Necesitas:

```bash
cd "Ganaderia San Juan"
python sync_dashboard.py
```

### Paso 2: Automatizar la Sincronización

#### Opción A: Cron Job (Mac/Linux)

```bash
# Editar crontab
crontab -e

# Agregar esta línea para ejecutar cada día a las 6:00 AM
0 6 * * * cd "/Users/juanpmaldonado/Documents/Documentos - iMac/Python Projectos/Ganaderia San Juan" && /usr/bin/python3 sync_dashboard.py >> sync.log 2>&1
```

#### Opción B: GitHub Actions (Gratis, en la nube)

1. Sube tu proyecto a GitHub
2. Crea `.github/workflows/sync.yml`:

```yaml
name: Sincronizar Dashboard

on:
  schedule:
    - cron: '0 6 * * *'  # Cada día a las 6 AM
  workflow_dispatch:  # Permite ejecución manual

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Instalar dependencias
        run: |
          pip install gspread google-auth
      - name: Sincronizar
        env:
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
        run: |
          python sync_dashboard.py
      - name: Commit cambios
        run: |
          git config --global user.name "GitHub Actions"
          git config --global user.email "actions@github.com"
          git add dashboard-bufalera-san-juan.html
          git commit -m "Auto-sync: $(date)" || exit 0
          git push
```

#### Opción C: Servicio en la Nube (Render, Railway, etc.)

1. Sube el código a GitHub
2. Conecta con Render/Railway
3. Configura para ejecutar `sync_dashboard.py` cada día

### Paso 3: Modificar el Dashboard para Leer JSON

El dashboard puede leer el archivo `datos_sync.json` generado automáticamente:

```javascript
// Al inicio del dashboard, cargar datos desde JSON
let datosSync = null;
try {
    const response = await fetch('datos_sync.json');
    datosSync = await response.json();
    // Usar datosSync para actualizar ACTIVIDADES_FINCA, REGISTRO_ASISTENCIA, etc.
} catch (e) {
    console.log('Usando datos locales');
}
```

## 📊 Estructura de Datos en Google Sheets

Ya tienes estas hojas:
- ✅ **JORNALES**: Actividades de jornaleros
- ✅ **TRACTOR**: Trabajos con tractor
- ✅ **SANITARIO**: Actividades sanitarias
- ✅ **ASISTENCIA**: Registro de asistencia
- ✅ **ROTACION**: Movimientos de ganado
- ✅ **PAGOS**: Historial de pagos

## 🔄 Flujo de Actualización

```
1. Adriana/George reportan actividades → Bot Telegram
2. Bot guarda en Google Sheets
3. Script sync_dashboard.py lee Sheets (cada día a las 6 AM)
4. Genera datos_sync.json
5. Actualiza FECHA_ACTUAL en HTML
6. Dashboard se actualiza automáticamente
```

## 🎯 Próximos Pasos Recomendados

1. **Cortar plazo**: Usar cron job local para sincronizar diariamente
2. **Mediano plazo**: Migrar a GitHub Actions para sincronización en la nube
3. **Largo plazo**: Convertir dashboard a React que lea directamente de Sheets API

## 📝 Notas Importantes

- El script `sync_dashboard.py` lee de Google Sheets y genera JSON
- El dashboard HTML puede leer ese JSON o mantener datos locales como respaldo
- Google Sheets es tu "fuente de verdad" (single source of truth)
- Todos los cambios se guardan en Sheets con timestamp

## 🛠️ Troubleshooting

Si la sincronización falla:
1. Verifica credenciales de Google Sheets
2. Revisa permisos de la cuenta de servicio
3. Verifica que las hojas existan en Sheets
4. Revisa los logs: `sync.log`
