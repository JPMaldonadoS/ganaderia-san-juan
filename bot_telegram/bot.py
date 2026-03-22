"""
Bot de Telegram para Ganadería San Juan
Cuestionario diario a las 4pm → guarda en SQLite → actualiza el dashboard
"""
import logging
import asyncio
from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import db_handler as db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ZONA_COLOMBIA = ZoneInfo("America/Bogota")

# ─── Estados del cuestionario ────────────────────────────────────────────────
(
    Q_CLIMA,
    Q_LUZ,
    Q_ADRIANA_TRABAJO,
    Q_ADRIANA_MOTIVO,
    Q_GEORGE_TRABAJO,
    Q_GEORGE_MOTIVO,
    Q_LOTE,
    Q_CUADRA,
    Q_JORNALES,
    Q_JORNALES_TIPO,
    Q_JORNALES_LOTE,
    Q_NOVEDAD,
    Q_VAC_PRODUCTO,
    Q_VAC_LOTE,
    Q_ENFERMO_DESC,
    Q_CONFIRMAR,
    Q_FECHA,
) = range(17)

# Datos temporales mientras dura el cuestionario
sesion = {}

# Chat IDs autorizados (Adriana + dueño)
AUTORIZADOS = {config.ADRIANA_CHAT_ID, config.OWNER_CHAT_ID}


async def _no_autorizado(update: Update):
    await update.effective_message.reply_text(
        "⛔ No tienes permiso para usar este bot."
    )


def autorizado(update: Update) -> bool:
    return update.effective_chat.id in AUTORIZADOS


def es_domingo(fecha: datetime = None) -> bool:
    f = fecha or datetime.now(ZONA_COLOMBIA)
    return f.weekday() == 6  # 6 = domingo


def teclado(opciones: list[tuple]) -> InlineKeyboardMarkup:
    """Crea teclado inline. opciones = [(texto, callback_data), ...]"""
    filas = []
    fila = []
    for i, (texto, dato) in enumerate(opciones):
        fila.append(InlineKeyboardButton(texto, callback_data=dato))
        if len(fila) == 2 or i == len(opciones) - 1:
            filas.append(fila)
            fila = []
    return InlineKeyboardMarkup(filas)


# ─── /start ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return await _no_autorizado(update)
    chat_id = update.effective_chat.id
    nombre = update.effective_user.first_name
    await update.message.reply_text(
        f"🐄 *Hola {nombre}!* Soy el bot de Ganadería San Juan.\n\n"
        f"Tu Chat ID es: `{chat_id}`\n\n"
        "Comparte ese número con Juan Pablo para activar el reporte diario.\n\n"
        "Comandos:\n"
        "/reporte — Iniciar reporte ahora\n"
        "/estado — Ver estado actual\n"
        "/ayuda — Ayuda",
        parse_mode='Markdown'
    )


# ─── /estado ─────────────────────────────────────────────────────────────────

async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return await _no_autorizado(update)
    lote = db.get_lote_actual()
    animales = db.get_total_animales()
    fecha_entrada = db.get_config('fecha_entrada_lote') or '-'
    hoy = datetime.now(ZONA_COLOMBIA).strftime('%Y-%m-%d')
    clima = db.get_clima(hoy)

    clima_txt = f"{clima['tipo']} — {clima['descripcion']}" if clima else "Sin registro hoy"

    await update.message.reply_text(
        f"📊 *Estado actual — Ganadería San Juan*\n\n"
        f"🐃 Animales: *{animales}*\n"
        f"📍 Lote actual: *Lote {lote}*\n"
        f"📅 En este lote desde: *{fecha_entrada}*\n"
        f"🌤 Clima hoy: *{clima_txt}*",
        parse_mode='Markdown'
    )


# ─── /ayuda ──────────────────────────────────────────────────────────────────

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return await _no_autorizado(update)
    await update.message.reply_text(
        "🐄 *Bot Ganadería San Juan — Ayuda*\n\n"
        "/reporte — Iniciar reporte diario\n"
        "/ver — Ver el reporte de hoy (o /ver 2026-03-16 para otra fecha)\n"
        "/corregir — Corregir un reporte ya enviado (hoy o ayer)\n"
        "/estado — Ver estado actual del ganado\n"
        "/start — Ver tu Chat ID\n\n"
        "El reporte diario llega automáticamente a las *4:00 PM*.\n"
        "Si no lo recibes, usa /reporte para iniciarlo manualmente.",
        parse_mode='Markdown'
    )


# ─── /ver ────────────────────────────────────────────────────────────────────

async def cmd_ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el reporte de hoy (o de la fecha indicada: /ver 2026-03-16)."""
    if not autorizado(update):
        return await _no_autorizado(update)

    args = context.args
    if args:
        fecha = args[0]
    else:
        fecha = datetime.now(ZONA_COLOMBIA).strftime('%Y-%m-%d')

    CLIMAS = {'seco': '☀️ Seco', 'sereno': '🌦 Llovizna', 'lluvia_fuerte': '⛈ Lluvia fuerte'}

    clima = db.get_clima(fecha)
    asistencia = db.get_asistencia(fecha=fecha)
    jornales = [j for j in db.get_jornales(desde=fecha, hasta=fecha)]
    sanitario = [s for s in db.get_sanitario(desde=fecha, hasta=fecha)]
    actividades = db.get_actividades(fecha=fecha)
    lote_actual = db.get_lote_actual()

    if not clima and not asistencia:
        await update.message.reply_text(
            f"📭 No hay reporte registrado para el *{fecha}*.\n"
            f"Usa /reporte para ingresarlo.",
            parse_mode='Markdown'
        )
        return

    # Clima
    clima_txt = CLIMAS.get(clima['tipo'], clima['tipo']) if clima else '—'

    # Asistencia
    def asist(personal_id):
        r = next((a for a in asistencia if a['personal_id'] == personal_id), None)
        if not r:
            return '—'
        return '✅ Trabajó' if r['presente'] else f"❌ No trabajó ({r.get('motivo_ausencia', '')})"

    # Lote
    rotacion = next((a for a in actividades if a.get('tipo') == 'rotacion'), None)
    lote_txt = f"🔄 Cambió a Lote {rotacion['lote']}" if rotacion else f"📍 Lote {lote_actual}"

    # Jornales
    if jornales:
        jornales_txt = '\n'.join(f"  • {j['tipo']} — Lote {j['lote']}" for j in jornales)
    else:
        jornales_txt = '  Sin jornales'

    # Sanitario
    san_txt = ''
    for s in sanitario:
        if s['tipo'] == 'vacunacion':
            san_txt += f"\n💉 Vacunación: {s['producto']} — {s['lote_animales']}"
        elif s['tipo'] == 'enfermedad':
            san_txt += f"\n🤒 Animal enfermo: {s['producto']}"
        else:
            san_txt += f"\n🩺 {s['tipo'].capitalize()}: {s['producto']}"

    # Novedad: se guarda en notas de George (asistencia) y como actividad 'manejo' con descripcion != 'Trabajo diario'
    george_row = next((a for a in asistencia if a['personal_id'] == 2), None)
    novedad_txt = (george_row.get('notas') or '').strip() if george_row else ''
    if not novedad_txt:
        nov_act = next((a for a in actividades if a.get('tipo') == 'manejo' and a.get('descripcion') != 'Trabajo diario'), None)
        novedad_txt = nov_act['descripcion'] if nov_act else ''
    if not novedad_txt:
        novedad_txt = 'Sin novedades'

    texto = (
        f"📋 *Reporte del {fecha}*\n\n"
        f"🌤 Clima: {clima_txt}\n"
        f"👩 Adriana: {asist(1)}\n"
        f"👨 George: {asist(2)}\n"
        f"🐃 {lote_txt}\n"
        f"👷 Jornales:\n{jornales_txt}\n"
        f"📝 Novedad: {novedad_txt}"
        f"{san_txt}"
    )

    await update.message.reply_text(texto, parse_mode='Markdown')


# ─── INICIO DEL CUESTIONARIO ─────────────────────────────────────────────────

async def iniciar_cuestionario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Punto de entrada: comando /reporte manual — pregunta primero la fecha."""
    if not autorizado(update):
        return await _no_autorizado(update)
    chat_id = update.effective_chat.id
    sesion[chat_id] = {}

    kb = teclado([
        ("📅 De hoy", "fecha_hoy"),
        ("⬅️ De ayer", "fecha_ayer"),
    ])
    await update.message.reply_text(
        "📋 *Reporte manual*\n\n"
        "*¿Este reporte es de hoy o de ayer?*\n"
        "_(Si no pudiste reportar a las 4pm, elige «De ayer»)_",
        reply_markup=kb,
        parse_mode='Markdown'
    )
    return Q_FECHA


