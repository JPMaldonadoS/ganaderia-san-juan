"""
Manejador de base de datos SQLite para Ganadería San Juan
Reemplaza completamente Google Sheets — sin permisos, sin internet, sin costo.
"""
import sqlite3
import os
from datetime import datetime
import config

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), config.DB_PATH))


def get_conn():
    """Retorna una conexión a la base de datos."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Resultados como diccionarios
    conn.execute("PRAGMA journal_mode=WAL")  # Mejor rendimiento concurrente
    return conn


# ═══════════════════════════════════════════════════════════════
# INICIALIZACIÓN — crea todas las tablas si no existen
# ═══════════════════════════════════════════════════════════════

def inicializar_db():
    """Crea la estructura completa de la base de datos."""
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        -- Clima diario
        CREATE TABLE IF NOT EXISTS clima (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT NOT NULL UNIQUE,
            tipo        TEXT NOT NULL,  -- 'seco', 'sereno', 'lluvia_fuerte'
            descripcion TEXT,
            registrado_por TEXT,
            timestamp   TEXT DEFAULT (datetime('now'))
        );

        -- Asistencia del personal fijo
        CREATE TABLE IF NOT EXISTS asistencia (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha           TEXT NOT NULL,
            personal_id     INTEGER NOT NULL,
            presente        INTEGER NOT NULL,  -- 1 = sí, 0 = no
            hora_entrada    TEXT DEFAULT '06:00',
            hora_salida     TEXT DEFAULT '15:00',
            motivo_ausencia TEXT DEFAULT '',
            notas           TEXT DEFAULT '',
            timestamp       TEXT DEFAULT (datetime('now')),
            UNIQUE(fecha, personal_id)
        );

        -- Rotación de lotes
        CREATE TABLE IF NOT EXISTS rotacion_lotes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT NOT NULL,
            lote_anterior INTEGER,
            lote_nuevo    INTEGER NOT NULL,
            animales      INTEGER DEFAULT 106,
            notas         TEXT DEFAULT '',
            timestamp     TEXT DEFAULT (datetime('now'))
        );

        -- Actividades de la finca (jornales, cercas, etc.)
        CREATE TABLE IF NOT EXISTS actividades (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT NOT NULL,
            tipo          TEXT NOT NULL,  -- 'jornal', 'cercas', 'tractor', 'rotacion', 'sanitario', 'manejo'
            descripcion   TEXT,
            lote          INTEGER,
            responsable   TEXT,
            tipo_contrato TEXT DEFAULT 'jornal',  -- 'fijo', 'jornal'
            completada    INTEGER DEFAULT 1,
            notas         TEXT DEFAULT '',
            timestamp     TEXT DEFAULT (datetime('now'))
        );

        -- Actividades sanitarias
        CREATE TABLE IF NOT EXISTS sanitario (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha          TEXT NOT NULL,
            tipo           TEXT NOT NULL,  -- 'vacunacion', 'purga', 'vitamina', 'marcacion'
            lote_animales  TEXT,           -- 'Octubre 2025', 'Enero 2026', 'todos'
            cantidad       INTEGER DEFAULT 0,
            producto       TEXT DEFAULT '',
            responsable    TEXT DEFAULT 'Adriana Bastidas',
            notas          TEXT DEFAULT '',
            timestamp      TEXT DEFAULT (datetime('now'))
        );

        -- Jornales contratados
        CREATE TABLE IF NOT EXISTS jornales (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT NOT NULL,
            tipo        TEXT NOT NULL,
            lote        TEXT,
            cantidad    INTEGER DEFAULT 1,
            responsable TEXT DEFAULT 'Jornalero',
            notas       TEXT DEFAULT '',
            timestamp   TEXT DEFAULT (datetime('now'))
        );

        -- Configuración general (lote actual, total animales, etc.)
        CREATE TABLE IF NOT EXISTS config (
            parametro   TEXT PRIMARY KEY,
            valor       TEXT NOT NULL,
            timestamp   TEXT DEFAULT (datetime('now'))
        );

        -- Facturas de venta
        CREATE TABLE IF NOT EXISTS facturas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_factura  TEXT NOT NULL,
            fecha           TEXT NOT NULL,
            cliente         TEXT NOT NULL,
            descripcion     TEXT,
            cantidad        REAL,
            valor_unitario  REAL,
            valor_total     REAL NOT NULL,
            metodo_pago     TEXT DEFAULT '',
            notas           TEXT DEFAULT '',
            archivo_path    TEXT DEFAULT '',
            nombre_archivo  TEXT DEFAULT '',
            timestamp       TEXT DEFAULT (datetime('now'))
        );

        -- Pagos de seguridad social
        CREATE TABLE IF NOT EXISTS pagos_seguridad_social (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            anio            INTEGER NOT NULL,
            mes             INTEGER NOT NULL,
            tipo            TEXT NOT NULL,   -- 'propia' o 'empleados'
            archivo_path    TEXT DEFAULT '',
            nombre_archivo  TEXT DEFAULT '',
            timestamp       TEXT DEFAULT (datetime('now')),
            UNIQUE(anio, mes, tipo)
        );

        -- Finanzas personales / finca
        CREATE TABLE IF NOT EXISTS finanzas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT NOT NULL,
            detalle     TEXT NOT NULL,
            ingreso     REAL DEFAULT 0,   -- Col C: plata que entra
            prestamo    REAL DEFAULT 0,   -- Col D: préstamos recibidos
            gasto       REAL DEFAULT 0,   -- Col E: plata que sale
            tipo        TEXT NOT NULL,    -- 'ingreso','prestamo_recibido','gasto'
            categoria   TEXT DEFAULT 'otro',
            forma_pago  TEXT DEFAULT '',
            notas       TEXT DEFAULT '',
            fuente      TEXT DEFAULT 'manual',  -- 'historico' o 'manual'
            synced_sheets INTEGER DEFAULT 0,
            orden_original INTEGER,       -- fila original del CSV para preservar orden
            timestamp   TEXT DEFAULT (datetime('now'))
        );

        -- Comprobantes de nómina (quincenas)
        CREATE TABLE IF NOT EXISTS comprobantes_nomina (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            anio            INTEGER NOT NULL,
            mes             INTEGER NOT NULL,
            quincena        INTEGER NOT NULL,   -- 1 o 2
            personal_id     INTEGER NOT NULL,
            archivo_path    TEXT DEFAULT '',
            nombre_archivo  TEXT DEFAULT '',
            timestamp       TEXT DEFAULT (datetime('now')),
            UNIQUE(anio, mes, quincena, personal_id)
        );

        -- Pagos realizados (botones verde/rojo de quincenas)
        CREATE TABLE IF NOT EXISTS pagos_realizados (
            clave       TEXT PRIMARY KEY,
            pagado      INTEGER DEFAULT 1,
            fecha       TEXT,
            timestamp   TEXT DEFAULT (datetime('now'))
        );

        -- Historial de pagos (registros financieros por quincena)
        CREATE TABLE IF NOT EXISTS historial_pagos (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha               TEXT,
            quincena            TEXT,
            tipo                TEXT,
            personal_id         INTEGER,
            beneficiario        TEXT,
            total_devengado     REAL DEFAULT 0,
            total_deducciones   REAL DEFAULT 0,
            total_pagado        REAL DEFAULT 0,
            metodo_pago         TEXT DEFAULT 'transferencia',
            referencia          TEXT DEFAULT '',
            notas               TEXT DEFAULT '',
            indice_comprobante  INTEGER,
            archivo_path        TEXT DEFAULT '',
            timestamp           TEXT DEFAULT (datetime('now')),
            UNIQUE(quincena, tipo, personal_id, indice_comprobante)
        );

        -- Historial diario de lote ocupado por los animales
        CREATE TABLE IF NOT EXISTS dias_en_lote (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha            TEXT NOT NULL UNIQUE,
            lote             INTEGER NOT NULL,
            dia_en_rotacion  INTEGER NOT NULL,
            rotacion_id      INTEGER REFERENCES rotacion_lotes(id),
            timestamp        TEXT DEFAULT (datetime('now'))
        );

        -- Movimientos de cuadra (pastoreo regenerativo)
        CREATE TABLE IF NOT EXISTS movimientos_cuadra (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha        TEXT NOT NULL,
            lote         INTEGER NOT NULL,
            cuadra_nueva INTEGER NOT NULL,
            animales     INTEGER DEFAULT 106,
            notas        TEXT DEFAULT '',
            timestamp    TEXT DEFAULT (datetime('now'))
        );

        -- Documentos adjuntos a movimientos de finanzas
        CREATE TABLE IF NOT EXISTS finanzas_docs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            finanza_id  INTEGER NOT NULL REFERENCES finanzas(id) ON DELETE CASCADE,
            archivo_path TEXT NOT NULL,
            nombre_archivo TEXT NOT NULL,
            tipo        TEXT DEFAULT 'comprobante',  -- comprobante, factura, otro
            timestamp   TEXT DEFAULT (datetime('now'))
        );

        -- Valores iniciales de configuración
        INSERT OR IGNORE INTO config (parametro, valor) VALUES
            ('lote_actual',        '3'),
            ('fecha_entrada_lote', '2026-03-14'),
            ('total_animales',     '106');
    """)

    conn.commit()

    # Migraciones: agregar columnas nuevas si no existen
    for sql in [
        "ALTER TABLE finanzas ADD COLUMN factura_id INTEGER",
        "ALTER TABLE rotacion_lotes ADD COLUMN fecha_salida TEXT",
        "ALTER TABLE rotacion_lotes ADD COLUMN dias_total INTEGER",
        "ALTER TABLE rotacion_lotes ADD COLUMN numero_rotacion INTEGER",
        "ALTER TABLE clima ADD COLUMN luz INTEGER DEFAULT 1",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass  # La columna ya existe

    conn.close()
    print(f"✓ Base de datos lista: {DB_PATH}")


# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

def get_config(parametro: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT valor FROM config WHERE parametro = ?", (parametro,)
        ).fetchone()
        return row['valor'] if row else None


def set_config(parametro: str, valor):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO config (parametro, valor) VALUES (?, ?)",
            (parametro, str(valor))
        )


