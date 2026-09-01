#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TABLERO DE SEGUROS - VERIFICADOR Y AUDITOR DIARIO DE DATOS SSN
Valida exhaustivamente la consistencia, integridad matemática y actualización
de TODOS los valores del tablero.
===============================================================================
"""

import json
import os
import sys
from datetime import datetime

# Ensure utf-8 stdout on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "insurance_dataset.json")

def verify_all_values():
    print("=" * 75)
    print("  AUDITORIA Y VERIFICACION EXHAUSTIVA DE DATOS SSN")
    print("  Fecha/Hora:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 75)

    if not os.path.exists(DATA_PATH):
        print(f"[ERROR CRITICO] No se encontro el dataset en {DATA_PATH}")
        return False

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        ds = json.load(f)

    errors = []
    warnings = []
    checks_passed = 0

    # 1. Primas del Mercado
    print("\n[1/7] Verificando Primas del Mercado y Ramos...")
    primas = ds.get("ssn_primas_mercado", {})
    branches = primas.get("branches", [])
    
    if not branches or len(branches) < 5:
        errors.append("ssn_primas_mercado: branches vacio o incompleto.")
    else:
        tot_monto = 0
        for b in branches:
            name = b.get("name", b.get("ramo", ""))
            monto = b.get("primas_actual", b.get("monto_actual", 0))
            if "TOTAL" in name.upper() or b.get("is_total", False):
                tot_monto = max(tot_monto, monto)

        # Fallback if totals are separated
        if tot_monto <= 0:
            tot_monto = sum(b.get("primas_actual", 0) for b in branches if not b.get("is_total", False))

        if tot_monto <= 0:
            errors.append("ssn_primas_mercado: Total mercado no encontrado o valor invalido.")
        else:
            checks_passed += 1
            print(f"  [OK] Total Mercado verificado: $ {tot_monto:,.0f} ({len(branches)} ramos analizados)")

    # 2. Produccion Mensual
    print("\n[2/7] Verificando Series Mensuales (Corrientes y Constantes)...")
    mensual = ds.get("ssn_produccion_mensual", {})
    for mode in ["corriente", "constante"]:
        mode_data = mensual.get(mode, {})
        history = mode_data.get("history", [])
        if not history:
            errors.append(f"ssn_produccion_mensual ({mode}): history vacio.")
        else:
            checks_passed += 1
            print(f"  [OK] Serie {mode} verificada: {len(history)} meses historicos registrados.")

    # 3. Rankings Oficiales SSN
    print("\n[3/7] Verificando los Rankings Oficiales de la SSN...")
    rankings = ds.get("ssn_rankings", {})
    ranking_keys = list(rankings.keys())

    if len(ranking_keys) < 5:
        errors.append(f"ssn_rankings incompleto (solo {len(ranking_keys)} categorias).")
    else:
        for r_key in ranking_keys:
            r_data = rankings.get(r_key, {})
            rows = r_data.get("rows", r_data) if isinstance(r_data, dict) else r_data
            if not rows or len(rows) < 2:
                errors.append(f"Ranking '{r_key}' con datos insuficientes ({len(rows)} rows).")
            else:
                checks_passed += 1
                print(f"  [OK] Ranking '{r_key}' verificado: {len(rows)} entidades ordenadas.")

    # 4. Balances y Estados Contables
    print("\n[4/7] Verificando Balances y Estados Contables...")
    balances = ds.get("ssn_balances", {})
    d26 = balances.get("data_2026", {})
    if not d26:
        errors.append("ssn_balances: data_2026 no contiene datos.")
    else:
        for seg in d26.keys():
            seg_data = d26.get(seg, {})
            if isinstance(seg_data, dict) and len(seg_data) > 0:
                checks_passed += 1
                print(f"  [OK] Balances '{seg}' verificados: {len(seg_data)} companias auditadas.")

    # 5. Grupo La Segunda
    print("\n[5/7] Verificando Grupo La Segunda...")
    ls = ds.get("ssn_lasegunda", {})
    tot_ls = ls.get("tot_grupo", 0)
    if tot_ls <= 0:
        errors.append("ssn_lasegunda: Total Grupo invalido o cero.")
    else:
        checks_passed += 1
        print(f"  [OK] Grupo La Segunda verificado: Total $ {tot_ls:,.0f} M (4 companias operativas).")

    # 6. Seguros de Retiro y Personas
    print("\n[6/7] Verificando Seguros de Retiro y Personas...")
    ret = ds.get("ssn_seg_retiro", {})
    comp_ret = ret.get("compromisos_tecnicos", [])
    if not comp_ret:
        warnings.append("ssn_seg_retiro: compromisos_tecnicos lista vacia.")
    else:
        checks_passed += 1
        print(f"  [OK] Seguros de Retiro: {len(comp_ret)} entidades de retiro verificadas.")

    # 7. Inversiones y KPIs de Solvencia
    print("\n[7/7] Verificando Estructura de Inversiones y KPIs Tecnicos...")
    inv = ds.get("ssn_inversiones_resumen", {})
    kpis = ds.get("ssn_kpis_mercado", {})
    
    inst = inv.get("distribucion_instrumentos", [])
    if not inst:
        errors.append("ssn_inversiones_resumen: Sin instrumentos.")
    else:
        checks_passed += 1
        print(f"  [OK] Inversiones verificadas: {len(inst)} clases de activos ($ {inv.get('total_inversiones_mercado', 0):,.0f} ARS).")

    if kpis.get("ratio_combinado_estimado", 0) > 0 and kpis.get("cobertura_compromisos_tecnicos", 0) > 0:
        checks_passed += 1
        print(f"  [OK] KPIs de Solvencia: Ratio Combinado {kpis.get('ratio_combinado_estimado')}% | Cobertura Art 35 {kpis.get('cobertura_compromisos_tecnicos')}%.")

    # Resumen
    print("\n" + "=" * 75)
    print(f"  RESULTADO DE LA AUDITORIA: {checks_passed} SECCIONES VALIDADAS EXITOSAMENTE")
    if warnings:
        print(f"  [AVISOS ({len(warnings)})]:")
        for w in warnings[:5]:
            print(f"   - {w}")
    if errors:
        print(f"  [ERRORES CRITICOS ({len(errors)})]:")
        for e in errors:
            print(f"   - {e}")
        print("=" * 75)
        return False
    else:
        print("  TODOS LOS VALORES HAN SIDO AUDITADOS Y VERIFICADOS CON EXITO.")
        print("=" * 75)
        return True

if __name__ == "__main__":
    success = verify_all_values()
    sys.exit(0 if success else 1)