async def cmd_corregir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borra el reporte existente de hoy o ayer y relanza el cuestionario."""
    if not autorizado(update):
        return await _no_autorizado(update)
    chat_id = update.effective_chat.id
    sesion[chat_id] = {'corrigiendo': True}

    kb = teclado([
        ("📅 Corregir hoy", "corregir_hoy"),
        ("⬅️ Corregir ayer", "corregir_ayer"),
    ])
    await update.message.reply_text(
        "✏️ *Corregir reporte*\n\n"
        "¿Qué reporte quieres corregir?\n"
        "_Se borrará el reporte existente y podrás ingresar uno nuevo._",
        reply_markup=kb,
        parse_mode='Markdown'
    )
    return Q_FECHA


async def q_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe respuesta de hoy/ayer (o corregir_hoy/corregir_ayer) y avanza al clima."""
    from datetime import timedelta
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    ahora = datetime.now(ZONA_COLOMBIA)
    corrigiendo = query.data in ('corregir_hoy', 'corregir_ayer')
    if query.data in ('fecha_ayer', 'corregir_ayer'):
        ahora = ahora - timedelta(days=1)

    fecha = ahora.strftime('%Y-%m-%d')

    if corrigiendo:
        db.borrar_reporte_fecha(fecha)
        await query.message.reply_text(
            f"🗑 Reporte del *{fecha}* borrado. Ingresa el nuevo reporte:",
            parse_mode='Markdown'
        )

    sesion[chat_id] = {
        'fecha': fecha,
        'domingo': ahora.weekday() == 6,
    }
    return await _preguntar_clima(query.message, fecha, sesion[chat_id]['domingo'])