def get_lote_actual() -> int:
    return int(get_config('lote_actual') or 3)


def get_total_animales() -> int:
    return int(get_config('total_animales') or 106)


# ═══════════════════════════════════════════════════════════════
# CLIMA
# ═══════════════════════════════════════════════════════════════

def guardar_clima(fecha: str, tipo: str, descripcion: str, registrado_por: str = 'Adriana', luz: int = 1):
    """Guarda o actualiza el clima de un día."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO clima (fecha, tipo, descripcion, registrado_por, luz)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(fecha) DO UPDATE SET
                tipo = excluded.tipo,
                descripcion = excluded.descripcion,
                registrado_por = excluded.registrado_por,
                luz = excluded.luz,
                timestamp = datetime('now')
        """, (fecha, tipo, descripcion, registrado_por, luz))
    return True


def get_clima(fecha: str = None):
    with get_conn() as conn:
        if fecha:
            row = conn.execute(
                "SELECT * FROM clima WHERE fecha = ?", (fecha,)
            ).fetchone()
            return dict(row) if row else None
        return [dict(r) for r in conn.execute(
            "SELECT * FROM clima ORDER BY fecha DESC"
        ).fetchall()]


# ═══════════════════════════════════════════════════════════════
# ASISTENCIA
# ═══════════════════════════════════════════════════════════════

