# ⚙️ Guía de Configuración Inicial

## 📋 Checklist Pre-Trabajo

Antes de comenzar, asegúrate de tener:

- [ ] Acceso a la cuenta de Google: maldonadoserranoyasociados@gmail.com
- [ ] Telegram instalado en tu teléfono
- [ ] El archivo `dashboard-bufalera-san-juan.html` disponible
- [ ] Tiempo disponible (5-6 horas para todo el proceso)

---

## 🔧 Configuración Paso a Paso

### **PASO 1: Crear Google Sheets**

1. Ve a [Google Sheets](https://sheets.google.com)
2. Inicia sesión con: maldonadoserranoyasociados@gmail.com
3. Crea una nueva hoja de cálculo
4. Nómbrala: **"Ganadería San Juan - Sistema 2026"**
5. **¡IMPORTANTE!** Esta será nuestra base de datos nueva, desde cero

### **PASO 2: Habilitar Google Sheets API**

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Crea un nuevo proyecto (o usa uno existente)
3. Habilita "Google Sheets API"
4. Crea credenciales (Service Account)
5. Descarga el archivo JSON de credenciales
6. Comparte la hoja de cálculo con el email de la Service Account

### **PASO 3: Crear Bot de Telegram**

1. Abre Telegram
2. Busca: **@BotFather**
3. Envía: `/newbot`
4. Sigue las instrucciones para crear tu bot
5. Guarda el **Token** que te dé (lo necesitaremos)

### **PASO 4: Estructura de Hojas en Google Sheets**

Cuando creemos las hojas, tendrán esta estructura:

#### **ACTIVIDADES_FINCA**
```
Fecha | Tipo | Lote | Cantidad | Responsable | Descripción | Notas
```

#### **ACTIVIDADES_SANITARIAS**
```
Fecha | Tipo | Lote | Responsable | Producto | Dosis | Animal | Notas
```

#### **ASISTENCIA**
```
Fecha | Empleado | Hora Entrada | Hora Salida | Lote | Actividades
```

#### **GANADO**
```
ID | Fecha | Peso | Precio/kg | Lote | Estado | Notas
```

#### **PAGOS**
```
Fecha | Tipo | Empleado | Monto | Quincena | Comprobante | Notas
```

#### **SEGURIDAD_SOCIAL**
```
Mes | Año | Propia | Empleados | Fecha Pago | Notas
```

#### **FACTURACION**
```
Número | Fecha | Cliente | Descripción | Cantidad | Valor Unitario | Total | Archivo
```

---

## 🔐 Seguridad

- ✅ El bot solo responderá a usuarios autorizados
- ✅ Google Sheets solo será accesible por el sistema
- ✅ Las credenciales se guardarán de forma segura

---

## 📞 Soporte

Si tienes dudas durante la configuración, avísame y te ayudo paso a paso.

---

**Estado:** ⏳ Listo para cuando quieras comenzar