async def iniciar_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Punto de entrada para el botón automático de las 4pm."""
    if not autorizado(update):
        return await _no_autorizado(update)
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    # sesion ya fue inicializada por enviar_cuestionario_automatico
    s = sesion.get(chat_id, {})
    fecha = s.get('fecha', datetime.now(ZONA_COLOMBIA).strftime('%Y-%m-%d'))
    domingo = s.get('domingo', datetime.now(ZONA_COLOMBIA).weekday() == 6)
    sesion[chat_id] = {'fecha': fecha, 'domingo': domingo}
    return await _preguntar_clima(query.message, fecha, domingo)


async def _preguntar_clima(message, fecha: str, domingo: bool):
    """Envía la pregunta de clima (paso 1)."""
    kb = teclado([
        ("☀️ Sin lluvia",     "clima_seco"),
        ("🌦 Llovizna",       "clima_sereno"),
        ("⛈ Lluvia fuerte",  "clima_lluvia_fuerte"),
    ])
    texto = (
        f"📋 *Reporte del {fecha}*\n"
        + ("_\\(Domingo — solo trabaja George\\)_\n" if domingo else "")
        + "\n☁️ *¿Cómo estuvo el clima hoy?*"
    )
    await message.reply_text(texto, reply_markup=kb, parse_mode='Markdown')
    return Q_CLIMA


async def enviar_cuestionario_automatico(context: ContextTypes.DEFAULT_TYPE):
    """Llamado por el scheduler a las 4pm — envía botón de inicio."""
    chat_id = config.ADRIANA_CHAT_ID
    if not chat_id:
        logger.warning("ADRIANA_CHAT_ID no configurado en .env")
        return

    hoy = datetime.now(ZONA_COLOMBIA).strftime('%Y-%m-%d')
    hoy_display = datetime.now(ZONA_COLOMBIA).strftime('%d/%m/%Y')
    sesion[chat_id] = {'fecha': hoy, 'domingo': es_domingo()}

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("▶️ Comenzar reporte", callback_data='iniciar_auto')
    ]])
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🐄 *Hola Adriana\\! Es hora del reporte — {hoy_display}*\n\n"
            "Son solo unas pregunticas, toca los botones para responder\\.\n\n"
            "_Si en algún momento te equivocas, escribe_ /corregir"
        ),
        reply_markup=kb,
        parse_mode='MarkdownV2'
    )


# ─── INFORME MENSUAL ─────────────────────────────────────────────────────────

async def enviar_informe_mensual(context):
    """Se llama el último día de cada mes a las 8pm. Envía resumen al dueño."""
    chat_id = config.OWNER_CHAT_ID or config.ADRIANA_CHAT_ID
    if not chat_id:
        return

    hoy   = datetime.now(ZONA_COLOMBIA)
    anio  = hoy.year
    mes   = hoy.month
    MESES = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
             'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

    inf = db.get_informe_mensual(anio, mes)
    r   = inf['resumen']
    ac  = inf['acumulado_anio']
    vs  = inf['vs_mes_anterior']

    def cop(n):
        return f"${n:,.0f}".replace(',', '.')

    # Categorías con más gasto
    top_cats = [c for c in inf['categorias'] if c['tot_gasto'] > 0][:5]
    cats_txt = '\n'.join(
        f"  • {c['categoria'].replace('_',' ').title()}: {cop(c['tot_gasto'])}"
        for c in top_cats
    ) or '  (sin gastos este mes)'

    # Top gastos individuales
    top_g_txt = '\n'.join(
        f"  {i+1}. {g['detalle'][:35]} — {cop(g['gasto'])}"
        for i, g in enumerate(inf['top_gastos'])
    ) or '  (ninguno)'

    # Flechas comparativa
    di = vs['delta_ingresos']
    dg = vs['delta_gastos']
    flecha_i = ('📈' if di >= 0 else '📉') + f" {cop(abs(di))} vs mes ant."
    flecha_g = ('📈' if dg >= 0 else '📉') + f" {cop(abs(dg))} vs mes ant."

    texto = (
        f"📊 *INFORME FINANCIERO — {MESES[mes]} {anio}*\n"
        f"{'─'*32}\n\n"
        f"💰 *MOVIMIENTOS DEL MES*\n"
        f"  Ingresos:   {cop(r['ingresos'])} {flecha_i}\n"
        f"  Préstamos:  {cop(r['prestamos'])}\n"
        f"  Gastos:     {cop(r['gastos'])} {flecha_g}\n"
        f"  Neto:       {cop(r['neto'])}\n\n"
        f"💳 *SALDOS*\n"
        f"  Al inicio del mes: {cop(r['saldo_inicio'])}\n"
        f"  Al cierre:         {cop(r['saldo_fin'])}\n\n"
        f"📋 *TOP CATEGORÍAS DE GASTO*\n{cats_txt}\n\n"
        f"🔴 *TOP GASTOS INDIVIDUALES*\n{top_g_txt}\n\n"
        f"📆 *ACUMULADO {anio} (ene–{MESES[mes][:3]})*\n"
        f"  Ingresos: {cop(ac['ingresos'])}\n"
        f"  Gastos:   {cop(ac['gastos'])}\n"
        f"  Neto:     {cop(ac['neto'])}\n\n"
        f"  Transacciones este mes: {r['num_transacciones']}"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=texto,
        parse_mode='Markdown'
    )


# ─── PASO 1: CLIMA ───────────────────────────────────────────────────────────

async def q_clima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    dato = query.data

    mapa = {
        'clima_seco':         ('seco',         'Día seco. Sin lluvia.'),
        'clima_sereno':       ('sereno',        'Llovizna.'),
        'clima_lluvia_fuerte':('lluvia_fuerte', 'Lluvia intensa.'),
    }
    tipo, desc = mapa[dato]
    sesion[chat_id]['clima_tipo'] = tipo
    sesion[chat_id]['clima_desc'] = desc

    await query.edit_message_reply_markup(reply_markup=None)
    return await _preguntar_luz(query)


async def _preguntar_luz(query):
    kb = teclado([
        ("💡 Sí hay luz",   "luz_si"),
        ("🔌 No hay luz",   "luz_no"),
    ])
    await query.message.reply_text(
        "💡 *¿Hubo luz eléctrica hoy en la finca?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_LUZ


async def q_luz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)
    sesion[chat_id]['luz'] = 1 if query.data == 'luz_si' else 0

    # Domingos: Adriana no trabaja — saltar directamente a George
    if sesion[chat_id]['domingo']:
        sesion[chat_id]['adriana_presente'] = False
        sesion[chat_id]['adriana_motivo'] = 'descanso_dominical'
        kb = teclado([("✅ Sí trabajó", "george_si"), ("❌ No trabajó", "george_no")])
        await query.message.reply_text(
            "*2️⃣ ¿George trabajó hoy?*",
            reply_markup=kb, parse_mode='Markdown'
        )
        return Q_GEORGE_TRABAJO

    # Días normales: preguntar por Adriana
    kb = teclado([("✅ Sí trabajé", "adriana_si"), ("❌ No trabajé", "adriana_no")])
    await query.message.reply_text(
        "👩 *¿Trabajaste hoy Adriana?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_ADRIANA_TRABAJO


# ─── PASO 2a: ADRIANA ────────────────────────────────────────────────────────

async def q_adriana_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    if query.data == 'adriana_si':
        sesion[chat_id]['adriana_presente'] = True
        sesion[chat_id]['adriana_motivo'] = ''
        return await _preguntar_george(query)

    # No trabajó — pedir motivo
    sesion[chat_id]['adriana_presente'] = False
    kb = teclado([
        ("🏠 Día libre",          "am_libre"),
        ("🤒 Enfermedad",         "am_enfermedad"),
        ("🏥 Incapacidad",        "am_incapacidad"),
        ("🏖️ Vacaciones",         "am_vacaciones"),
        ("📝 Permiso",            "am_permiso"),
        ("🚨 Calamidad",          "am_calamidad"),
    ])
    await query.message.reply_text(
        "👩 *¿Cuál fue el motivo?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_ADRIANA_MOTIVO


async def q_adriana_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    mapa = {
        'am_libre': 'libre', 'am_enfermedad': 'enfermedad',
        'am_incapacidad': 'incapacidad', 'am_vacaciones': 'vacaciones',
        'am_permiso': 'permiso', 'am_calamidad': 'calamidad',
    }
    sesion[chat_id]['adriana_motivo'] = mapa.get(query.data, 'libre')
    return await _preguntar_george(query)


async def _preguntar_george(query):
    chat_id = query.from_user.id
    kb = teclado([("✅ Sí trabajó", "george_si"), ("❌ No trabajó", "george_no")])
    await query.message.reply_text(
        "👨 *¿George trabajó hoy?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_GEORGE_TRABAJO


# ─── PASO 3: GEORGE ──────────────────────────────────────────────────────────

async def q_george_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    if query.data == 'george_si':
        sesion[chat_id]['george_presente'] = True
        sesion[chat_id]['george_motivo'] = ''
        return await _preguntar_lote(query)

    sesion[chat_id]['george_presente'] = False
    kb = teclado([
        ("🏠 Día libre",   "gm_libre"),
        ("🤒 Enfermedad",  "gm_enfermedad"),
        ("🏥 Incapacidad", "gm_incapacidad"),
        ("🏖️ Vacaciones",  "gm_vacaciones"),
        ("📝 Permiso",     "gm_permiso"),
        ("🚨 Calamidad",   "gm_calamidad"),
    ])
    await query.message.reply_text(
        "👨 *¿Cuál fue el motivo de George?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_GEORGE_MOTIVO


async def q_george_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    mapa = {
        'gm_libre': 'libre', 'gm_enfermedad': 'enfermedad',
        'gm_incapacidad': 'incapacidad', 'gm_vacaciones': 'vacaciones',
        'gm_permiso': 'permiso', 'gm_calamidad': 'calamidad',
    }
    sesion[chat_id]['george_motivo'] = mapa.get(query.data, 'libre')
    return await _preguntar_lote(query)


# ─── PASO 4: LOTE ────────────────────────────────────────────────────────────

async def _preguntar_lote(query):
    lote_actual = db.get_lote_actual()
    opciones = [(f"Lote {i}", f"lote_{i}") for i in range(1, 11)]
    kb = teclado(opciones)
    await query.message.reply_text(
        f"🐄 *¿En qué lote están los animales hoy?*\n_Ayer estaban en: Lote {lote_actual}_",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_LOTE


async def q_lote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    lote_seleccionado = int(query.data.split('_')[-1])
    lote_anterior = db.get_lote_actual()

    if lote_seleccionado != lote_anterior:
        # Cambio de lote → cuadra 1 automáticamente, sin preguntar
        sesion[chat_id]['lote_cambio'] = True
        sesion[chat_id]['lote_nuevo'] = lote_seleccionado
        sesion[chat_id]['cuadra_movio'] = True
        sesion[chat_id]['cuadra_nueva'] = 1
        sesion[chat_id]['cuadra_anterior'] = 0
        return await _preguntar_jornales(query)
    else:
        # Mismo lote → preguntar si hubo cambio de cuadra
        sesion[chat_id]['lote_cambio'] = False
        return await _preguntar_cuadra(query)


# ─── PASO 4b: CUADRA (solo cuando no hubo cambio de lote) ───────────────────

async def _preguntar_cuadra(query):
    lote = db.get_lote_actual()
    cuadra_actual = db.get_cuadra_actual(lote)
    kb = teclado([
        ("✅ Sí cambiaron",    "cuadra_si"),
        ("➡️ No, misma cuadra", "cuadra_no"),
    ])
    await query.message.reply_text(
        f"🌿 *¿Los animales cambiaron de cuadra hoy?*\n_Cuadra en uso: {cuadra_actual}_",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_CUADRA


async def q_cuadra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    lote = db.get_lote_actual()
    cuadra_actual = db.get_cuadra_actual(lote)

    if query.data == 'cuadra_no':
        sesion[chat_id]['cuadra_movio'] = False
        sesion[chat_id]['cuadra_actual'] = cuadra_actual
    else:
        sesion[chat_id]['cuadra_movio'] = True
        sesion[chat_id]['cuadra_nueva'] = cuadra_actual + 1
        sesion[chat_id]['cuadra_anterior'] = cuadra_actual

    return await _preguntar_jornales(query)


# ─── PASO 5: JORNALES ────────────────────────────────────────────────────────

async def _preguntar_jornales(query):
    kb = teclado([
        ("👷 Sí hubo jornales", "jornales_si"),
        ("✋ No hubo jornales", "jornales_no"),
    ])
    await query.message.reply_text(
        "👷 *¿Hubo algún trabajador contratado hoy?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_JORNALES


async def q_jornales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    if query.data == 'jornales_no':
        if 'jornales' not in sesion[chat_id]:
            sesion[chat_id]['jornales'] = []
        return await _preguntar_novedad(query)

    kb = teclado([
        ("🐄 Corral",       "jt_corral"),
        ("🏠 Casa/Cuadras", "jt_casa"),
        ("🪵 Cercas",       "jt_cercas"),
        ("💨 Fumigación",   "jt_fumigacion"),
        ("👷 General",      "jt_general"),
        ("🚜 Tractor",      "jt_tractor"),
    ])
    await query.message.reply_text(
        "👷 *¿En qué trabajó?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_JORNALES_TIPO


async def q_jornales_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    mapa = {
        'jt_corral': 'corral', 'jt_casa': 'casa',
        'jt_cercas': 'cercas', 'jt_fumigacion': 'fumigacion',
        'jt_general': 'general', 'jt_tractor': 'tractor',
    }
    sesion[chat_id]['jornal_tipo_temp'] = mapa.get(query.data, 'General')

    opciones = [(f"Lote {i}", f"jl_{i}") for i in range(1, 11)]
    opciones.append(("Corral", "jl_corral"))
    opciones.append(("General", "jl_general"))
    kb = teclado(opciones)
    await query.message.reply_text(
        "📍 *¿En qué lote o área trabajó?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_JORNALES_LOTE


async def q_jornales_lote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    lote = query.data.replace('jl_', '')
    if 'jornales' not in sesion[chat_id]:
        sesion[chat_id]['jornales'] = []
    sesion[chat_id]['jornales'].append({
        'tipo': sesion[chat_id].get('jornal_tipo_temp', 'General'),
        'lote': lote,
        'cantidad': 1,
    })

    kb = teclado([
        ("➕ Agregar otro jornal", "jornales_si"),
        ("✅ Listo con jornales", "jornales_no"),
    ])
    await query.message.reply_text(
        "✓ Anotado.\n*¿Hubo otro trabajador contratado hoy?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_JORNALES


# ─── PASO 6: NOVEDAD (texto libre) ───────────────────────────────────────────

async def _preguntar_novedad(query):
    kb = teclado([
        ("✅ Sin novedades",   "novedad_no"),
        ("💉 Vacunaron",       "novedad_vacunacion"),
        ("🤒 Animal enfermo",  "novedad_enfermo"),
        ("📝 Otra novedad",    "novedad_otra"),
    ])
    await query.message.reply_text(
        "📝 *¿Hubo alguna novedad hoy?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_NOVEDAD


async def q_novedad_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Texto libre escrito directamente (sin presionar botón)."""
    chat_id = update.effective_chat.id
    sesion[chat_id]['novedad'] = update.message.text
    sesion[chat_id]['sanitario_tipo'] = None
    return await _confirmar(update.message, chat_id)