def guardar_asistencia(fecha: str, personal_id: int, presente: bool,
                       hora_entrada: str = '06:00', hora_salida: str = '15:00',
                       motivo_ausencia: str = '', notas: str = ''):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO asistencia
                (fecha, personal_id, presente, hora_entrada, hora_salida, motivo_ausencia, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fecha, personal_id) DO UPDATE SET
                presente        = excluded.presente,
                hora_entrada    = excluded.hora_entrada,
                hora_salida     = excluded.hora_salida,
                motivo_ausencia = excluded.motivo_ausencia,
                notas           = excluded.notas,
                timestamp       = datetime('now')
        """, (fecha, personal_id, 1 if presente else 0,
              hora_entrada if presente else '',
              hora_salida if presente else '',
              '' if presente else motivo_ausencia,
              notas))
    return True


def get_asistencia(fecha: str = None, desde: str = None, hasta: str = None):
    with get_conn() as conn:
        if fecha:
            rows = conn.execute(
                "SELECT * FROM asistencia WHERE fecha = ? ORDER BY personal_id", (fecha,)
            ).fetchall()
        elif desde and hasta:
            rows = conn.execute(
                "SELECT * FROM asistencia WHERE fecha BETWEEN ? AND ? ORDER BY fecha, personal_id",
                (desde, hasta)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM asistencia ORDER BY fecha DESC, personal_id"
            ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# ROTACIÓN DE LOTES
# ═══════════════════════════════════════════════════════════════

def guardar_rotacion(fecha: str, lote_anterior: int, lote_nuevo: int,
                     animales: int = None, notas: str = ''):
    animales = animales or get_total_animales()
    with get_conn() as conn:
        # Cerrar la rotación anterior abierta (si existe)
        conn.execute("""
            UPDATE rotacion_lotes
            SET fecha_salida = ?,
                dias_total = CAST(julianday(?) - julianday(fecha) AS INTEGER) + 1
            WHERE lote_nuevo = ? AND fecha_salida IS NULL
        """, (fecha, fecha, lote_anterior))

        # Calcular cuántas veces han estado en lote_nuevo (para numero_rotacion)
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM rotacion_lotes WHERE lote_nuevo = ?",
            (lote_nuevo,)
        ).fetchone()
        numero_rotacion = (row['cnt'] if row else 0) + 1

        conn.execute("""
            INSERT INTO rotacion_lotes (fecha, lote_anterior, lote_nuevo, animales, notas, numero_rotacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (fecha, lote_anterior, lote_nuevo, animales, notas, numero_rotacion))

    # Actualizar configuración
    set_config('lote_actual', lote_nuevo)
    set_config('fecha_entrada_lote', fecha)
    return True


