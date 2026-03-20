"""
Manejador de Google Sheets para Ganadería San Juan
Guarda y lee datos históricos de la finca
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import config

# Scopes necesarios para Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def get_client():
    """Obtiene el cliente autenticado de Google Sheets"""
    creds = Credentials.from_service_account_file(
        config.CREDENTIALS_FILE,
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def get_spreadsheet():
    """Obtiene el spreadsheet de la ganadería"""
    client = get_client()
    return client.open_by_key(config.GOOGLE_SHEET_ID)


# ═══════════════════════════════════════════════════════════════
# JORNALES
# ═══════════════════════════════════════════════════════════════

def agregar_jornal(fecha: str, tipo: str, lote: str, cantidad: int, 
                   responsable: str = "Jornalero", notas: str = ""):
    """
    Agrega un registro de jornal a la hoja JORNALES
    
    Args:
        fecha: Fecha en formato YYYY-MM-DD
        tipo: Tipo de jornal (Corral, Casa, Cercas, etc.)
        lote: Número de lote o 'corral', 'casa'
        cantidad: Número de jornales
        responsable: Quien realizó el trabajo
        notas: Observaciones adicionales
    """
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('JORNALES')
        
        # Agregar fila
        hoja.append_row([
            fecha,
            tipo,
            str(lote),
            cantidad,
            responsable,
            notas,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Timestamp de registro
        ])
        return True
    except Exception as e:
        print(f"Error al agregar jornal: {e}")
        return False


def obtener_jornales(desde: str = None, hasta: str = None):
    """Obtiene los jornales, opcionalmente filtrados por fecha"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('JORNALES')
        datos = hoja.get_all_records()
        
        if desde:
            datos = [d for d in datos if d['Fecha'] >= desde]
        if hasta:
            datos = [d for d in datos if d['Fecha'] <= hasta]
            
        return datos
    except Exception as e:
        print(f"Error al obtener jornales: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# TRACTOR
# ═══════════════════════════════════════════════════════════════

def agregar_tractor(fecha: str, lote: int, hectareas: float, 
                    tipo_trabajo: str = "Cortamalezas", notas: str = ""):
    """
    Agrega un registro de trabajo de tractor
    
    Args:
        fecha: Fecha en formato YYYY-MM-DD
        lote: Número del lote (1-10)
        hectareas: Hectáreas trabajadas
        tipo_trabajo: Tipo de trabajo realizado
        notas: Observaciones adicionales
    """
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('TRACTOR')
        
        hoja.append_row([
            fecha,
            lote,
            hectareas,
            tipo_trabajo,
            notas,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
        return True
    except Exception as e:
        print(f"Error al agregar tractor: {e}")
        return False


def obtener_tractor(desde: str = None, hasta: str = None):
    """Obtiene los trabajos de tractor"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('TRACTOR')
        datos = hoja.get_all_records()
        
        if desde:
            datos = [d for d in datos if d['Fecha'] >= desde]
        if hasta:
            datos = [d for d in datos if d['Fecha'] <= hasta]
            
        return datos
    except Exception as e:
        print(f"Error al obtener tractor: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# ROTACIÓN DE GANADO
# ═══════════════════════════════════════════════════════════════

def agregar_rotacion(fecha: str, lote_anterior: int, lote_nuevo: int, 
                     animales: int = 81, notas: str = ""):
    """
    Registra un cambio de lote del ganado
    
    Args:
        fecha: Fecha del cambio
        lote_anterior: Lote de donde salieron (0 si es entrada inicial)
        lote_nuevo: Lote a donde entraron
        animales: Número de animales movidos
        notas: Observaciones
    """
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('ROTACION')
        
        hoja.append_row([
            fecha,
            lote_anterior if lote_anterior else '-',
            lote_nuevo,
            animales,
            notas,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
        
        # Actualizar CONFIG con el lote actual
        actualizar_config('LOTE_GANADO_ACTUAL', lote_nuevo)
        actualizar_config('FECHA_ENTRADA_LOTE', fecha)
        
        return True
    except Exception as e:
        print(f"Error al agregar rotación: {e}")
        return False


def obtener_lote_actual():
    """Obtiene el lote donde está actualmente el ganado"""
    try:
        return int(obtener_config('LOTE_GANADO_ACTUAL') or 1)
    except:
        return 1


def obtener_rotaciones():
    """Obtiene el historial de rotaciones"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('ROTACION')
        return hoja.get_all_records()
    except Exception as e:
        print(f"Error al obtener rotaciones: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# ACTIVIDADES SANITARIAS
# ═══════════════════════════════════════════════════════════════

def agregar_sanitario(fecha: str, tipo: str, lote_animales: str, 
                      cantidad: int, producto: str = "", 
                      responsable: str = "Adriana Bastidas", notas: str = ""):
    """
    Registra una actividad sanitaria
    
    Args:
        fecha: Fecha de la actividad
        tipo: vacunacion, purga, vitamina, marcacion
        lote_animales: 'Octubre 2025', 'Enero 2026', 'todos'
        cantidad: Número de animales tratados
        producto: Nombre del producto usado
        responsable: Quien realizó la actividad
        notas: Observaciones
    """
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('SANITARIO')
        
        hoja.append_row([
            fecha,
            tipo,
            lote_animales,
            cantidad,
            producto,
            responsable,
            notas,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
        return True
    except Exception as e:
        print(f"Error al agregar sanitario: {e}")
        return False


def obtener_sanitario(desde: str = None, hasta: str = None):
    """Obtiene el historial sanitario"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('SANITARIO')
        datos = hoja.get_all_records()
        
        if desde:
            datos = [d for d in datos if d['Fecha'] >= desde]
        if hasta:
            datos = [d for d in datos if d['Fecha'] <= hasta]
            
        return datos
    except Exception as e:
        print(f"Error al obtener sanitario: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# ASISTENCIA
# ═══════════════════════════════════════════════════════════════

def agregar_asistencia(fecha: str, empleado: str, presente: bool, 
                       hora_entrada: str = "", hora_salida: str = "", 
                       motivo_ausencia: str = "", notas: str = ""):
    """
    Registra la asistencia de un empleado
    
    Args:
        fecha: Fecha del registro
        empleado: Nombre del empleado
        presente: True si asistió
        hora_entrada: Hora de entrada
        hora_salida: Hora de salida
        motivo_ausencia: Motivo si no asistió (enfermedad, vacaciones, etc.)
        notas: Observaciones
    """
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('ASISTENCIA')
        
        hoja.append_row([
            fecha,
            empleado,
            'Sí' if presente else 'No',
            hora_entrada,
            hora_salida,
            motivo_ausencia if not presente else '',
            notas,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
        
        # Si hay ausencia con motivo especial, registrar en novedades
        if not presente and motivo_ausencia:
            agregar_novedad_personal(fecha, empleado, motivo_ausencia, notas)
        
        return True
    except Exception as e:
        print(f"Error al agregar asistencia: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# NOVEDADES DE PERSONAL (Incapacidades, Vacaciones, etc.)
# ═══════════════════════════════════════════════════════════════

def agregar_novedad_personal(fecha_inicio: str, empleado: str, tipo: str, 
                             notas: str = "", fecha_fin: str = "", dias: int = 1):
    """
    Registra una novedad de personal (incapacidad, vacaciones, etc.)
    
    Args:
        fecha_inicio: Fecha de inicio de la novedad
        empleado: Nombre del empleado
        tipo: Tipo de novedad (incapacidad, vacaciones, enfermedad, etc.)
        notas: Observaciones
        fecha_fin: Fecha estimada de fin (opcional)
        dias: Días estimados de ausencia
    """
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('NOVEDADES_PERSONAL')
        
        hoja.append_row([
            fecha_inicio,
            empleado,
            tipo,
            fecha_fin if fecha_fin else 'Por definir',
            dias,
            'Activa',  # Estado: Activa, Finalizada
            notas,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
        return True
    except Exception as e:
        print(f"Error al agregar novedad: {e}")
        return False


def obtener_novedades_activas():
    """Obtiene las novedades de personal activas"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('NOVEDADES_PERSONAL')
        datos = hoja.get_all_records()
        
        # Filtrar solo las activas
        return [d for d in datos if d.get('Estado') == 'Activa']
    except Exception as e:
        print(f"Error al obtener novedades: {e}")
        return []


def obtener_novedades_personal(desde: str = None, hasta: str = None):
    """Obtiene todas las novedades de personal"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('NOVEDADES_PERSONAL')
        datos = hoja.get_all_records()
        
        if desde:
            datos = [d for d in datos if d['Fecha_Inicio'] >= desde]
        if hasta:
            datos = [d for d in datos if d['Fecha_Inicio'] <= hasta]
            
        return datos
    except Exception as e:
        print(f"Error al obtener novedades: {e}")
        return []


def finalizar_novedad(empleado: str, tipo: str):
    """Marca una novedad como finalizada"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('NOVEDADES_PERSONAL')
        datos = hoja.get_all_records()
        
        for idx, d in enumerate(datos):
            if d.get('Empleado') == empleado and d.get('Tipo') == tipo and d.get('Estado') == 'Activa':
                # +2 porque los índices empiezan en 1 y hay encabezado
                hoja.update_cell(idx + 2, 6, 'Finalizada')
                return True
        return False
    except Exception as e:
        print(f"Error al finalizar novedad: {e}")
        return False


def obtener_asistencia(desde: str = None, hasta: str = None):
    """Obtiene el registro de asistencia"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('ASISTENCIA')
        datos = hoja.get_all_records()
        
        if desde:
            datos = [d for d in datos if d['Fecha'] >= desde]
        if hasta:
            datos = [d for d in datos if d['Fecha'] <= hasta]
            
        return datos
    except Exception as e:
        print(f"Error al obtener asistencia: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
# NÓMINA Y PAGOS
# ═══════════════════════════════════════════════════════════════

def agregar_pago(fecha: str, quincena: str, tipo: str, beneficiario: str,
                 total_devengado: float, total_deducciones: float, total_pagado: float,
                 metodo_pago: str = "Transferencia", referencia: str = "", notas: str = ""):
    """
    Registra un pago realizado a un empleado o contratista
    
    Args:
        fecha: Fecha del pago
        quincena: Quincena a la que corresponde (ej: '1ra Quincena Enero 2026')
        tipo: 'nomina' para empleados fijos, 'contratista' para jornales/tractor
        beneficiario: Nombre del empleado o tipo de contratista
        total_devengado: Total devengado
        total_deducciones: Total de deducciones
        total_pagado: Neto pagado
        metodo_pago: 'Transferencia', 'Efectivo', etc.
        referencia: Número de referencia del pago bancario
        notas: Observaciones
    """
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('PAGOS')
        
        hoja.append_row([
            fecha,
            quincena,
            tipo,
            beneficiario,
            total_devengado,
            total_deducciones,
            total_pagado,
            metodo_pago,
            referencia,
            notas,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])
        return True
    except Exception as e:
        print(f"Error al agregar pago: {e}")
        return False


def obtener_pagos(desde: str = None, hasta: str = None, beneficiario: str = None):
    """Obtiene el historial de pagos"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('PAGOS')
        datos = hoja.get_all_records()
        
        if desde:
            datos = [d for d in datos if d['Fecha'] >= desde]
        if hasta:
            datos = [d for d in datos if d['Fecha'] <= hasta]
        if beneficiario:
            datos = [d for d in datos if d['Beneficiario'] == beneficiario]
            
        return datos
    except Exception as e:
        print(f"Error al obtener pagos: {e}")
        return []


def obtener_pagos_quincena(quincena: str):
    """Obtiene todos los pagos de una quincena específica"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('PAGOS')
        datos = hoja.get_all_records()
        
        return [d for d in datos if d.get('Quincena') == quincena]
    except Exception as e:
        print(f"Error al obtener pagos de quincena: {e}")
        return []


def calcular_totales_quincena(quincena: str):
    """
    Calcula los totales de una quincena
    Retorna: jornales, hectareas_tractor, total_jornales, total_tractor
    """
    try:
        # Determinar fechas de la quincena
        partes = quincena.split()
        es_primera = partes[0] == '1ra'
        meses = {'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6,
                 'Julio': 7, 'Agosto': 8, 'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12}
        mes = meses.get(partes[2], 1)
        año = int(partes[3])
        
        if es_primera:
            fecha_inicio = f"{año}-{mes:02d}-01"
            fecha_fin = f"{año}-{mes:02d}-15"
        else:
            fecha_inicio = f"{año}-{mes:02d}-16"
            # Último día del mes
            import calendar
            ultimo_dia = calendar.monthrange(año, mes)[1]
            fecha_fin = f"{año}-{mes:02d}-{ultimo_dia}"
        
        # Obtener jornales de la quincena
        jornales = obtener_jornales(desde=fecha_inicio, hasta=fecha_fin)
        total_jornales = sum(j.get('Cantidad', 1) for j in jornales)
        
        # Obtener trabajo de tractor
        tractor = obtener_tractor(desde=fecha_inicio, hasta=fecha_fin)
        total_hectareas = sum(t.get('Hectareas', 0) for t in tractor)
        
        return {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'jornales': total_jornales,
            'hectareas_tractor': total_hectareas,
            'detalle_jornales': jornales,
            'detalle_tractor': tractor
        }
    except Exception as e:
        print(f"Error al calcular totales: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE NÓMINA
# ═══════════════════════════════════════════════════════════════

def obtener_config_nomina(empleado: str):
    """Obtiene la configuración de nómina de un empleado"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('CONFIG_NOMINA')
        datos = hoja.get_all_records()
        
        for d in datos:
            if d.get('Empleado') == empleado:
                return d
        return None
    except Exception as e:
        print(f"Error al obtener config nómina: {e}")
        return None


def actualizar_config_nomina(empleado: str, salario_basico: float = None, 
                             auxilio_transporte: float = None, bonificaciones: float = None):
    """Actualiza la configuración de nómina de un empleado"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('CONFIG_NOMINA')
        datos = hoja.get_all_records()
        
        for idx, d in enumerate(datos):
            if d.get('Empleado') == empleado:
                fila = idx + 2  # +2 por encabezado y base 0
                if salario_basico is not None:
                    hoja.update_cell(fila, 2, salario_basico)
                if auxilio_transporte is not None:
                    hoja.update_cell(fila, 3, auxilio_transporte)
                if bonificaciones is not None:
                    hoja.update_cell(fila, 4, bonificaciones)
                return True
        
        # Si no existe, crear
        if salario_basico is not None:
            hoja.append_row([empleado, salario_basico, auxilio_transporte or 0, bonificaciones or 0])
        return True
    except Exception as e:
        print(f"Error al actualizar config nómina: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

def obtener_config(parametro: str):
    """Obtiene un valor de configuración"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('CONFIG')
        datos = hoja.get_all_records()
        
        for fila in datos:
            if fila.get('Parametro') == parametro:
                return fila.get('Valor')
        return None
    except Exception as e:
        print(f"Error al obtener config: {e}")
        return None


def actualizar_config(parametro: str, valor):
    """Actualiza un valor de configuración"""
    try:
        sheet = get_spreadsheet()
        hoja = sheet.worksheet('CONFIG')
        
        # Buscar la fila del parámetro
        celdas = hoja.findall(parametro)
        if celdas:
            fila = celdas[0].row
            hoja.update_cell(fila, 2, str(valor))
        else:
            # Si no existe, crear
            hoja.append_row([parametro, str(valor)])
        return True
    except Exception as e:
        print(f"Error al actualizar config: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# EXPORTAR DATOS PARA EL DASHBOARD
# ═══════════════════════════════════════════════════════════════

def exportar_datos_dashboard():
    """
    Exporta todos los datos en formato JSON para el dashboard
    """
    return {
        'config': {
            'lote_actual': obtener_lote_actual(),
            'fecha_entrada_lote': obtener_config('FECHA_ENTRADA_LOTE'),
            'total_animales': int(obtener_config('TOTAL_ANIMALES') or 81),
        },
        'jornales': obtener_jornales(),
        'tractor': obtener_tractor(),
        'rotaciones': obtener_rotaciones(),
        'sanitario': obtener_sanitario(),
        'asistencia': obtener_asistencia(),
    }


# ═══════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE HOJAS
# ═══════════════════════════════════════════════════════════════

def inicializar_hojas():
    """
    Crea las hojas necesarias si no existen con sus encabezados
    """
    try:
        sheet = get_spreadsheet()
        hojas_existentes = [h.title for h in sheet.worksheets()]
        
        # Definir estructura de cada hoja
        estructuras = {
            'JORNALES': ['Fecha', 'Tipo', 'Lote', 'Cantidad', 'Responsable', 'Notas', 'Timestamp'],
            'TRACTOR': ['Fecha', 'Lote', 'Hectareas', 'Tipo_Trabajo', 'Notas', 'Timestamp'],
            'ROTACION': ['Fecha', 'Lote_Anterior', 'Lote_Nuevo', 'Animales', 'Notas', 'Timestamp'],
            'SANITARIO': ['Fecha', 'Tipo', 'Lote_Animales', 'Cantidad', 'Producto', 'Responsable', 'Notas', 'Timestamp'],
            'ASISTENCIA': ['Fecha', 'Empleado', 'Presente', 'Hora_Entrada', 'Hora_Salida', 'Motivo_Ausencia', 'Notas', 'Timestamp'],
            'NOVEDADES_PERSONAL': ['Fecha_Inicio', 'Empleado', 'Tipo', 'Fecha_Fin', 'Dias', 'Estado', 'Notas', 'Timestamp'],
            'PAGOS': ['Fecha', 'Quincena', 'Tipo', 'Beneficiario', 'Total_Devengado', 'Total_Deducciones', 'Total_Pagado', 'Metodo_Pago', 'Referencia', 'Notas', 'Timestamp'],
            'CONFIG_NOMINA': ['Empleado', 'Salario_Basico', 'Auxilio_Transporte', 'Bonificaciones', 'EPS', 'AFP', 'Cedula', 'Banco', 'Cuenta'],
            'CONFIG': ['Parametro', 'Valor'],
        }
        
        for nombre_hoja, encabezados in estructuras.items():
            if nombre_hoja not in hojas_existentes:
                nueva_hoja = sheet.add_worksheet(title=nombre_hoja, rows=1000, cols=len(encabezados))
                nueva_hoja.append_row(encabezados)
                print(f"✓ Hoja '{nombre_hoja}' creada")
            else:
                print(f"• Hoja '{nombre_hoja}' ya existe")
        
        # Inicializar CONFIG con valores por defecto
        config_hoja = sheet.worksheet('CONFIG')
        config_actual = config_hoja.get_all_records()
        parametros_existentes = [c.get('Parametro') for c in config_actual]
        
        valores_iniciales = {
            'LOTE_GANADO_ACTUAL': '1',
            'FECHA_ENTRADA_LOTE': '2025-12-31',
            'TOTAL_ANIMALES': '81',
            'FECHA_ACTUAL': datetime.now().strftime('%Y-%m-%d'),
        }
        
        for param, valor in valores_iniciales.items():
            if param not in parametros_existentes:
                config_hoja.append_row([param, valor])
                print(f"  + Config '{param}' = {valor}")
        
        # Inicializar CONFIG_NOMINA con los empleados
        nomina_hoja = sheet.worksheet('CONFIG_NOMINA')
        nomina_actual = nomina_hoja.get_all_records()
        empleados_existentes = [c.get('Empleado') for c in nomina_actual]
        
        empleados_iniciales = [
            # [Empleado, Salario_Basico, Auxilio_Transporte, Bonificaciones, EPS, AFP, Cedula, Banco, Cuenta]
            ['Adriana Bastidas', 1800000, 200000, 0, '', '', '', '', ''],
            ['George Bastidas', 1500000, 200000, 0, '', '', '', '', ''],
        ]
        
        for emp in empleados_iniciales:
            if emp[0] not in empleados_existentes:
                nomina_hoja.append_row(emp)
                print(f"  + Nómina '{emp[0]}' = ${emp[1]:,}")
        
        print("\n✓ Inicialización completada")
        return True
        
    except Exception as e:
        print(f"Error en inicialización: {e}")
        return False


if __name__ == '__main__':
    # Test de conexión
    print("Probando conexión con Google Sheets...")
    inicializar_hojas()