async def q_novedad_boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    if query.data == 'novedad_no':
        sesion[chat_id]['novedad'] = ''
        sesion[chat_id]['sanitario_tipo'] = None
        return await _confirmar(query.message, chat_id)

    if query.data == 'novedad_vacunacion':
        sesion[chat_id]['sanitario_tipo'] = 'vacunacion'
        await query.message.reply_text(
            "💉 *¿Qué vacuna o producto aplicaron?*\n"
            "_Ej: Aftosa, Carbón sintomático, Vitamina AD3E, Oxitetraciclina..._",
            parse_mode='Markdown'
        )
        return Q_VAC_PRODUCTO

    if query.data == 'novedad_enfermo':
        sesion[chat_id]['sanitario_tipo'] = 'enfermedad'
        await query.message.reply_text(
            "🤒 *Describe el animal y el tratamiento aplicado:*\n"
            "_Ej: Vaca negra con fiebre alta, se aplicó Oxitetraciclina 5ml_",
            parse_mode='Markdown'
        )
        return Q_ENFERMO_DESC

    # novedad_otra → esperar texto libre
    await query.message.reply_text(
        "📝 *Escribe la novedad:*",
        parse_mode='Markdown'
    )
    return Q_NOVEDAD


# ─── PASO 6b: VACUNACIÓN ─────────────────────────────────────────────────────

async def q_vac_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe nombre de vacuna/producto, pregunta grupo de animales."""
    chat_id = update.effective_chat.id
    sesion[chat_id]['sanitario_producto'] = update.message.text
    kb = teclado([
        ("🗓 Octubre 2025", "vl_oct2025"),
        ("🗓 Enero 2026",   "vl_ene2026"),
        ("🗓 Marzo 2026",   "vl_mar2026"),
        ("🐄 Todos",        "vl_todos"),
    ])
    await update.message.reply_text(
        "*¿A qué grupo de animales?*",
        reply_markup=kb, parse_mode='Markdown'
    )
    return Q_VAC_LOTE


async def q_vac_lote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe grupo de animales, va a confirmar."""
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)
    mapa = {
        'vl_oct2025': 'Octubre 2025',
        'vl_ene2026': 'Enero 2026',
        'vl_mar2026': 'Marzo 2026',
        'vl_todos':   'Todos',
    }
    sesion[chat_id]['sanitario_lote_animales'] = mapa.get(query.data, 'Todos')
    producto = sesion[chat_id].get('sanitario_producto', '')
    lote_anim = sesion[chat_id]['sanitario_lote_animales']
    sesion[chat_id]['novedad'] = f"Vacunación {producto} — {lote_anim}"
    return await _confirmar(query.message, chat_id)