def registrar_dia_en_lote(fecha: str):
    """Registra diariamente en qué lote están los animales y qué día de la rotación es."""
    from datetime import date as _date
    lote = get_lote_actual()
    fecha_entrada = get_config('fecha_entrada_lote') or fecha
    dia_en_rotacion = (_date.fromisoformat(fecha) - _date.fromisoformat(fecha_entrada)).days + 1

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM rotacion_lotes WHERE lote_nuevo = ? AND fecha_salida IS NULL ORDER BY fecha DESC LIMIT 1",
            (lote,)
        ).fetchone()
        rotacion_id = row['id'] if row else None

        conn.execute("""
            INSERT OR REPLACE INTO dias_en_lote (fecha, lote, dia_en_rotacion, rotacion_id)
            VALUES (?, ?, ?, ?)
        """, (fecha, lote, dia_en_rotacion, rotacion_id))


def get_rotaciones():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM rotacion_lotes ORDER BY fecha DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# ACTIVIDADES
# ═══════════════════════════════════════════════════════════════

def guardar_actividad(fecha: str, tipo: str, descripcion: str,
                      lote: int = None, responsable: str = '',
                      tipo_contrato: str = 'fijo', notas: str = ''):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO actividades
                (fecha, tipo, descripcion, lote, responsable, tipo_contrato, completada, notas)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (fecha, tipo, descripcion, lote, responsable, tipo_contrato, notas))
    return True


def get_actividades(fecha: str = None, desde: str = None, hasta: str = None):
    with get_conn() as conn:
        if fecha:
            rows = conn.execute(
                "SELECT * FROM actividades WHERE fecha = ? ORDER BY id", (fecha,)
            ).fetchall()
        elif desde and hasta:
            rows = conn.execute(
                "SELECT * FROM actividades WHERE fecha BETWEEN ? AND ? ORDER BY fecha, id",
                (desde, hasta)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM actividades ORDER BY fecha DESC, id DESC"
            ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# JORNALES
# ═══════════════════════════════════════════════════════════════

def guardar_jornal(fecha: str, tipo: str, lote: str, cantidad: int = 1,
                   responsable: str = 'Jornalero', notas: str = ''):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO jornales (fecha, tipo, lote, cantidad, responsable, notas)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (fecha, tipo, str(lote), cantidad, responsable, notas))
    return True


