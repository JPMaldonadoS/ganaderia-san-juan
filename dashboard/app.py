"""
Dashboard Web - Ganadería San Juan
Flask lee el HTML existente, inyecta datos de SQLite y lo sirve.
El diseño visual queda 100% idéntico al original.
"""
import json
import re
import os
import sys
import functools
from flask import Flask, jsonify, send_from_directory, request, Response
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'bot_telegram', '.env'))

# Agregar el path del bot para importar db_handler
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot_telegram'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import db_handler as db
import sheets_sync

app = Flask(__name__)

# ─── Autenticación básica ─────────────────────────────────────────────────────
USUARIOS = {
    os.getenv('DASH_USER', 'sanjuan'): os.getenv('DASH_PASS', 'ganaderia2026'),
}

def requiere_auth(f):
    @functools.wraps(f)
    def decorada(*args, **kwargs):
        auth = request.authorization
        if not auth or USUARIOS.get(auth.username) != auth.password:
            return Response(
                'Acceso restringido — Ganadería San Juan',
                401,
                {'WWW-Authenticate': 'Basic realm="Ganadería San Juan"'}
            )
        return f(*args, **kwargs)
    return decorada

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_HTML = os.path.join(BASE_DIR, 'dashboard-bufalera-san-juan.html')
DOCS_DIR       = os.path.join(BASE_DIR, 'documentos')
ZONA_CO        = ZoneInfo("America/Bogota")

EXTENSIONES_OK = {'.pdf', '.jpg', '.jpeg', '.png', '.gif'}

os.makedirs(os.path.join(DOCS_DIR, 'facturas'), exist_ok=True)
os.makedirs(os.path.join(DOCS_DIR, 'seguridad_social'), exist_ok=True)
os.makedirs(os.path.join(DOCS_DIR, 'nomina'), exist_ok=True)


def get_fecha_actual() -> str:
    return datetime.now(ZONA_CO).strftime('%Y-%m-%d')


def get_fecha_ultimo_reporte() -> str:
    """Fecha del último reporte enviado (último registro en clima)."""
    registros = db.get_clima()
    if registros:
        return max(r['fecha'] for r in registros)
    return get_fecha_actual()


def build_registro_clima() -> list:
    """Convierte los datos de SQLite al formato que usa el dashboard."""
    registros = db.get_clima()
    resultado = []
    for r in registros:
        resultado.append({
            'fecha':        r['fecha'],
            'tipo':         r['tipo'],
            'descripcion':  r['descripcion'] or '',
            'registradoPor': r['registrado_por'] or 'Adriana',
            'luz':          r['luz'] if r['luz'] is not None else 1,
        })
    return sorted(resultado, key=lambda x: x['fecha'])


def build_registro_asistencia() -> list:
    """Convierte asistencia de SQLite al formato del dashboard."""
    registros = db.get_asistencia()
    resultado = []
    for r in registros:
        resultado.append({
            'fecha':          r['fecha'],
            'personalId':     r['personal_id'],
            'presente':       bool(r['presente']),
            'horaEntrada':    r['hora_entrada'] or '',
            'horaSalida':     r['hora_salida'] or '',
            'motivoAusencia': r['motivo_ausencia'] or '',
            'notas':          r['notas'] or '',
        })
    return sorted(resultado, key=lambda x: x['fecha'])


NOMBRES_PERSONAL = {1: 'Adriana Bastidas', 2: 'George Bastidas'}


def build_actividades_finca() -> list:
    """
    Convierte actividades de SQLite al formato del dashboard.
    Si una fecha tiene asistencia pero no actividades, genera las entradas
    'Trabajo diario' automáticamente para que aparezcan en la quincena.
    """
    actividades = db.get_actividades()

    # Fechas que ya tienen actividades guardadas
    fechas_con_actividad = set(a['fecha'] for a in actividades)

    resultado = []
    for a in actividades:
        resultado.append({
            'fecha':        a['fecha'],
            'tipo':         a['tipo'],
            'descripcion':  a['descripcion'] or '',
            'lote':         a['lote'],
            'responsable':  a['responsable'] or '',
            'tipoContrato': a['tipo_contrato'] or 'fijo',
            'completada':   bool(a['completada']),
            'notas':        a['notas'] or '',
        })

    # Derivar "Trabajo diario" desde asistencia para fechas sin actividades
    lote_actual = db.get_lote_actual()
    for r in db.get_asistencia():
        if r['fecha'] not in fechas_con_actividad and r['presente']:
            resultado.append({
                'fecha':        r['fecha'],
                'tipo':         'manejo',
                'descripcion':  'Trabajo diario',
                'lote':         lote_actual,
                'responsable':  NOMBRES_PERSONAL.get(r['personal_id'], 'Personal'),
                'tipoContrato': 'fijo',
                'completada':   True,
                'notas':        r['notas'] or '',
            })

    return sorted(resultado, key=lambda x: x['fecha'])