# ─── PASO 6c: ANIMAL ENFERMO ──────────────────────────────────────────────────

async def q_enfermo_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe descripción de animal enfermo y tratamiento."""
    chat_id = update.effective_chat.id
    sesion[chat_id]['sanitario_producto'] = update.message.text
    sesion[chat_id]['sanitario_lote_animales'] = ''
    sesion[chat_id]['novedad'] = f"Animal enfermo: {update.message.text}"
    return await _confirmar(update.message, chat_id)


# ─── PASO 7: CONFIRMACIÓN ────────────────────────────────────────────────────

async def _confirmar(message, chat_id):
    s = sesion[chat_id]
    lote_actual = db.get_lote_actual()

    CLIMAS = {'seco': '☀️ Seco', 'sereno': '🌦 Llovizna', 'lluvia_fuerte': '⛈ Lluvia fuerte'}
    adriana = '✅ Trabajó' if s.get('adriana_presente') else f"❌ No trabajó ({s.get('adriana_motivo', '')})"
    george  = '✅ Trabajó' if s.get('george_presente')  else f"❌ No trabajó ({s.get('george_motivo', '')})"

    if s.get('lote_cambio'):
        lote_txt = f"🔄 Cambio a Lote {s.get('lote_nuevo')}"
    else:
        lote_txt = f"📍 Siguen en Lote {lote_actual}"

    if s.get('cuadra_movio'):
        cuadra_txt = f"🟢 Cambio Cuadra {s.get('cuadra_anterior')} → {s.get('cuadra_nueva')} (cuadra {s.get('cuadra_anterior')} inicia descanso)"
    else:
        cuadra_txt = f"➡️ Sin cambio (Cuadra {s.get('cuadra_actual', '?')} en uso)"

    jornales_txt = ''
    for j in s.get('jornales', []):
        jornales_txt += f"\n  • {j['tipo']} — {j['lote']}"
    if not jornales_txt:
        jornales_txt = '\n  Sin jornales'

    novedad_txt = s.get('novedad') or 'Sin novedades'

    sanitario_txt = ''
    if s.get('sanitario_tipo') == 'vacunacion':
        sanitario_txt = (
            f"\n💉 Vacunación: {s.get('sanitario_producto', '')} "
            f"— {s.get('sanitario_lote_animales', 'Todos')}"
        )
    elif s.get('sanitario_tipo') == 'enfermedad':
        sanitario_txt = f"\n🤒 Animal enfermo: {s.get('sanitario_producto', '')[:60]}"

    luz_txt = "💡 Hay luz" if s.get('luz', 1) else "🔌 Sin luz"

    resumen = (
        f"📋 *Resumen del reporte — {s['fecha']}*\n\n"
        f"🌤 Clima: {CLIMAS.get(s.get('clima_tipo', 'seco'))} | {luz_txt}\n"
        f"👩 Adriana: {adriana}\n"
        f"👨 George: {george}\n"
        f"🐃 Lote: {lote_txt}\n"
        f"🌿 Cuadra: {cuadra_txt}\n"
        f"👷 Jornales: {jornales_txt}\n"
        f"📝 Novedad: {novedad_txt}{sanitario_txt}\n\n"
        f"*¿Confirmar y guardar?*"
    )

    kb = teclado([("✅ Confirmar", "confirmar_si"), ("✏️ Reiniciar", "confirmar_no")])
    await message.reply_text(resumen, reply_markup=kb, parse_mode='Markdown')
    return Q_CONFIRMAR


async def q_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    await query.edit_message_reply_markup(reply_markup=None)

    if query.data == 'confirmar_no':
        await query.message.reply_text(
            "Reporte cancelado. Usa /reporte para empezar de nuevo."
        )
        sesion.pop(chat_id, None)
        return ConversationHandler.END

    s = sesion[chat_id]
    fecha = s['fecha']
    lote_actual = db.get_lote_actual()

    # 1. Guardar clima
    db.guardar_clima(
        fecha=fecha,
        tipo=s.get('clima_tipo', 'seco'),
        descripcion=s.get('clima_desc', ''),
        registrado_por='George' if s['domingo'] else 'Adriana',
        luz=s.get('luz', 1)
    )

    # 2. Guardar asistencia Adriana
    db.guardar_asistencia(
        fecha=fecha,
        personal_id=1,
        presente=s.get('adriana_presente', False),
        motivo_ausencia=s.get('adriana_motivo', ''),
        notas='Domingo - Adriana no labora.' if s['domingo'] else ''
    )

    # 3. Guardar asistencia George
    db.guardar_asistencia(
        fecha=fecha,
        personal_id=2,
        presente=s.get('george_presente', True),
        motivo_ausencia=s.get('george_motivo', ''),
        notas=s.get('novedad', '')
    )

    # 4. Rotación de lote (si hubo cambio)
    if s.get('lote_cambio') and s.get('lote_nuevo'):
        db.guardar_rotacion(
            fecha=fecha,
            lote_anterior=lote_actual,
            lote_nuevo=s['lote_nuevo'],
            notas=s.get('novedad', '')
        )
        db.guardar_actividad(
            fecha=fecha,
            tipo='rotacion',
            descripcion=f"Rotación animales Lote {lote_actual} → Lote {s['lote_nuevo']}",
            lote=s['lote_nuevo'],
            responsable='Adriana Bastidas y George Bastidas',
            tipo_contrato='fijo',
            notas=s.get('novedad', '')
        )

    # 5. Registrar el día en el lote (siempre, haya o no rotación)
    db.registrar_dia_en_lote(fecha)

    # 6. Guardar movimiento de cuadra (si hubo)
    lote_dia = s.get('lote_nuevo') or lote_actual
    if s.get('cuadra_movio') and s.get('cuadra_nueva'):
        db.guardar_movimiento_cuadra(
            fecha=fecha,
            lote=lote_dia,
            cuadra_nueva=s['cuadra_nueva'],
            notas=s.get('novedad', '')
        )

    # 6. Guardar jornales
    _JORNAL_TIPO_MAP = {
        'cercas':     ('cercas',     'Jornalero Cercas'),
        'fumigacion': ('fumigacion', 'Fumigador'),
        'corral':     ('jornal',     'Jornalero Corral'),
        'casa':       ('jornal',     'Jornalero Casa/Cuadras'),
        'general':    ('jornal',     'Jornalero General'),
        'tractor':    ('tractor',    'Tractorista'),
    }
    for j in s.get('jornales', []):
        db.guardar_jornal(
            fecha=fecha,
            tipo=j['tipo'],
            lote=j['lote'],
            cantidad=j.get('cantidad', 1)
        )
        tipo_act, responsable_act = _JORNAL_TIPO_MAP.get(j['tipo'].lower(), ('jornal', 'Jornalero'))
        db.guardar_actividad(
            fecha=fecha,
            tipo=tipo_act,
            descripcion=f"Jornal {j['tipo'].capitalize()} — Lote {j['lote']}",
            lote=int(j['lote']) if str(j['lote']).isdigit() else None,
            responsable=responsable_act,
            tipo_contrato='jornal'
        )

    # 6. Guardar "Trabajo diario" por cada trabajador presente (cuenta como jornal fijo)
    lote_dia = s.get('lote_nuevo') or lote_actual
    if s.get('adriana_presente'):
        db.guardar_actividad(
            fecha=fecha,
            tipo='manejo',
            descripcion='Trabajo diario',
            lote=lote_dia,
            responsable='Adriana Bastidas',
            tipo_contrato='fijo',
            notas=s.get('novedad', '')
        )
    if s.get('george_presente'):
        db.guardar_actividad(
            fecha=fecha,
            tipo='manejo',
            descripcion='Trabajo diario',
            lote=lote_dia,
            responsable='George Bastidas',
            tipo_contrato='fijo',
            notas=s.get('novedad', '')
        )

    # 7. Guardar evento sanitario (vacunación o animal enfermo)
    if s.get('sanitario_tipo'):
        db.guardar_sanitario(
            fecha=fecha,
            tipo=s['sanitario_tipo'],
            lote_animales=s.get('sanitario_lote_animales', ''),
            producto=s.get('sanitario_producto', ''),
            responsable='Adriana Bastidas' if not s['domingo'] else 'George Bastidas',
            notas=s.get('novedad', '')
        )
        db.guardar_actividad(
            fecha=fecha,
            tipo='sanitario',
            descripcion=s.get('novedad', '')[:80],
            lote=lote_dia,
            responsable='Adriana Bastidas' if not s['domingo'] else 'George Bastidas',
            tipo_contrato='fijo',
            notas=s.get('novedad', '')
        )

    # 8. Si hay novedad de texto libre, guardar actividad adicional
    if s.get('novedad') and not s.get('sanitario_tipo'):
        db.guardar_actividad(
            fecha=fecha,
            tipo='manejo',
            descripcion=s['novedad'][:80],
            lote=lote_dia,
            responsable='Adriana Bastidas' if not s['domingo'] else 'George Bastidas',
            tipo_contrato='fijo',
            notas=s['novedad']
        )

    # Construir resumen ANTES de limpiar sesión
    CLIMAS = {'seco': '☀️ Seco', 'sereno': '🌦 Llovizna', 'lluvia_fuerte': '⛈ Lluvia fuerte'}
    adriana_txt = '✅ Trabajó' if s.get('adriana_presente') else f"❌ No trabajó ({s.get('adriana_motivo', '')})"
    george_txt  = '✅ Trabajó' if s.get('george_presente')  else f"❌ No trabajó ({s.get('george_motivo', '')})"
    lote_actual_notif = db.get_lote_actual()
    lote_txt_n  = f"🔄 Cambio a Lote {s.get('lote_nuevo')}" if s.get('lote_cambio') else f"📍 Lote {lote_actual_notif}"
    cuadra_txt_n = (f"🟢 Cambio Cuadra {s.get('cuadra_anterior')} → {s.get('cuadra_nueva')}"
                    if s.get('cuadra_movio') else f"➡️ Cuadra {s.get('cuadra_actual', '?')} sin cambio")
    jornales_n = ''.join(f"\n  • {j['tipo']} — {j['lote']}" for j in s.get('jornales', [])) or '\n  Sin jornales'
    novedad_n  = s.get('novedad') or 'Sin novedades'
    sanitario_n = ''
    if s.get('sanitario_tipo') == 'vacunacion':
        sanitario_n = f"\n💉 Vacunación: {s.get('sanitario_producto', '')} — {s.get('sanitario_lote_animales', 'Todos')}"
    elif s.get('sanitario_tipo') == 'enfermedad':
        sanitario_n = f"\n🤒 Animal enfermo: {s.get('sanitario_producto', '')[:60]}"
    resumen_notif = (
        f"📬 *Reporte del {fecha} confirmado*\n\n"
        f"🌤 Clima: {CLIMAS.get(s.get('clima_tipo', 'seco'))}\n"
        f"👩 Adriana: {adriana_txt}\n"
        f"👨 George: {george_txt}\n"
        f"🐃 {lote_txt_n}\n"
        f"🌿 {cuadra_txt_n}\n"
        f"👷 Jornales:{jornales_n}\n"
        f"📝 Novedad: {novedad_n}{sanitario_n}"
    )

    sesion.pop(chat_id, None)

    await query.message.reply_text(
        "✅ *Reporte guardado correctamente.*\n\n"
        "El dashboard se actualizará en unos segundos. ¡Gracias!",
        parse_mode='Markdown'
    )

    # Notificar al dueño con el resumen completo
    if config.OWNER_CHAT_ID and config.OWNER_CHAT_ID != chat_id:
        try:
            await context.bot.send_message(
                chat_id=config.OWNER_CHAT_ID,
                text=resumen_notif,
                parse_mode='Markdown',
            )
        except Exception:
            pass

    return ConversationHandler.END


async def q_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sesion.pop(chat_id, None)
    await update.message.reply_text("Reporte cancelado. Usa /reporte para empezar de nuevo.")
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════════════════
# MÓDULO DE GASTOS/INGRESOS PERSONALES (Juan Pablo)
# ═══════════════════════════════════════════════════════════════════════════════

import os as _os

DOCS_FIN_DIR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'documentos', 'finanzas'))
_os.makedirs(DOCS_FIN_DIR, exist_ok=True)

# Estados del ConversationHandler de finanzas (rango 100+ para no chocar)
(
    FIN_TIENE,    # ¿tuviste gastos hoy? (modo noche)
    FIN_TIPO,     # gasto / ingreso / prestamo
    FIN_MONTO,    # monto en texto
    FIN_DETALLE,  # descripción
    FIN_CAT,      # categoría
    FIN_PAGO,     # forma de pago
    FIN_FOTO,     # foto/doc opcional
    FIN_OTRO,     # ¿agregar otro movimiento?
) = range(100, 108)

sesion_fin = {}   # {chat_id: {tipo, monto, detalle, cat, pago}}

CATEGORIAS_FIN = [
    ('⛽ Combustible',     'combustible'),
    ('🐄 Ganado',          'ganado'),
    ('🌿 Insumos finca',   'insumos_finca'),
    ('🍽 Alimentación',    'alimentacion'),
    ('👷 Nómina finca',    'nomina_finca'),
    ('🚛 Transporte',      'transporte'),
    ('📱 Celulares',       'celulares'),
    ('💼 Servicios',       'servicios'),
    ('🏦 Impuestos',       'impuestos'),
    ('🚗 Vehículo',        'vehiculo'),
    ('🎁 Personal/Familia','personal_familia'),
    ('💸 Préstamo',        'prestamo'),
    ('📦 Otro',            'otro'),
]

FORMAS_PAGO_FIN = [
    ('💵 Efectivo',       'efectivo'),
    ('💳 Débito',         'debito'),
    ('📱 Nequi',          'nequi'),
    ('🌐 Virtual/PSE',    'virtual'),
    ('🏦 Transferencia',  'transferencia'),
    ('🏛 Consignación',   'consignacion'),
    ('— Sin especificar', ''),
]


def _teclado_fin(opciones, cols=2):
    """Genera InlineKeyboardMarkup desde lista de (label, data)."""
    rows, row = [], []
    for label, data in opciones:
        row.append(InlineKeyboardButton(label, callback_data=f'fin_{data}'))
        if len(row) == cols:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


async def _fin_pedir_tipo(message, chat_id, modo='manual'):
    """Pregunta si es gasto, ingreso o préstamo."""
    sesion_fin[chat_id] = {'modo': modo}
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton('🔴 Gasto',    callback_data='fin_tipo_gasto'),
        InlineKeyboardButton('🟢 Ingreso',  callback_data='fin_tipo_ingreso'),
        InlineKeyboardButton('🔵 Préstamo', callback_data='fin_tipo_prestamo'),
    ]])
    await message.reply_text(
        "💰 *Nuevo movimiento*\n\n¿Qué tipo de movimiento es?",
        reply_markup=kb, parse_mode='Markdown'
    )
    return FIN_TIPO


async def cmd_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /gasto — inicia registro manual."""
    if not autorizado(update):
        await _no_autorizado(update); return ConversationHandler.END
    chat_id = update.effective_chat.id
    if chat_id == config.ADRIANA_CHAT_ID:
        await update.message.reply_text("Este comando es solo para el dueño.")
        return ConversationHandler.END
    return await _fin_pedir_tipo(update.message, chat_id)


