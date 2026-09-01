import os
import io
import time
import hashlib
import requests
import pandas as pd

def fetch_ssn_inversiones_retiro():
    print("[SSN Inversiones Retiro] Fetching SSN Inversiones Retiro Data...")
    
    # Try current and recent period URLs
    periods = ["202603", "202512", "202509", "202506", "202503"]
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".cache", "ssn")
    os.makedirs(cache_dir, exist_ok=True)
    
    content = None
    period_found = "Marzo 2026"
    
    for p in periods:
        url = f"https://www.argentina.gob.ar/sites/default/files/ssn_{p}_inversiones_creditos_deudas.xlsx"
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        cache_file = os.path.join(cache_dir, f"{url_hash}.bin")
        
        if os.path.exists(cache_file) and time.time() - os.path.getmtime(cache_file) < 48 * 3600:
            with open(cache_file, "rb") as f:
                content = f.read()
                print(f"[SSN Inversiones Retiro] Loaded cached data for period {p}")
                break
        else:
            try:
                r = requests.get(url, verify=False, timeout=30)
                if r.status_code == 200 and len(r.content) > 10000:
                    content = r.content
                    with open(cache_file, "wb") as f:
                        f.write(content)
                    print(f"[SSN Inversiones Retiro] Successfully downloaded period {p}")
                    break
            except Exception as e:
                print(f"[SSN Inversiones Retiro] Failed period {p}: {e}")

    if not content:
        print("[SSN Inversiones Retiro] Could not retrieve any SSN Inversiones Excel file.")
        return None

    try:
        xls = pd.read_excel(io.BytesIO(content), sheet_name=None, header=None)
        sheet_inv = xls.get("Inversiones")
        if sheet_inv is None:
            for k in xls.keys():
                if "invers" in k.lower():
                    sheet_inv = xls[k]
                    break
                    
        if sheet_inv is None:
            print("[SSN Inversiones Retiro] Sheet 'Inversiones' not found.")
            return None

        # Find row with "EXCLUSIVAS RETIRO"
        start_row = None
        for i in range(len(sheet_inv)):
            val = str(sheet_inv.iloc[i, 2]).strip().upper() if pd.notnull(sheet_inv.iloc[i, 2]) else ""
            if "EXCLUSIVAS RETIRO" in val:
                start_row = i
                break
                
        if start_row is None:
            print("[SSN Inversiones Retiro] Could not find row 'EXCLUSIVAS RETIRO'.")
            return None

        # Helper to parse 10 rubros from a row
        def parse_row(row):
            def num(c):
                if c >= len(row.values):
                    return 0.0
                v = row.values[c]
                parsed = pd.to_numeric(v, errors='coerce')
                return float(parsed) if pd.notnull(parsed) else 0.0

            tp_cotiz = num(3)      # Col D (idx 3)
            tp_sin_cotiz = num(4)  # Col E (idx 4)
            acc_cotiz = num(6)     # Col G (idx 6)
            acc_sin_cotiz = num(7) # Col H (idx 7)
            ons = num(9)           # Col J (idx 9)
            fci = num(10)          # Col K (idx 10)
            ff = num(11)           # Col L (idx 11)
            pf = num(12)           # Col M (idx 12)
            prestamos = num(16)    # Col Q (idx 16)
            total = num(20)        # Col U (idx 20)
            
            sum_9 = tp_cotiz + tp_sin_cotiz + acc_cotiz + acc_sin_cotiz + ons + fci + ff + pf + prestamos
            otros = max(0.0, total - sum_9)
            
            def pct(val):
                return round((val / total * 100), 2) if total > 0 else 0.0

            items = [
                {"rubro": "Títulos Públicos con Cotización", "key": "tp_cotiz", "monto": tp_cotiz, "pct": pct(tp_cotiz)},
                {"rubro": "Títulos Públicos sin Cotización", "key": "tp_sin_cotiz", "monto": tp_sin_cotiz, "pct": pct(tp_sin_cotiz)},
                {"rubro": "Acciones con Cotización", "key": "acc_cotiz", "monto": acc_cotiz, "pct": pct(acc_cotiz)},
                {"rubro": "Acciones sin Cotización", "key": "acc_sin_cotiz", "monto": acc_sin_cotiz, "pct": pct(acc_sin_cotiz)},
                {"rubro": "Obligaciones Negociables (ONs)", "key": "ons", "monto": ons, "pct": pct(ons)},
                {"rubro": "Fondos Comunes de Inversión (FCI)", "key": "fci", "monto": fci, "pct": pct(fci)},
                {"rubro": "Fideicomisos Financieros (FF)", "key": "ff", "monto": ff, "pct": pct(ff)},
                {"rubro": "Plazos Fijos (PF)", "key": "pf", "monto": pf, "pct": pct(pf)},
                {"rubro": "Préstamos", "key": "prestamos", "monto": prestamos, "pct": pct(prestamos)},
                {"rubro": "Otros", "key": "otros", "monto": otros, "pct": pct(otros)}
            ]
            
            return {
                "total_inversiones": total,
                "items": items
            }

        total_exclusivas = parse_row(sheet_inv.iloc[start_row])
        
        empresas = {
            "TODAS": {
                "nombre": "Total Exclusivas Retiro",
                "total_inversiones": total_exclusivas["total_inversiones"],
                "items": total_exclusivas["items"]
            }
        }

        # Parse individual companies (rows start_row + 1 until end of block)
        curr = start_row + 1
        while curr < len(sheet_inv):
            name = str(sheet_inv.iloc[curr, 2]).strip().upper() if pd.notnull(sheet_inv.iloc[curr, 2]) else ""
            if not name or "TOTAL" in name or "EXCLUSIVAS" in name:
                break
            
            parsed_c = parse_row(sheet_inv.iloc[curr])
            display_name = name.title()
            if "La Segunda" in display_name or "Segunda" in display_name:
                display_name = "La Segunda Retiro"
                
            empresas[name] = {
                "nombre": display_name if display_name != name.title() else name,
                "total_inversiones": parsed_c["total_inversiones"],
                "items": parsed_c["items"]
            }
            curr += 1

        result = {
            "period": period_found,
            "empresas": empresas
        }
        
        print(f"[SSN Inversiones Retiro] Parsed successfully ({len(empresas)-1} companies).")
        return result

    except Exception as e:
        print(f"[SSN Inversiones Retiro] Error parsing SSN Inversiones Excel: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    data = fetch_ssn_inversiones_retiro()
    print("Keys in result:", list(data.keys()) if data else "None")