def get_jornales(desde: str = None, hasta: str = None):
    with get_conn() as conn:
        if desde and hasta:
            rows = conn.execute(
                "SELECT * FROM jornales WHERE fecha BETWEEN ? AND ? ORDER BY fecha",
                (desde, hasta)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jornales ORDER BY fecha DESC"
            ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# SANITARIO
# ═══════════════════════════════════════════════════════════════

def guardar_sanitario(fecha: str, tipo: str, lote_animales: str,
                      cantidad: int = 0, producto: str = '',
                      responsable: str = 'Adriana Bastidas', notas: str = ''):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO sanitario
                (fecha, tipo, lote_animales, cantidad, producto, responsable, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (fecha, tipo, lote_animales, cantidad, producto, responsable, notas))
    return True


def get_sanitario(desde: str = None, hasta: str = None):
    with get_conn() as conn:
        if desde and hasta:
            rows = conn.execute(
                "SELECT * FROM sanitario WHERE fecha BETWEEN ? AND ? ORDER BY fecha",
                (desde, hasta)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sanitario ORDER BY fecha DESC").fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# FACTURAS
# ═══════════════════════════════════════════════════════════════

def guardar_factura(numero_factura: str, fecha: str, cliente: str, descripcion: str,
                    valor_total: float, cantidad: float = None, valor_unitario: float = None,
                    metodo_pago: str = '', notas: str = '',
                    archivo_path: str = '', nombre_archivo: str = ''):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO facturas
                (numero_factura, fecha, cliente, descripcion, cantidad, valor_unitario,
                 valor_total, metodo_pago, notas, archivo_path, nombre_archivo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (numero_factura, fecha, cliente, descripcion, cantidad, valor_unitario,
              valor_total, metodo_pago, notas, archivo_path, nombre_archivo))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def actualizar_factura_archivo(factura_id: int, archivo_path: str, nombre_archivo: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE facturas SET archivo_path=?, nombre_archivo=? WHERE id=?",
            (archivo_path, nombre_archivo, factura_id)
        )


def eliminar_factura(factura_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM facturas WHERE id=?", (factura_id,))


def get_facturas():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM facturas ORDER BY fecha DESC, id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# SEGURIDAD SOCIAL
# ═══════════════════════════════════════════════════════════════

def guardar_pago_seguridad(anio: int, mes: int, tipo: str,
                           archivo_path: str, nombre_archivo: str):
    """tipo = 'propia' o 'empleados'"""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO pagos_seguridad_social (anio, mes, tipo, archivo_path, nombre_archivo)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(anio, mes, tipo) DO UPDATE SET
                archivo_path   = excluded.archivo_path,
                nombre_archivo = excluded.nombre_archivo,
                timestamp      = datetime('now')
        """, (anio, mes, tipo, archivo_path, nombre_archivo))


def get_pagos_seguridad(anio: int = None):
    with get_conn() as conn:
        if anio:
            rows = conn.execute(
                "SELECT * FROM pagos_seguridad_social WHERE anio=? ORDER BY mes, tipo",
                (anio,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pagos_seguridad_social ORDER BY anio DESC, mes, tipo"
            ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# COMPROBANTES DE NÓMINA
# ═══════════════════════════════════════════════════════════════

def guardar_comprobante_nomina(anio: int, mes: int, quincena: int, personal_id: int,
                               archivo_path: str, nombre_archivo: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO comprobantes_nomina
                (anio, mes, quincena, personal_id, archivo_path, nombre_archivo)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(anio, mes, quincena, personal_id) DO UPDATE SET
                archivo_path   = excluded.archivo_path,
                nombre_archivo = excluded.nombre_archivo,
                timestamp      = datetime('now')
        """, (anio, mes, quincena, personal_id, archivo_path, nombre_archivo))


def get_comprobantes_nomina(anio: int = None, mes: int = None):
    with get_conn() as conn:
        if anio and mes:
            rows = conn.execute(
                "SELECT * FROM comprobantes_nomina WHERE anio=? AND mes=? ORDER BY quincena, personal_id",
                (anio, mes)
            ).fetchall()
        elif anio:
            rows = conn.execute(
                "SELECT * FROM comprobantes_nomina WHERE anio=? ORDER BY mes, quincena, personal_id",
                (anio,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM comprobantes_nomina ORDER BY anio DESC, mes, quincena, personal_id"
            ).fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# PAGOS REALIZADOS
# ═══════════════════════════════════════════════════════════════

def get_pagos_realizados():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM pagos_realizados").fetchall()
        return {r['clave']: {'pagado': bool(r['pagado']), 'fecha': r['fecha']} for r in rows}

def guardar_pago_realizado(clave: str, fecha: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO pagos_realizados (clave, pagado, fecha)
            VALUES (?, 1, ?)
            ON CONFLICT(clave) DO UPDATE SET pagado=1, fecha=excluded.fecha, timestamp=datetime('now')
        """, (clave, fecha))

def eliminar_pago_realizado(clave: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM pagos_realizados WHERE clave=?", (clave,))

def seed_pagos_defecto(pagos: dict):
    """Inserta pagos por defecto solo si no existen ya."""
    with get_conn() as conn:
        for clave, info in pagos.items():
            conn.execute("""
                INSERT OR IGNORE INTO pagos_realizados (clave, pagado, fecha)
                VALUES (?, 1, ?)
            """, (clave, info.get('fecha', '')))


# ═══════════════════════════════════════════════════════════════
# HISTORIAL DE PAGOS
# ═══════════════════════════════════════════════════════════════

def get_historial_pagos():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM historial_pagos ORDER BY fecha DESC, id DESC").fetchall()
        return [dict(r) for r in rows]

def guardar_historial_pago(fecha: str, quincena: str, tipo: str, personal_id,
                           beneficiario: str, total_devengado: float,
                           total_deducciones: float, total_pagado: float,
                           metodo_pago: str = 'transferencia', referencia: str = '',
                           notas: str = '', indice_comprobante=None, archivo_path: str = ''):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO historial_pagos
                (fecha, quincena, tipo, personal_id, beneficiario,
                 total_devengado, total_deducciones, total_pagado,
                 metodo_pago, referencia, notas, indice_comprobante, archivo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(quincena, tipo, personal_id, indice_comprobante) DO UPDATE SET
                fecha=excluded.fecha, beneficiario=excluded.beneficiario,
                total_devengado=excluded.total_devengado, total_deducciones=excluded.total_deducciones,
                total_pagado=excluded.total_pagado, archivo_path=excluded.archivo_path,
                timestamp=datetime('now')
        """, (fecha, quincena, tipo, personal_id, beneficiario,
              total_devengado, total_deducciones, total_pagado,
              metodo_pago, referencia, notas, indice_comprobante, archivo_path))

def eliminar_historial_quincena(quincena: str, tipo: str = None):
    with get_conn() as conn:
        if tipo:
            conn.execute("DELETE FROM historial_pagos WHERE quincena=? AND tipo=?", (quincena, tipo))
        else:
            conn.execute("DELETE FROM historial_pagos WHERE quincena=?", (quincena,))

def actualizar_historial_archivo(historial_id: int, archivo_path: str):
    with get_conn() as conn:
        conn.execute("UPDATE historial_pagos SET archivo_path=? WHERE id=?", (archivo_path, historial_id))


# ═══════════════════════════════════════════════════════════════
# MOVIMIENTOS DE CUADRA
# ═══════════════════════════════════════════════════════════════

def guardar_movimiento_cuadra(fecha: str, lote: int, cuadra_nueva: int,
                               animales: int = None, notas: str = ''):
    animales = animales or get_total_animales()
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO movimientos_cuadra (fecha, lote, cuadra_nueva, animales, notas)
            VALUES (?, ?, ?, ?, ?)
        """, (fecha, lote, cuadra_nueva, animales, notas))
    return True


def get_movimientos_cuadra(lote: int = None):
    with get_conn() as conn:
        if lote:
            rows = conn.execute(
                "SELECT * FROM movimientos_cuadra WHERE lote = ? ORDER BY fecha, id",
                (lote,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM movimientos_cuadra ORDER BY fecha, id"
            ).fetchall()
        return [dict(r) for r in rows]


def get_cuadra_actual(lote: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT cuadra_nueva FROM movimientos_cuadra WHERE lote = ? ORDER BY fecha DESC, id DESC LIMIT 1",
            (lote,)
        ).fetchone()
        return row['cuadra_nueva'] if row else 1


# ═══════════════════════════════════════════════════════════════
# EXPORTAR — datos completos para el dashboard
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# FINANZAS
# ═══════════════════════════════════════════════════════════════

def get_finanzas(anio=None, mes=None, tipo=None, categoria=None, forma_pago=None, busqueda=None):
    with get_conn() as conn:
        # Window function computes global running saldo chronologically,
        # then we filter and return newest-first.
        cte = """
            WITH base AS (
                SELECT *,
                    SUM(ingreso + prestamo - gasto)
                        OVER (ORDER BY orden_original, id
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS saldo_acumulado
                FROM finanzas
            )
            SELECT * FROM base WHERE 1=1
        """
        params = []
        if anio:
            cte += " AND substr(fecha,1,4) = ?"
            params.append(str(anio))
        if mes:
            cte += " AND substr(fecha,6,2) = ?"
            params.append(f"{int(mes):02d}")
        if tipo:
            cte += " AND tipo = ?"
            params.append(tipo)
        if categoria:
            cte += " AND categoria = ?"
            params.append(categoria)
        if forma_pago:
            cte += " AND forma_pago = ?"
            params.append(forma_pago)
        if busqueda:
            cte += " AND (detalle LIKE ? OR notas LIKE ? OR categoria LIKE ?)"
            b = f"%{busqueda}%"
            params.extend([b, b, b])
        cte += " ORDER BY orden_original DESC, id DESC"
        rows = conn.execute(cte, params).fetchall()
    return [dict(r) for r in rows]


def guardar_finanza(fecha, detalle, ingreso=0.0, prestamo=0.0, gasto=0.0,
                    tipo='gasto', categoria='otro', forma_pago='', notas='', factura_id=None):
    with get_conn() as conn:
        max_orden = conn.execute(
            "SELECT COALESCE(MAX(orden_original), 0) FROM finanzas"
        ).fetchone()[0]
        conn.execute("""
            INSERT INTO finanzas
                (fecha, detalle, ingreso, prestamo, gasto, tipo,
                 categoria, forma_pago, notas, fuente, synced_sheets, orden_original, factura_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual', 0, ?, ?)
        """, (fecha, detalle, ingreso, prestamo, gasto, tipo,
              categoria, forma_pago, notas, max_orden + 1, factura_id))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def eliminar_finanza(finanza_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM finanzas WHERE id = ?", (finanza_id,))


def actualizar_finanza(finanza_id, fecha, detalle, ingreso=0.0, prestamo=0.0, gasto=0.0,
                       tipo='gasto', categoria='otro', forma_pago='', notas=''):
    with get_conn() as conn:
        conn.execute("""
            UPDATE finanzas SET fecha=?, detalle=?, ingreso=?, prestamo=?, gasto=?,
            tipo=?, categoria=?, forma_pago=?, notas=?
            WHERE id=?
        """, (fecha, detalle, ingreso, prestamo, gasto, tipo, categoria, forma_pago, notas, finanza_id))


def get_finanzas_resumen(anio=None):
    """Totales por tipo para las tarjetas KPI."""
    with get_conn() as conn:
        q = "SELECT SUM(ingreso) as tot_ingreso, SUM(prestamo) as tot_prestamo, SUM(gasto) as tot_gasto FROM finanzas WHERE 1=1"
        params = []
        if anio:
            q += " AND substr(fecha,1,4) = ?"
            params.append(str(anio))
        row = conn.execute(q, params).fetchone()
    return {
        'totalIngresos':  row['tot_ingreso']  or 0,
        'totalPrestamos': row['tot_prestamo'] or 0,
        'totalGastos':    row['tot_gasto']    or 0,
        'saldoActual':    (row['tot_ingreso'] or 0) + (row['tot_prestamo'] or 0) - (row['tot_gasto'] or 0),
    }


def get_informe_mensual(anio: int, mes: int) -> dict:
    """Informe financiero completo de un mes con comparativa y acumulado anual."""
    anio_str = str(anio)
    mes_str  = f"{mes:02d}"
    fecha_ini = f"{anio}-{mes_str}-01"

    with get_conn() as conn:
        # ─── Resumen del mes ──────────────────────────────────────────────────
        mr = conn.execute("""
            SELECT COALESCE(SUM(ingreso),0) tot_i,
                   COALESCE(SUM(prestamo),0) tot_p,
                   COALESCE(SUM(gasto),0)   tot_g,
                   COUNT(*) num_tx
            FROM finanzas
            WHERE substr(fecha,1,4)=? AND substr(fecha,6,2)=?
        """, (anio_str, mes_str)).fetchone()
        tot_i, tot_p, tot_g = mr['tot_i'], mr['tot_p'], mr['tot_g']

        # ─── Saldo al inicio del mes (acumulado de todo lo anterior) ─────────
        sr = conn.execute("""
            SELECT COALESCE(SUM(ingreso + prestamo - gasto), 0) saldo
            FROM finanzas WHERE fecha < ?
        """, (fecha_ini,)).fetchone()
        saldo_inicio = sr['saldo']
        saldo_fin    = saldo_inicio + tot_i + tot_p - tot_g

        # ─── Gastos por categoría ─────────────────────────────────────────────
        cat_rows = conn.execute("""
            SELECT categoria,
                   COALESCE(SUM(gasto),0)   tot_gasto,
                   COALESCE(SUM(ingreso),0) tot_ingreso,
                   COUNT(*) num_tx
            FROM finanzas
            WHERE substr(fecha,1,4)=? AND substr(fecha,6,2)=?
            GROUP BY categoria
            ORDER BY tot_gasto DESC
        """, (anio_str, mes_str)).fetchall()

        # ─── Top 5 gastos individuales ────────────────────────────────────────
        top_g = conn.execute("""
            SELECT fecha, detalle, gasto, categoria
            FROM finanzas
            WHERE substr(fecha,1,4)=? AND substr(fecha,6,2)=? AND gasto > 0
            ORDER BY gasto DESC LIMIT 5
        """, (anio_str, mes_str)).fetchall()

        # ─── Top 5 ingresos individuales ─────────────────────────────────────
        top_i = conn.execute("""
            SELECT fecha, detalle, ingreso, prestamo
            FROM finanzas
            WHERE substr(fecha,1,4)=? AND substr(fecha,6,2)=? AND (ingreso>0 OR prestamo>0)
            ORDER BY (ingreso + prestamo) DESC LIMIT 5
        """, (anio_str, mes_str)).fetchall()

        # ─── Acumulado año hasta este mes ────────────────────────────────────
        yr = conn.execute("""
            SELECT COALESCE(SUM(ingreso),0) tot_i,
                   COALESCE(SUM(prestamo),0) tot_p,
                   COALESCE(SUM(gasto),0) tot_g
            FROM finanzas
            WHERE substr(fecha,1,4)=? AND substr(fecha,6,2)<=?
        """, (anio_str, mes_str)).fetchone()

        # ─── Mes anterior (comparativa) ───────────────────────────────────────
        if mes == 1:
            ma_str, ya_str = '12', str(anio - 1)
        else:
            ma_str, ya_str = f"{mes-1:02d}", anio_str
        ar = conn.execute("""
            SELECT COALESCE(SUM(ingreso),0) tot_i, COALESCE(SUM(gasto),0) tot_g
            FROM finanzas WHERE substr(fecha,1,4)=? AND substr(fecha,6,2)=?
        """, (ya_str, ma_str)).fetchone()

        # ─── Resumen mes a mes del año (para gráfica) ─────────────────────────
        meses_yr = conn.execute("""
            SELECT substr(fecha,6,2) mes,
                   COALESCE(SUM(ingreso),0) tot_i,
                   COALESCE(SUM(prestamo),0) tot_p,
                   COALESCE(SUM(gasto),0) tot_g
            FROM finanzas WHERE substr(fecha,1,4)=?
            GROUP BY substr(fecha,6,2) ORDER BY mes
        """, (anio_str,)).fetchall()

    return {
        'anio': anio,
        'mes': mes,
        'resumen': {
            'ingresos':          tot_i,
            'prestamos':         tot_p,
            'gastos':            tot_g,
            'neto':              tot_i + tot_p - tot_g,
            'num_transacciones': mr['num_tx'],
            'saldo_inicio':      saldo_inicio,
            'saldo_fin':         saldo_fin,
        },
        'categorias':   [dict(r) for r in cat_rows],
        'top_gastos':   [dict(r) for r in top_g],
        'top_ingresos': [dict(r) for r in top_i],
        'acumulado_anio': {
            'ingresos':  yr['tot_i'],
            'prestamos': yr['tot_p'],
            'gastos':    yr['tot_g'],
            'neto':      yr['tot_i'] + yr['tot_p'] - yr['tot_g'],
        },
        'vs_mes_anterior': {
            'ingresos_anterior': ar['tot_i'],
            'gastos_anterior':   ar['tot_g'],
            'delta_ingresos':    tot_i - ar['tot_i'],
            'delta_gastos':      tot_g - ar['tot_g'],
        },
        'meses_anio': [dict(r) for r in meses_yr],
    }


def get_finanzas_docs(finanza_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM finanzas_docs WHERE finanza_id = ? ORDER BY id ASC",
            (finanza_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def guardar_finanza_doc(finanza_id, archivo_path, nombre_archivo, tipo='comprobante'):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO finanzas_docs (finanza_id, archivo_path, nombre_archivo, tipo)
            VALUES (?, ?, ?, ?)
        """, (finanza_id, archivo_path, nombre_archivo, tipo))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def eliminar_finanza_doc(doc_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT archivo_path FROM finanzas_docs WHERE id = ?", (doc_id,)
        ).fetchone()
        conn.execute("DELETE FROM finanzas_docs WHERE id = ?", (doc_id,))
    return dict(row) if row else None


def borrar_reporte_fecha(fecha: str):
    """Elimina jornales, sanitario y actividades de una fecha para permitir re-ingreso."""
    with get_conn() as conn:
        conn.execute("DELETE FROM jornales WHERE fecha = ?", (fecha,))
        conn.execute("DELETE FROM sanitario WHERE fecha = ?", (fecha,))
        conn.execute("DELETE FROM actividades WHERE fecha = ?", (fecha,))
        # clima y asistencia usan upsert, se corrigen solos al re-guardar


def exportar_para_dashboard():
    return {
        'config': {
            'lote_actual':        get_lote_actual(),
            'fecha_entrada_lote': get_config('fecha_entrada_lote'),
            'total_animales':     get_total_animales(),
        },
        'clima':      get_clima(),
        'asistencia': get_asistencia(),
        'rotaciones': get_rotaciones(),
        'actividades': get_actividades(),
        'jornales':   get_jornales(),
        'sanitario':  get_sanitario(),
    }


if __name__ == '__main__':
    inicializar_db()
    print("Lote actual:", get_lote_actual())
    print("Total animales:", get_total_animales())