async def fin_tiene_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Respuesta al botón nocturno ¿tuviste gastos?"""
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    if query.data == 'fin_noche_no':
        await query.edit_message_text("👍 Perfecto, sin movimientos hoy. ¡Buenas noches!")
        return ConversationHandler.END
    await query.edit_message_reply_markup(reply_markup=None)
    return await _fin_pedir_tipo(query.message, chat_id, modo='noche')


async def fin_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    tipo_map = {
        'fin_tipo_gasto':    'gasto',
        'fin_tipo_ingreso':  'ingreso',
        'fin_tipo_prestamo': 'prestamo_recibido',
    }
    sesion_fin[chat_id]['tipo'] = tipo_map[query.data]
    label = {'gasto':'Gasto 🔴','ingreso':'Ingreso 🟢','prestamo_recibido':'Préstamo 🔵'}[sesion_fin[chat_id]['tipo']]
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"*{label}* seleccionado.\n\n💵 ¿Cuánto fue el monto? (solo el número, ej: 45000)",
        parse_mode='Markdown'
    )
    return FIN_MONTO


async def fin_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    texto = update.message.text.strip().replace(',', '').replace('.', '').replace('$', '').replace(' ', '')
    try:
        monto = float(texto)
        if monto <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Escribe solo el número, sin símbolos. Ej: 45000")
        return FIN_MONTO
    sesion_fin[chat_id]['monto'] = monto
    await update.message.reply_text(
        "📝 ¿Cuál es el detalle o descripción? (ej: Gasolina camioneta, Mercado semana)"
    )
    return FIN_DETALLE


async def fin_detalle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sesion_fin[chat_id]['detalle'] = update.message.text.strip()
    await update.message.reply_text(
        "🏷 ¿A qué categoría pertenece?",
        reply_markup=_teclado_fin(CATEGORIAS_FIN, cols=2)
    )
    return FIN_CAT


async def fin_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    sesion_fin[chat_id]['categoria'] = query.data.replace('fin_', '', 1)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        "💳 ¿Cómo fue el pago?",
        reply_markup=_teclado_fin(FORMAS_PAGO_FIN, cols=2)
    )
    return FIN_PAGO


async def fin_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    sesion_fin[chat_id]['forma_pago'] = query.data.replace('fin_', '', 1)
    await query.edit_message_reply_markup(reply_markup=None)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton('⏭ Sin adjunto', callback_data='fin_foto_skip')
    ]])
    await query.message.reply_text(
        "📎 ¿Quieres adjuntar una foto del recibo o factura?\n\n"
        "Envíame la *foto o PDF* ahora, o toca *Sin adjunto* para continuar.",
        reply_markup=kb, parse_mode='Markdown'
    )
    return FIN_FOTO


async def fin_foto_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usuario decidió no adjuntar foto."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    return await _fin_guardar(query.message, query.from_user.id, foto_path=None)


async def fin_foto_recibida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usuario envió foto o documento."""
    chat_id = update.effective_chat.id
    hoy = datetime.now(ZONA_COLOMBIA).strftime('%Y%m%d_%H%M%S')
    foto_path = None

    try:
        if update.message.photo:
            file_obj = await context.bot.get_file(update.message.photo[-1].file_id)
            filename = f"bot_{chat_id}_{hoy}.jpg"
        elif update.message.document:
            doc = update.message.document
            ext = _os.path.splitext(doc.file_name)[1].lower() if doc.file_name else '.pdf'
            if ext not in ('.pdf', '.jpg', '.jpeg', '.png'):
                await update.message.reply_text("⚠️ Solo acepto JPG, PNG o PDF. Intenta de nuevo o toca Sin adjunto.")
                return FIN_FOTO
            file_obj = await context.bot.get_file(doc.file_id)
            filename = f"bot_{chat_id}_{hoy}{ext}"
        else:
            await update.message.reply_text("⚠️ Envía una foto o documento PDF.")
            return FIN_FOTO

        ruta = _os.path.join(DOCS_FIN_DIR, filename)
        await file_obj.download_to_drive(ruta)
        foto_path = f"finanzas/{filename}"
        await update.message.reply_text("✅ Archivo recibido.")
    except Exception as e:
        logger.error(f"Error descargando adjunto: {e}")
        await update.message.reply_text("⚠️ No pude guardar el archivo. Continúo sin adjunto.")

    return await _fin_guardar(update.message, chat_id, foto_path=foto_path)


