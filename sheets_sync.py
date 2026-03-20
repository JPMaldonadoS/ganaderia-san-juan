"""
Sincronización SQLite → Google Sheets
Se llama desde app.py cada vez que se crea o elimina una finanza.
"""
import os
import sys
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _fecha_key(f):
    """Clave de ordenamiento: fechas ISO válidas primero; fechas mal formateadas al final."""
    try:
        return datetime.strptime(f.get('fecha', ''), '%Y-%m-%d')
    except (ValueError, TypeError):
        return datetime.min

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'ganaderia-san-juan-fbf777fab6af.json')
SHEET_ID = '1OoHVcB1tE84OsKFIEdNr2avXO2dOWKk9zG4dGwt8lX4'
HOJA_NOMBRE = 'Finanzas'

HEADERS = ['Fecha', 'Detalle', 'Ingreso', 'Préstamo', 'Gasto', 'Saldo', 'Categoría', 'Forma de Pago', 'Notas']

def _get_sheet():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
        ]
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        return spreadsheet.worksheet(HOJA_NOMBRE)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=HOJA_NOMBRE, rows=5000, cols=9)
        sheet.append_row(HEADERS)
        return sheet


def sincronizar_todo(finanzas: list):
    """Reescribe la hoja con el mismo formato del dashboard: Fecha, Detalle, Ingreso, Préstamo, Gasto, Saldo, Categoría, Pago, Notas."""
    try:
        sheet = _get_sheet()
        sheet.clear()
        sheet.append_row(HEADERS)
        rows = []
        saldo = 0.0
        # Calcular saldo en orden cronológico ascendente
        for f in sorted(finanzas, key=_fecha_key):
            ingreso  = float(f.get('ingreso', 0) or 0)
            prestamo = float(f.get('prestamo', 0) or 0)
            gasto    = float(f.get('gasto', 0) or 0)
            saldo   += ingreso + prestamo - gasto
            rows.append([
                f.get('fecha', ''),
                f.get('detalle', ''),
                ingreso  if ingreso  else '',
                prestamo if prestamo else '',
                gasto    if gasto    else '',
                round(saldo, 2),
                f.get('categoria', ''),
                f.get('formaPago', ''),
                f.get('notas', ''),
            ])
        # Mostrar más reciente primero (sin alterar el saldo acumulado)
        rows.reverse()
        if rows:
            sheet.append_rows(rows)

        # Ajustar ancho de columnas: Fecha, Detalle(ancho), Ingreso, Préstamo, Gasto, Saldo, Categoría, Pago, Notas
        spreadsheet = sheet.spreadsheet
        sheet_id = sheet.id
        requests = [
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 100}, "fields": "pixelSize"}},  # Fecha
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 400}, "fields": "pixelSize"}},  # Detalle
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 6}, "properties": {"pixelSize": 110}, "fields": "pixelSize"}},  # Ingreso/Préstamo/Gasto/Saldo
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 9}, "properties": {"pixelSize": 130}, "fields": "pixelSize"}},  # Categoría/Pago/Notas
        ]
        spreadsheet.batch_update({"requests": requests})

        logger.info(f"Sheets sincronizado: {len(rows)} registros")
    except Exception as e:
        logger.error(f"Error sincronizando con Google Sheets: {e}")
