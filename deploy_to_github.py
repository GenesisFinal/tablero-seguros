#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
TABLERO DE SEGUROS - MERCADO ASEGURADOR ARGENTINO
Script de Despliegue Automatizado a GitHub (API REST) y GitHub Pages
===============================================================================
"""

import os
import sys
import requests
import base64
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "GitHub token.txt")
REPO_NAME = "tablero-seguros"
REPO_DESC = "Tablero de Control del Mercado Asegurador Argentino - SSN & Brandbook La Segunda"

def get_token():
    if not os.path.exists(TOKEN_FILE):
        print(f"[ERROR] No se encontro el archivo de token en {TOKEN_FILE}")
        return None
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.read().splitlines() if l.strip().startswith("ghp_") or l.strip().startswith("github_pat_")]
        if lines:
            return lines[0]
    return None

def upload_file(repo, headers, path_in_repo, local_file_path, msg):
    if not os.path.exists(local_file_path):
        return False

    with open(local_file_path, "rb") as f:
        content_bytes = f.read()

    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"

    resp = requests.get(url, headers=headers)
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    payload = {"message": msg, "content": content_b64}
    if sha:
        payload["sha"] = sha

    print(f"  -> Subiendo {path_in_repo} ({len(content_bytes):,} bytes)...")
    put_resp = requests.put(url, headers=headers, json=payload)
    if put_resp.status_code in [200, 201]:
        print(f"  [OK] {path_in_repo} subido con exito.")
        return True
    else:
        print(f"  [ERROR] {path_in_repo}: {put_resp.status_code} - {put_resp.text}")
        return False

def main():
    print("=" * 75)
    print("  DESPLIEGUE A GITHUB: TABLERO DE SEGUROS")
    print("=" * 75)

    token = get_token()
    if not token:
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Mozilla/5.0"
    }

    user_res = requests.get("https://api.github.com/user", headers=headers)
    user_login = user_res.json().get("login")
    repo = f"{user_login}/{REPO_NAME}"
    print(f"[OK] Usuario GitHub: {user_login}")
    print(f"[OK] Repositorio destino: {repo}")

    # Ensure repo exists
    r_check = requests.get(f"https://api.github.com/repos/{repo}", headers=headers)
    if r_check.status_code == 404:
        print(f"[*] Creando repositorio '{repo}'...")
        r_create = requests.post("https://api.github.com/user/repos", headers=headers, json={
            "name": REPO_NAME,
            "description": REPO_DESC,
            "private": False,
            "auto_init": True
        })
        print(f"[OK] Repositorio creado: {r_create.status_code}")
        time.sleep(2)

    # Files to upload
    files = [
        (".nojekyll", os.path.join(BASE_DIR, ".nojekyll"), "Bypass Jekyll build"),
        ("index.html", os.path.join(BASE_DIR, "index.html"), "Feat: Tablero de Seguros SPA"),
        ("README.md", os.path.join(BASE_DIR, "README.md"), "Docs: Documentacion oficial"),
        ("actualizar_tablero.py", os.path.join(BASE_DIR, "actualizar_tablero.py"), "Feat: Actualizador maestro"),
        ("deploy_to_github.py", os.path.join(BASE_DIR, "deploy_to_github.py"), "Feat: Script de despliegue"),
        (".gitignore", os.path.join(BASE_DIR, ".gitignore"), "Chore: .gitignore"),
        ("data/insurance_dataset.json", os.path.join(BASE_DIR, "data", "insurance_dataset.json"), "Data: insurance_dataset.json"),
        ("data/insurance_data.js", os.path.join(BASE_DIR, "data", "insurance_data.js"), "Data: insurance_data.js"),
        ("src/verify_all_values.py", os.path.join(BASE_DIR, "src", "verify_all_values.py"), "Feat: Verificador diario"),
        (".github/workflows/daily_update.yml", os.path.join(BASE_DIR, ".github", "workflows", "daily_update.yml"), "CI/CD: Daily update workflow")
    ]

    scrapers_dir = os.path.join(BASE_DIR, "src", "scrapers")
    if os.path.exists(scrapers_dir):
        for sf in os.listdir(scrapers_dir):
            if sf.endswith(".py"):
                files.append((f"src/scrapers/{sf}", os.path.join(scrapers_dir, sf), f"Feat: Scraper {sf}"))

    uploaded = 0
    for repo_path, local_path, msg in files:
        if upload_file(repo, headers, repo_path, local_path, msg):
            uploaded += 1

    # Enable Pages
    pages_url = f"https://api.github.com/repos/{repo}/pages"
    r_pages = requests.get(pages_url, headers=headers)
    if r_pages.status_code == 404:
        requests.post(pages_url, headers=headers, json={"source": {"branch": "main", "path": "/"}})

    print("\n" + "=" * 75)
    print(f"  [EXITO] {uploaded} archivos sincronizados en GitHub!")
    print(f"  Repositorio: https://github.com/{repo}")
    print(f"  GitHub Pages: https://{user_login.lower()}.github.io/{REPO_NAME}/")
    print("=" * 75)

if __name__ == "__main__":
    main()