async def _fin_guardar(message, chat_id: int, foto_path: str | None):
    """Guarda el movimiento en DB y pregunta si hay otro."""
    s = sesion_fin.get(chat_id, {})
    tipo = s.get('tipo', 'gasto')
    monto = s.get('monto', 0)
    ingreso  = monto if tipo == 'ingreso' else 0.0
    prestamo = monto if tipo == 'prestamo_recibido' else 0.0
    gasto    = monto if tipo == 'gasto' else 0.0

    fecha = datetime.now(ZONA_COLOMBIA).strftime('%Y-%m-%d')
    fin_id = db.guardar_finanza(
        fecha      = fecha,
        detalle    = s.get('detalle', ''),
        ingreso    = ingreso,
        prestamo   = prestamo,
        gasto      = gasto,
        tipo       = tipo,
        categoria  = s.get('categoria', 'otro'),
        forma_pago = s.get('forma_pago', ''),
        notas      = 'Registrado por bot Telegram',
    )

    if foto_path:
        db.guardar_finanza_doc(fin_id, foto_path, _os.path.basename(foto_path), tipo='comprobante')

    tipo_label = {'gasto':'Gasto 🔴','ingreso':'Ingreso 🟢','prestamo_recibido':'Préstamo 🔵'}.get(tipo, tipo)
    monto_fmt  = f"${monto:,.0f}".replace(',', '.')
    adjunto_txt = f"\n📎 Adjunto guardado." if foto_path else ""

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton('➕ Agregar otro', callback_data='fin_otro_si'),
        InlineKeyboardButton('✅ Listo',        callback_data='fin_otro_no'),
    ]])
    await message.reply_text(
        f"✅ *Registrado:*\n"
        f"  {tipo_label} — {monto_fmt}\n"
        f"  📝 {s.get('detalle','')}\n"
        f"  🏷 {s.get('categoria','otro')} · {s.get('forma_pago','') or 'sin forma de pago'}"
        f"{adjunto_txt}\n\n"
        f"¿Quieres agregar otro movimiento?",
        reply_markup=kb, parse_mode='Markdown'
    )
    sesion_fin.pop(chat_id, None)
    return FIN_OTRO