def build_rotacion_config() -> dict:
    """Obtiene configuración de rotación actual."""
    return {
        'loteActual':      db.get_lote_actual(),
        'fechaEntrada':    db.get_config('fecha_entrada_lote') or '',
        'totalAnimales':   db.get_total_animales(),
    }


def build_historial_movimientos() -> list:
    """Lee rotaciones de DB y las convierte al formato historialMovimientos del JS."""
    rotaciones = db.get_rotaciones()
    result = []
    for r in rotaciones:
        result.append({
            'lote':         r['lote_nuevo'],
            'rotacionNum':  r['numero_rotacion'] or 1,
            'fechaEntrada': r['fecha'] or '',
            'fechaSalida':  r['fecha_salida'],
            'animales':     r['animales'] or 0,
            'nota':         r['notas'] or '',
            'diasEnLote':   r['dias_total'],
        })
    return sorted(result, key=lambda x: x['fechaEntrada'])


def lineas_historial_movimientos(rotaciones: list) -> str:
    lines = []
    for r in rotaciones:
        fecha_salida = f"'{r['fechaSalida']}'" if r['fechaSalida'] else 'null'
        dias_lote    = str(r['diasEnLote']) if r['diasEnLote'] is not None else 'null'
        nota         = r['nota'].replace("'", "")
        lines.append(
            f"            {{ lote: {r['lote']}, rotacionNum: {r['rotacionNum']}, "
            f"fechaEntrada: '{r['fechaEntrada']}', fechaSalida: {fecha_salida}, "
            f"animales: {r['animales']}, nota: '{nota}', "
            f"diasEnLote: {dias_lote}, cuadrasDias: [] }},"
        )
    return '\n'.join(lines)


def fechas_en_html(html: str, patron: str) -> set:
    """Extrae todas las fechas que ya existen en una sección del HTML."""
    return set(re.findall(r"fecha:\s*'(\d{4}-\d{2}-\d{2})'", patron))


def lineas_clima(registros: list) -> str:
    return '\n'.join(
        f"            {{ fecha: '{r['fecha']}', tipo: '{r['tipo']}', "
        f"descripcion: '{r['descripcion'].replace(chr(39), '')}', registradoPor: '{r['registradoPor']}', "
        f"luz: {r.get('luz', 1)} }},"
        for r in registros
    )


def lineas_asistencia(registros: list) -> str:
    return '\n'.join(
        f"            {{ fecha: '{r['fecha']}', personalId: {r['personalId']}, "
        f"presente: {'true' if r['presente'] else 'false'}, "
        f"horaEntrada: '{r['horaEntrada']}', horaSalida: '{r['horaSalida']}', "
        f"motivoAusencia: '{r['motivoAusencia']}', "
        f"notas: '{r['notas'].replace(chr(39), '')}' }},"
        for r in registros
    )


def lineas_actividades(actividades: list) -> str:
    return '\n'.join(
        f"            {{ fecha: '{a['fecha']}', tipo: '{a['tipo']}', "
        f"descripcion: '{a['descripcion'].replace(chr(39), '')}', "
        f"lote: {a['lote'] if a['lote'] else 'null'}, "
        f"responsable: '{a['responsable']}', tipoContrato: '{a['tipoContrato']}', "
        f"completada: true, notas: '{a['notas'].replace(chr(39), '')}' }},"
        for a in actividades
    )


