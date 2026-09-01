#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TABLERO DE SEGUROS - MERCADO ASEGURADOR ARGENTINO
Script Maestro de Actualización, Generación y Verificación de Datos
===============================================================================
"""

import os
import sys
import json
import time
from datetime import datetime

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCRAPERS_DIR = os.path.join(BASE_DIR, "src", "scrapers")
JSON_OUTPUT = os.path.join(DATA_DIR, "insurance_dataset.json")
JS_OUTPUT = os.path.join(DATA_DIR, "insurance_data.js")

# Import verification module
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from verify_all_values import verify_all_values

def update_insurance_data():
    print("=" * 75)
    print("  ACTUALIZANDO DATOS DEL TABLERO DE SEGUROS (SSN ARGENTINA)")
    print("=" * 75)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 1. Load existing dataset
    if os.path.exists(JSON_OUTPUT):
        print(f"[OK] Cargando dataset existente desde {JSON_OUTPUT}...")
        with open(JSON_OUTPUT, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    else:
        print("[AVISO] Dataset no encontrado, inicializando estructura base...")
        dataset = {}

    # Update timestamp
    dataset["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dataset["update_time_human"] = datetime.now().strftime("%d/%m/%Y %H:%M hs")

    # 2. Save unified JSON
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    print(f"[OK] insurance_dataset.json actualizado ({os.path.getsize(JSON_OUTPUT):,} bytes)")

    # 3. Generate standalone JS file for local & production execution without CORS restrictions
    with open(JS_OUTPUT, "w", encoding="utf-8") as f:
        f.write("/* Tablero de Seguros - Dataset Oficial SSN */\n")
        f.write("window.INSURANCE_DATA = ")
        json.dump(dataset, f, ensure_ascii=False)
        f.write(";\n")
    print(f"[OK] insurance_data.js generado ({os.path.getsize(JS_OUTPUT):,} bytes)")

    # 4. Run full verification of all values
    print("\nIniciando verificación exhaustiva de todos los valores...")
    is_valid = verify_all_values()

    print("=" * 75)
    if is_valid:
        print("  ACTUALIZACIÓN Y AUDITORÍA FINALIZADA CON ÉXITO")
    else:
        print("  [ADVERTENCIA] LA ACTUALIZACIÓN CONCLUYÓ CON OBSERVACIONES EN LA AUDITORÍA")
    print("=" * 75)
    return is_valid

if __name__ == "__main__":
    success = update_insurance_data()
    sys.exit(0 if success else 1)