async def fin_otro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    if query.data == 'fin_otro_si':
        return await _fin_pedir_tipo(query.message, query.from_user.id)
    await query.message.reply_text("👍 ¡Listo! Todo guardado en el dashboard.")
    return ConversationHandler.END


async def fin_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sesion_fin.pop(update.effective_chat.id, None)
    await update.message.reply_text("Registro cancelado. Usa /gasto para empezar de nuevo.")
    return ConversationHandler.END


async def enviar_cuestionario_gastos(context):
    """10pm: pregunta al dueño si tuvo gastos hoy."""
    chat_id = config.OWNER_CHAT_ID
    if not chat_id:
        return
    fecha = datetime.now(ZONA_COLOMBIA).strftime('%Y-%m-%d')
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton('💰 Sí, registrar',  callback_data='fin_noche_si'),
        InlineKeyboardButton('👍 No tuve gastos',  callback_data='fin_noche_no'),
    ]])
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🌙 *Cierre del día — {fecha}*\n\n¿Registraste algún gasto o ingreso hoy?",
        reply_markup=kb,
        parse_mode='Markdown'
    )


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    db.inicializar_db()

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler('reporte',   iniciar_cuestionario),
            CommandHandler('corregir',  cmd_corregir),
            CallbackQueryHandler(iniciar_auto, pattern='^iniciar_auto$'),
        ],
        states={
            Q_FECHA:          [CallbackQueryHandler(q_fecha, pattern='^(fecha_|corregir_)')],
            Q_CLIMA:          [CallbackQueryHandler(q_clima, pattern='^clima_')],
            Q_LUZ:            [CallbackQueryHandler(q_luz, pattern='^luz_')],
            Q_ADRIANA_TRABAJO:[CallbackQueryHandler(q_adriana_trabajo, pattern='^adriana_')],
            Q_ADRIANA_MOTIVO: [CallbackQueryHandler(q_adriana_motivo, pattern='^am_')],
            Q_GEORGE_TRABAJO: [CallbackQueryHandler(q_george_trabajo, pattern='^george_')],
            Q_GEORGE_MOTIVO:  [CallbackQueryHandler(q_george_motivo, pattern='^gm_')],
            Q_LOTE:           [CallbackQueryHandler(q_lote, pattern='^lote_')],
            Q_CUADRA:         [CallbackQueryHandler(q_cuadra, pattern='^cuadra_')],
            Q_JORNALES:       [CallbackQueryHandler(q_jornales, pattern='^jornales_')],
            Q_JORNALES_TIPO:  [CallbackQueryHandler(q_jornales_tipo, pattern='^jt_')],
            Q_JORNALES_LOTE:  [CallbackQueryHandler(q_jornales_lote, pattern='^jl_')],
            Q_NOVEDAD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, q_novedad_texto),
                CallbackQueryHandler(q_novedad_boton, pattern='^novedad_'),
            ],
            Q_VAC_PRODUCTO:  [MessageHandler(filters.TEXT & ~filters.COMMAND, q_vac_producto)],
            Q_VAC_LOTE:      [CallbackQueryHandler(q_vac_lote, pattern='^vl_')],
            Q_ENFERMO_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, q_enfermo_desc)],
            Q_CONFIRMAR: [CallbackQueryHandler(q_confirmar, pattern='^confirmar_')],
        },
        fallbacks=[CommandHandler('cancelar', q_cancelar)],
        allow_reentry=True,
    )

    # ── ConversationHandler de finanzas (gastos/ingresos del dueño) ──────────
    conv_fin = ConversationHandler(
        entry_points=[
            CommandHandler('gasto', cmd_gasto),
            CallbackQueryHandler(fin_tiene_gastos, pattern='^fin_noche_'),
        ],
        states={
            FIN_TIPO:   [CallbackQueryHandler(fin_tipo,    pattern='^fin_tipo_')],
            FIN_MONTO:  [MessageHandler(filters.TEXT & ~filters.COMMAND, fin_monto)],
            FIN_DETALLE:[MessageHandler(filters.TEXT & ~filters.COMMAND, fin_detalle)],
            FIN_CAT:    [CallbackQueryHandler(fin_cat,     pattern='^fin_')],
            FIN_PAGO:   [CallbackQueryHandler(fin_pago,    pattern='^fin_')],
            FIN_FOTO: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, fin_foto_recibida),
                CallbackQueryHandler(fin_foto_skip, pattern='^fin_foto_skip$'),
            ],
            FIN_OTRO:   [CallbackQueryHandler(fin_otro,    pattern='^fin_otro_')],
        },
        fallbacks=[CommandHandler('cancelar', fin_cancelar)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('estado', cmd_estado))
    app.add_handler(CommandHandler('ver', cmd_ver))
    app.add_handler(CommandHandler('ayuda', cmd_ayuda))
    app.add_handler(conv_fin)
    app.add_handler(conv)

    # Scheduler: envío automático a las 4pm hora Colombia
    hora, minuto = map(int, config.HORA_REPORTE.split(':'))
    scheduler = AsyncIOScheduler(timezone=ZONA_COLOMBIA)

    async def job_cuestionario():
        logger.info(f"Scheduler: disparando cuestionario automático ({config.HORA_REPORTE})")
        class FakeContext:
            bot = app.bot
        try:
            await enviar_cuestionario_automatico(FakeContext())
            logger.info("Scheduler: cuestionario enviado a Adriana correctamente")
        except Exception as e:
            logger.error(f"Scheduler: error al enviar cuestionario — {e}")

    scheduler.add_job(job_cuestionario, 'cron', hour=hora, minute=minuto)

    # Informe financiero mensual: último día de cada mes a las 8pm hora Colombia
    async def job_informe_mensual():
        class FakeContext:
            bot = app.bot
        await enviar_informe_mensual(FakeContext())

    scheduler.add_job(job_informe_mensual, 'cron', day='last', hour=20, minute=0)

    # Cuestionario de gastos nocturnos: 10pm todos los días al dueño
    async def job_gastos_noche():
        class FakeContext:
            bot = app.bot
        await enviar_cuestionario_gastos(FakeContext())

    scheduler.add_job(job_gastos_noche, 'cron', hour=22, minute=0)

    scheduler.start()

    logger.info(f"Bot iniciado. Cuestionario automático a las {config.HORA_REPORTE} hora Colombia.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
