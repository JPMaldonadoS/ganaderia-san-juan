"""
Configuración del Bot de Ganadería San Juan
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADRIANA_CHAT_ID = int(os.getenv('ADRIANA_CHAT_ID', 0))
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID', 0))

# Horario del cuestionario (hora Colombia)
HORA_REPORTE = os.getenv('HORA_REPORTE', '16:00')

# Base de datos SQLite
DB_PATH = os.getenv('DB_PATH', '../data/ganaderia.db')

# Tipos de jornal
TIPOS_JORNAL = {
    '1': {'nombre': 'Corral',        'icono': '🐄', 'lote_default': 'corral'},
    '2': {'nombre': 'Casa/Cuadras',  'icono': '🏠', 'lote_default': 'casa'},
    '3': {'nombre': 'Cercas',        'icono': '🪵', 'lote_default': None},
    '4': {'nombre': 'Fumigación',    'icono': '💨', 'lote_default': None},
    '5': {'nombre': 'General',       'icono': '👷', 'lote_default': None},
}

# Tipos de actividad sanitaria
TIPOS_SANITARIO = {
    '1': {'nombre': 'Vacunación', 'icono': '💉', 'tipo': 'vacunacion'},
    '2': {'nombre': 'Purga',      'icono': '💊', 'tipo': 'purga'},
    '3': {'nombre': 'Vitamina',   'icono': '🧴', 'tipo': 'vitamina'},
    '4': {'nombre': 'Marcación',  'icono': '🔥', 'tipo': 'marcacion'},
}

# Lotes de la finca
LOTES_FINCA = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Personal fijo (id debe coincidir con la tabla personal en SQLite)
PERSONAL_FIJO = {
    1: 'Adriana Bastidas',
    2: 'George Bastidas',
}

# Motivos de ausencia
MOTIVOS_AUSENCIA = {
    '1': {'nombre': 'Día libre',           'icono': '🏠', 'tipo': 'libre'},
    '2': {'nombre': 'Enfermedad',          'icono': '🤒', 'tipo': 'enfermedad'},
    '3': {'nombre': 'Incapacidad médica',  'icono': '🏥', 'tipo': 'incapacidad'},
    '4': {'nombre': 'Vacaciones',          'icono': '🏖️', 'tipo': 'vacaciones'},
    '5': {'nombre': 'Permiso personal',    'icono': '📝', 'tipo': 'permiso'},
    '6': {'nombre': 'Calamidad doméstica', 'icono': '🚨', 'tipo': 'calamidad'},
}
