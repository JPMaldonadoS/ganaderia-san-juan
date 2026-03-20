# 📋 Plan de Trabajo - Sistema de Gestión Ganadera

## 🎯 Objetivo
Crear un sistema completo que se actualice automáticamente, conectando:
- **Dashboard HTML** (interfaz visual)
- **Google Sheets** (base de datos)
- **Bot de Telegram** (entrada de datos desde el campo)

---

## 📁 Estructura que Vamos a Crear

### 1. **Google Sheets** (Base de Datos Principal)
**Cuenta:** maldonadoserranoyasociados@gmail.com

**Hojas que crearemos (TODO NUEVO, desde cero):**
- `ACTIVIDADES_FINCA` - Registro diario de actividades
- `ACTIVIDADES_SANITARIAS` - Tratamientos y curaciones
- `ASISTENCIA` - Control de asistencia de empleados
- `GANADO` - Inventario y movimientos de ganado
- `PAGOS` - Historial de pagos y nómina
- `SEGURIDAD_SOCIAL` - Pagos de seguridad social
- `FACTURACION` - Ventas y facturación

### 2. **Bot de Telegram** (Entrada de Datos)
- Los trabajadores reportan actividades desde el campo
- El bot guarda todo en Google Sheets automáticamente
- No necesita intervención manual

### 3. **Dashboard HTML** (Visualización)
- Lee datos de Google Sheets automáticamente
- Se actualiza solo cuando hay cambios
- Muestra toda la información de forma visual

---

## 🚀 Pasos de Implementación

### **FASE 1: Configuración de Google Sheets** (30 min)
1. Crear nueva hoja de cálculo en Google Drive
2. Crear las hojas (tabs) necesarias con estructura
3. Configurar permisos y API
4. Obtener credenciales de acceso

### **FASE 2: Migración de Datos Actuales** (1 hora)
1. Exportar datos actuales del dashboard HTML
2. Importar a Google Sheets
3. Verificar que todo esté correcto

### **FASE 3: Configuración del Bot de Telegram** (1 hora)
1. Crear bot en Telegram (con @BotFather)
2. Configurar credenciales
3. Conectar con Google Sheets
4. Probar reportes desde el campo

### **FASE 4: Actualización del Dashboard** (2 horas)
1. Modificar HTML para leer de Google Sheets
2. Implementar actualización automática
3. Probar sincronización

### **FASE 5: Automatización** (30 min)
1. Configurar actualizaciones automáticas
2. Probar flujo completo
3. Documentar uso

---

## 📝 Información que Necesitamos

### Para Google Sheets:
- ✅ Cuenta: maldonadoserranoyasociados@gmail.com
- ⏳ Crear nueva hoja (haremos esto juntos)
- ⏳ Configurar API (haremos esto juntos)

### Para Telegram Bot:
- ⏳ Token del bot (lo crearemos con @BotFather)
- ⏳ Usuarios autorizados (tú, Adriana, George, etc.)

### Para el Dashboard:
- ✅ Ya existe: `dashboard-bufalera-san-juan.html`
- ⏳ Modificar para leer de Sheets

---

## 🔄 Flujo de Trabajo Final

```
┌─────────────────┐
│  Trabajador     │
│  (en el campo)  │
└────────┬────────┘
         │
         │ Envía mensaje
         ▼
┌─────────────────┐
│  Bot Telegram   │
│  (recibe datos) │
└────────┬────────┘
         │
         │ Guarda automáticamente
         ▼
┌─────────────────┐
│  Google Sheets  │
│  (Base de datos)│
└────────┬────────┘
         │
         │ Lee automáticamente
         ▼
┌─────────────────┐
│  Dashboard HTML │
│  (Visualización)│
└─────────────────┘
```

---

## ⚠️ Importante: Empezar de Cero

- ✅ **NO** usaremos información antigua (10 años)
- ✅ **SÍ** crearemos todo nuevo y limpio
- ✅ La información antigua queda en Google Drive (archivada)
- ✅ El nuevo sistema será solo para 2026 en adelante

---

## 📅 Cuándo Empezamos

Cuando estés listo, comenzamos con la **FASE 1** y vamos paso a paso.

**Tiempo estimado total:** 5-6 horas de trabajo conjunto

---

## ❓ Preguntas para Cuando Empecemos

1. ¿Qué usuarios de Telegram necesitan acceso al bot? (Adriana, George, otros)
2. ¿Quieres mantener el dashboard actual mientras configuramos el nuevo?
3. ¿Prefieres que el bot funcione 24/7 o solo en horarios específicos?

---

**Última actualización:** 21 de Enero 2026
**Estado:** ⏳ Esperando para comenzar