def serve_dashboard():
    """
    Lee el HTML original (histórico intacto) e inserta directamente
    en los arrays JS los nuevos datos de SQLite, usando anchors únicos.
    """
    with open(DASHBOARD_HTML, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Actualizar FECHA_ACTUAL y FECHA_ULTIMO_REPORTE
    fecha_actual = get_fecha_actual()
    html = re.sub(
        r"const FECHA_ACTUAL\s*=\s*'[\d-]+'[^;]*;",
        f"const FECHA_ACTUAL = '{fecha_actual}';  // Flask/SQLite",
        html
    )
    fecha_ultimo_reporte = get_fecha_ultimo_reporte()
    html = re.sub(
        r"const FECHA_ULTIMO_REPORTE\s*=\s*'[\d-]+'[^;]*;",
        f"const FECHA_ULTIMO_REPORTE = '{fecha_ultimo_reporte}';  // Flask/SQLite",
        html
    )

    # 2. Extraer fechas ya en el HTML (entre los markers de cada array)
    # REGISTRO_CLIMA
    m_clima = re.search(r'const REGISTRO_CLIMA\s*=\s*\[(.*?)// ⚠️ AGREGAR NUEVOS REGISTROS AQUÍ', html, re.DOTALL)
    fechas_clima = set(re.findall(r"fecha:\s*'(\d{4}-\d{2}-\d{2})'", m_clima.group(1))) if m_clima else set()

    # REGISTRO_ASISTENCIA
    m_asist = re.search(r'const REGISTRO_ASISTENCIA\s*=\s*\[(.*?)// ⚠️ AGREGAR NUEVOS REGISTROS DE ASISTENCIA AQUÍ', html, re.DOTALL)
    fechas_asist = set(re.findall(r"fecha:\s*'(\d{4}-\d{2}-\d{2})'", m_asist.group(1))) if m_asist else set()

    # ACTIVIDADES_FINCA
    m_activ = re.search(r'const ACTIVIDADES_FINCA\s*=\s*\[(.*?)// ⚠️ Aquí se continuarán agregando', html, re.DOTALL)
    fechas_activ = set(re.findall(r"fecha:\s*'(\d{4}-\d{2}-\d{2})'", m_activ.group(1))) if m_activ else set()

    # 3. Filtrar solo entradas nuevas desde SQLite
    clima_new   = [r for r in build_registro_clima()     if r['fecha'] not in fechas_clima]
    asist_new   = [r for r in build_registro_asistencia() if r['fecha'] not in fechas_asist]
    activ_new   = [r for r in build_actividades_finca()  if r['fecha'] not in fechas_activ]

    # 4. Insertar directamente en el HTML en los anchors (ANTES de renderizar React)
    if clima_new:
        html = html.replace(
            '// ⚠️ AGREGAR NUEVOS REGISTROS AQUÍ',
            lineas_clima(clima_new) + '\n            // ⚠️ AGREGAR NUEVOS REGISTROS AQUÍ'
        )

    if asist_new:
        html = html.replace(
            '// ⚠️ AGREGAR NUEVOS REGISTROS DE ASISTENCIA AQUÍ',
            lineas_asistencia(asist_new) + '\n            // ⚠️ AGREGAR NUEVOS REGISTROS DE ASISTENCIA AQUÍ'
        )

    if activ_new:
        html = html.replace(
            '// ⚠️ Aquí se continuarán agregando las actividades de la quincena',
            lineas_actividades(activ_new) + '\n            // ⚠️ Aquí se continuarán agregando las actividades de la quincena'
        )

    # 5. Actualizar loteActual, fechaEntrada y totalAnimales
    rotacion = build_rotacion_config()
    html = re.sub(r'(loteActual\s*:\s*)\d+', f"loteActual: {rotacion['loteActual']}", html, count=1)
    html = re.sub(r'(totalAnimales\s*:\s*)\d+', f"totalAnimales: {rotacion['totalAnimales']}", html, count=1)
    html = re.sub(r"(fechaEntrada\s*:\s*)'[\d-]+'", f"fechaEntrada: '{rotacion['fechaEntrada']}'", html, count=1)

    # 6. Inyectar historialMovimientos desde DB (solo entradas nuevas no presentes en HTML)
    MARKER_HISTORIAL = '// ⚠️ HISTORIAL ROTACIONES DB'
    m_hist = re.search(
        r'historialMovimientos:\s*\[(.+?)' + re.escape(MARKER_HISTORIAL),
        html, re.DOTALL
    )
    if m_hist:
        existing = set(re.findall(
            r"lote:\s*(\d+)[^}]*?fechaEntrada:\s*'(\d{4}-\d{2}-\d{2})'",
            m_hist.group(1), re.DOTALL
        ))
        db_historial = build_historial_movimientos()
        nuevas = [r for r in db_historial if (str(r['lote']), r['fechaEntrada']) not in existing]
        if nuevas:
            html = html.replace(
                MARKER_HISTORIAL,
                lineas_historial_movimientos(nuevas) + '\n                ' + MARKER_HISTORIAL,
                1
            )

    # 7. Actualizar rotacionesPorLote desde DB (solo incrementa, nunca reduce valor HTML)
    db_counts: dict[int, int] = {}
    for r in db.get_rotaciones():
        lote_n = r['lote_nuevo']
        nr     = r['numero_rotacion'] or 1
        if nr > db_counts.get(lote_n, 0):
            db_counts[lote_n] = nr

    if db_counts:
        def _actualizar_rotaciones(match):
            bloque = match.group(1)
            for lote_num, cnt in db_counts.items():
                m_actual = re.search(rf'\b{lote_num}:\s*(\d+)', bloque)
                if m_actual and cnt > int(m_actual.group(1)):
                    bloque = re.sub(rf'\b{lote_num}:\s*\d+', f'{lote_num}: {cnt}', bloque)
            return 'rotacionesPorLote: {' + bloque + '}'
        html = re.sub(
            r'rotacionesPorLote:\s*\{([^}]+)\}',
            _actualizar_rotaciones,
            html, count=1
        )

    # Inyectar auto-refresh: recarga solo si la DB cambió
    AUTO_REFRESH_JS = """
<script>
(function() {
  var _ts = null;
  function checkUpdate() {
    fetch('/api/ultimo-update')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (_ts === null) { _ts = d.ts; return; }
        if (d.ts !== _ts) { location.reload(); }
      })
      .catch(function() {});
  }
  setInterval(checkUpdate, 60000);
  checkUpdate();
})();
</script>
"""
    last = html.rfind('</body>')
    if last != -1:
        html = html[:last] + AUTO_REFRESH_JS + html[last:]

    return html


# ─── Rutas ───────────────────────────────────────────────────────────────────

@app.route('/')
@requiere_auth
def index():
    html = serve_dashboard()
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/api/ultimo-update')
@requiere_auth
def api_ultimo_update():
    db_path = os.path.join(BASE_DIR, 'data', 'ganaderia.db')
    ts = int(os.path.getmtime(db_path)) if os.path.exists(db_path) else 0
    return jsonify({'ts': ts})


@app.route('/api/data')
@requiere_auth
def api_data():
    return jsonify(db.exportar_para_dashboard())


@app.route('/api/clima')
@requiere_auth
def api_clima():
    return jsonify(build_registro_clima())


@app.route('/api/asistencia')
@requiere_auth
def api_asistencia():
    return jsonify(build_registro_asistencia())


@app.route('/api/actividades')
@requiere_auth
def api_actividades():
    return jsonify(build_actividades_finca())


@app.route('/api/sanitario')
@requiere_auth
def api_sanitario():
    registros = db.get_sanitario()
    # Normalize field names to match dashboard format
    result = []
    for r in registros:
        result.append({
            'id': r['id'],
            'fecha': r['fecha'],
            'tipo': r['tipo'],
            'descripcion': r.get('notas') or r.get('tipo', ''),
            'loteAplicado': r.get('lote_animales') or 'todos',
            'animalesAfectados': r.get('cantidad') or 0,
            'producto': r.get('producto') or 'No especificado',
            'responsable': r.get('responsable') or 'Adriana Bastidas',
            'notas': r.get('notas') or '',
            'fromDB': True,
        })
    return jsonify(result)


@app.route('/api/config')
@requiere_auth
def api_config():
    return jsonify(build_rotacion_config())


@app.route('/media/<path:filename>')
@requiere_auth
def media(filename):
    return send_from_directory(BASE_DIR, filename)


# El dashboard busca el video en la raíz — lo servimos desde aquí también
@app.route('/Video1.mp4')
@requiere_auth
def video_mp4():
    return send_from_directory(BASE_DIR, 'Video1.mp4')


@app.route('/Video1.mov')
@requiere_auth
def video_mov():
    return send_from_directory(BASE_DIR, 'Video1.mov')


@app.route('/videorayasx.mp4')
@requiere_auth
def video_rayasx():
    return send_from_directory(BASE_DIR, 'videorayasx.mp4')


# ─── Documentos (PDFs guardados en disco) ─────────────────────────────────────

@app.route('/documentos/<path:filename>')
@requiere_auth
def serve_documento(filename):
    return send_from_directory(DOCS_DIR, filename)


@app.route('/api/upload', methods=['POST'])
@requiere_auth
def upload_documento():
    """Recibe un archivo y lo guarda en /documentos/<categoria>/"""
    if 'file' not in request.files:
        return jsonify({'error': 'Sin archivo'}), 400
    archivo = request.files['file']
    if not archivo.filename:
        return jsonify({'error': 'Nombre vacío'}), 400

    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in EXTENSIONES_OK:
        return jsonify({'error': f'Tipo no permitido: {ext}'}), 400

    categoria = request.form.get('categoria', 'otros')  # facturas | seguridad_social | nomina
    nombre_base = request.form.get('nombre', 'documento')
    nombre_seguro = secure_filename(f"{nombre_base}{ext}")

    carpeta = os.path.join(DOCS_DIR, categoria)
    os.makedirs(carpeta, exist_ok=True)
    ruta_completa = os.path.join(carpeta, nombre_seguro)
    archivo.save(ruta_completa)

    path_relativo = f"{categoria}/{nombre_seguro}"
    return jsonify({'ok': True, 'path': path_relativo, 'nombre': nombre_seguro})


# ─── Facturas ─────────────────────────────────────────────────────────────────

@app.route('/api/facturas', methods=['GET'])
@requiere_auth
def api_get_facturas():
    return jsonify(db.get_facturas())


@app.route('/api/facturas', methods=['POST'])
@requiere_auth
def api_crear_factura():
    data = request.json
    valor_total = float(data['valorTotal'])
    factura_id = db.guardar_factura(
        numero_factura = data['numeroFactura'],
        fecha          = data['fecha'],
        cliente        = data['cliente'],
        descripcion    = data.get('descripcion', ''),
        valor_total    = valor_total,
        cantidad       = float(data['cantidad']) if data.get('cantidad') else None,
        valor_unitario = float(data['valorUnitario']) if data.get('valorUnitario') else None,
        metodo_pago    = data.get('metodoPago', ''),
        notas          = data.get('notas', ''),
        archivo_path   = data.get('archivoPath', ''),
        nombre_archivo = data.get('nombreArchivo', ''),
    )
    # Crear automáticamente el ingreso en finanzas
    detalle_finanza = f"Factura {data['numeroFactura']} — {data['cliente']}"
    db.guardar_finanza(
        fecha       = data['fecha'],
        detalle     = detalle_finanza,
        ingreso     = valor_total,
        tipo        = 'ingreso',
        categoria   = 'ganado',
        forma_pago  = data.get('metodoPago', ''),
        notas       = data.get('descripcion', ''),
        factura_id  = factura_id,
    )
    return jsonify({'ok': True, 'id': factura_id})


@app.route('/api/facturas/<int:factura_id>', methods=['DELETE'])
@requiere_auth
def api_eliminar_factura(factura_id):
    db.eliminar_factura(factura_id)
    return jsonify({'ok': True})


# ─── Seguridad Social ─────────────────────────────────────────────────────────

@app.route('/api/seguridad-social', methods=['GET'])
@requiere_auth
def api_get_seguridad():
    anio = request.args.get('anio', type=int)
    return jsonify(db.get_pagos_seguridad(anio))


@app.route('/api/seguridad-social', methods=['POST'])
@requiere_auth
def api_guardar_seguridad():
    data = request.json
    db.guardar_pago_seguridad(
        anio           = int(data['anio']),
        mes            = int(data['mes']),
        tipo           = data['tipo'],
        archivo_path   = data.get('archivoPath', ''),
        nombre_archivo = data.get('nombreArchivo', ''),
    )
    return jsonify({'ok': True})


# ─── Comprobantes de Nómina ───────────────────────────────────────────────────

@app.route('/api/comprobantes-nomina', methods=['GET'])
@requiere_auth
def api_get_comprobantes():
    anio = request.args.get('anio', type=int)
    mes  = request.args.get('mes', type=int)
    return jsonify(db.get_comprobantes_nomina(anio, mes))


@app.route('/api/comprobantes-nomina', methods=['POST'])
@requiere_auth
def api_guardar_comprobante():
    data = request.json
    db.guardar_comprobante_nomina(
        anio           = int(data['anio']),
        mes            = int(data['mes']),
        quincena       = int(data['quincena']),
        personal_id    = int(data['personalId']),
        archivo_path   = data.get('archivoPath', ''),
        nombre_archivo = data.get('nombreArchivo', ''),
    )
    return jsonify({'ok': True})


# ─── Pagos Realizados ─────────────────────────────────────────────────────────

@app.route('/api/pagos-realizados', methods=['GET'])
@requiere_auth
def api_get_pagos():
    return jsonify(db.get_pagos_realizados())


@app.route('/api/pagos-realizados', methods=['POST'])
@requiere_auth
def api_guardar_pago():
    data = request.json
    db.guardar_pago_realizado(clave=data['clave'], fecha=data.get('fecha', ''))
    return jsonify({'ok': True})


@app.route('/api/pagos-realizados/seed', methods=['POST'])
@requiere_auth
def api_seed_pagos():
    db.seed_pagos_defecto(request.json)
    return jsonify({'ok': True})


@app.route('/api/pagos-realizados/<path:clave>', methods=['DELETE'])
@requiere_auth
def api_eliminar_pago(clave):
    db.eliminar_pago_realizado(clave)
    return jsonify({'ok': True})


# ─── Historial de Pagos ───────────────────────────────────────────────────────

@app.route('/api/historial-pagos', methods=['GET'])
@requiere_auth
def api_get_historial():
    return jsonify(db.get_historial_pagos())


@app.route('/api/historial-pagos', methods=['POST'])
@requiere_auth
def api_guardar_historial():
    data = request.json
    db.guardar_historial_pago(
        fecha              = data.get('fecha', ''),
        quincena           = data['quincena'],
        tipo               = data['tipo'],
        personal_id        = data.get('personalId'),
        beneficiario       = data.get('beneficiario', ''),
        total_devengado    = float(data.get('totalDevengado', 0)),
        total_deducciones  = float(data.get('totalDeducciones', 0)),
        total_pagado       = float(data.get('totalPagado', 0)),
        metodo_pago        = data.get('metodoPago', 'transferencia'),
        referencia         = data.get('referencia', ''),
        notas              = data.get('notas', ''),
        indice_comprobante = data.get('indiceComprobante'),
        archivo_path       = data.get('archivoPath', ''),
    )
    return jsonify({'ok': True})


@app.route('/api/movimientos-cuadra', methods=['GET'])
@requiere_auth
def api_get_movimientos_cuadra():
    lote = request.args.get('lote', type=int)
    return jsonify(db.get_movimientos_cuadra(lote=lote))


@app.route('/api/movimientos-cuadra', methods=['POST'])
@requiere_auth
def api_guardar_movimiento_cuadra():
    data = request.json
    db.guardar_movimiento_cuadra(
        fecha       = data.get('fecha', get_fecha_actual()),
        lote        = data['lote'],
        cuadra_nueva= data['cuadraNueva'],
        animales    = data.get('animales'),
        notas       = data.get('notas', ''),
    )
    return jsonify({'ok': True})


# ─── Finanzas ─────────────────────────────────────────────────────────────────

@app.route('/api/finanzas', methods=['GET'])
@requiere_auth
def api_get_finanzas():
    return jsonify(db.get_finanzas(
        anio      = request.args.get('anio'),
        mes       = request.args.get('mes'),
        tipo      = request.args.get('tipo'),
        categoria = request.args.get('categoria'),
        forma_pago= request.args.get('forma_pago'),
        busqueda  = request.args.get('busqueda'),
    ))


@app.route('/api/finanzas/resumen', methods=['GET'])
@requiere_auth
def api_resumen_finanzas():
    return jsonify(db.get_finanzas_resumen(anio=request.args.get('anio')))


@app.route('/api/finanzas', methods=['POST'])
@requiere_auth
def api_crear_finanza():
    data = request.json
    monto = float(data.get('monto', 0))
    tipo  = data.get('tipo', 'gasto')
    ingreso  = monto if tipo == 'ingreso' else 0.0
    prestamo = monto if tipo == 'prestamo_recibido' else 0.0
    gasto    = monto if tipo == 'gasto' else 0.0
    new_id = db.guardar_finanza(
        fecha      = data['fecha'],
        detalle    = data['detalle'],
        ingreso    = ingreso,
        prestamo   = prestamo,
        gasto      = gasto,
        tipo       = tipo,
        categoria  = data.get('categoria', 'otro'),
        forma_pago = data.get('formaPago', ''),
        notas      = data.get('notas', ''),
    )
    sheets_sync.sincronizar_todo(db.get_finanzas())
    return jsonify({'ok': True, 'id': new_id})


@app.route('/api/finanzas/<int:finanza_id>', methods=['PUT'])
@requiere_auth
def api_editar_finanza(finanza_id):
    data = request.json
    monto = float(data.get('monto', 0))
    tipo  = data.get('tipo', 'gasto')
    ingreso  = monto if tipo == 'ingreso' else 0.0
    prestamo = monto if tipo == 'prestamo_recibido' else 0.0
    gasto    = monto if tipo == 'gasto' else 0.0
    db.actualizar_finanza(
        finanza_id = finanza_id,
        fecha      = data['fecha'],
        detalle    = data['detalle'],
        ingreso    = ingreso,
        prestamo   = prestamo,
        gasto      = gasto,
        tipo       = tipo,
        categoria  = data.get('categoria', 'otro'),
        forma_pago = data.get('formaPago', ''),
        notas      = data.get('notas', ''),
    )
    sheets_sync.sincronizar_todo(db.get_finanzas())
    return jsonify({'ok': True})


@app.route('/api/finanzas/<int:finanza_id>', methods=['DELETE'])
@requiere_auth
def api_eliminar_finanza(finanza_id):
    db.eliminar_finanza(finanza_id)
    sheets_sync.sincronizar_todo(db.get_finanzas())
    return jsonify({'ok': True})


# ─── Informe mensual de finanzas ──────────────────────────────────────────────

@app.route('/api/finanzas/informe', methods=['GET'])
@requiere_auth
def api_informe_mensual():
    try:
        anio = int(request.args.get('anio', datetime.now(ZONA_CO).year))
        mes  = int(request.args.get('mes',  datetime.now(ZONA_CO).month))
    except (ValueError, TypeError):
        return jsonify({'error': 'Parámetros inválidos'}), 400
    return jsonify(db.get_informe_mensual(anio, mes))


# ─── Documentos adjuntos a finanzas ───────────────────────────────────────────

@app.route('/api/finanzas/<int:finanza_id>/docs', methods=['GET'])
@requiere_auth
def api_get_finanza_docs(finanza_id):
    return jsonify(db.get_finanzas_docs(finanza_id))


@app.route('/api/finanzas/<int:finanza_id>/docs', methods=['POST'])
@requiere_auth
def api_crear_finanza_doc(finanza_id):
    data = request.json
    doc_id = db.guardar_finanza_doc(
        finanza_id     = finanza_id,
        archivo_path   = data['archivoPath'],
        nombre_archivo = data['nombreArchivo'],
        tipo           = data.get('tipo', 'comprobante'),
    )
    return jsonify({'ok': True, 'id': doc_id})


@app.route('/api/finanzas/docs/<int:doc_id>', methods=['DELETE'])
@requiere_auth
def api_eliminar_finanza_doc(doc_id):
    info = db.eliminar_finanza_doc(doc_id)
    if info and info.get('archivo_path'):
        ruta = os.path.join(DOCS_DIR, info['archivo_path'])
        if os.path.exists(ruta):
            os.remove(ruta)
    return jsonify({'ok': True})


if __name__ == '__main__':
    db.inicializar_db()
    print("Dashboard iniciando...")
    print(f"Abre en tu navegador: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
