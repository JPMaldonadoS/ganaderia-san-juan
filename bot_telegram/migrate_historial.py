#!/usr/bin/env python3
"""
Migración: Poblar rotacion_lotes con historial completo.
Ejecutar UNA SOLA VEZ en el servidor para que el bot calcule
numero_rotacion correctamente en todas las rotaciones futuras.
"""
import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'ganaderia.db'))

# Historial completo en orden cronológico
# (fecha, lote_anterior, lote_nuevo, animales, notas, fecha_salida, dias_total, numero_rotacion)
HISTORIAL = [
    ('2025-12-31', None, 1, 81,  'Entrada 81 animales a L1 (55 Oct + 26 Ene)',             '2026-01-12', 13,   1),
    ('2026-01-13', 1,    2, 81,  'Rotación L1 → L2',                                        '2026-01-19', 7,    1),
    ('2026-01-20', 2,    5, 81,  'Rotación L2 → L5',                                        '2026-01-30', 10,   1),
    ('2026-01-30', 5,    4, 81,  'Rotación L5 → L4',                                        '2026-02-16', 18,   1),
    ('2026-02-16', 4,    8, 81,  'Rotación L4 → L8',                                        '2026-02-27', 12,   1),
    ('2026-02-27', 8,    6, 106, 'Rotación L8 → L6. 9 mar: llegan 25 animales, total 106.', '2026-03-14', 15,   1),
    ('2026-03-14', 6,    3, 106, 'Rotación L6 → L3',                                        '2026-03-18', 5,    1),
    ('2026-03-18', 3,    1, 106, 'Rotación L3 → L1. Segunda rotación en L1.',               '2026-03-28', 10,   2),
    ('2026-03-28', 1,    2, 106, 'Rotación L1 → L2. Segunda rotación en L2.',               None,         None, 2),
]

with sqlite3.connect(DB_PATH) as conn:
    existing = conn.execute("SELECT COUNT(*) FROM rotacion_lotes").fetchone()[0]
    print(f"Entradas actuales en DB: {existing}")

    conn.execute("DELETE FROM rotacion_lotes")
    print("✓ Tabla limpiada")

    for row in HISTORIAL:
        conn.execute("""
            INSERT INTO rotacion_lotes
                (fecha, lote_anterior, lote_nuevo, animales, notas,
                 fecha_salida, dias_total, numero_rotacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, row)

    print(f"✓ Insertadas {len(HISTORIAL)} rotaciones\n")

    rows = conn.execute(
        "SELECT id, fecha, lote_anterior, lote_nuevo, numero_rotacion, fecha_salida "
        "FROM rotacion_lotes ORDER BY fecha"
    ).fetchall()

    for r in rows:
        ant = f'L{r[2]}' if r[2] else 'inicio'
        salida = r[5] or 'ACTIVA'
        print(f"  [{r[0]}] {r[1]}  {ant} → L{r[3]}  rotación #{r[4]}  salida: {salida}")

print("\n✓ Migración completa. El bot calculará rotaciones correctamente de ahora en adelante.")
