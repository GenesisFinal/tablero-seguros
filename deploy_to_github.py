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
from datetime import datetime

# Windows console encoding fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

def update_file_on_github(repo, headers, path_in_repo, local_file_path, commit_message, max_retries=3):
    if not os.path.exists(local_file_path):
        print(f"[AVISO] Archivo local {local_file_path} no existe.")
        return False

    with open(local_file_path, "rb") as f:
        content_bytes = f.read()

    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"

    for attempt in range(1, max_retries + 1):
        resp = requests.get(url, headers=headers)
        sha = None
        if resp.status_code == 200:
            sha = resp.json().get("sha")

        payload = {
            "message": commit_message,
            "content": content_b64
        }
        if sha:
            payload["sha"] = sha

        print(f"  -> Subiendo {path_in_repo} ({len(content_bytes):,} bytes)...")
        put_resp = requests.put(url, headers=headers, json=payload)

        if put_resp.status_code in [200, 201]:
            print(f"  [OK] {path_in_repo} sincronizado exitosamente.")
            return True
        elif put_resp.status_code == 409:
            print(f"  [RETRY] Conflicto 409 para {path_in_repo}, reintentando en 1s...")
            time.sleep(1)
        else:
            print(f"  [ERROR] Falla al subir {path_in_repo}: {put_resp.status_code} - {put_resp.text}")
            time.sleep(1)

    return False

def deploy():
    print("=" * 75)
    print("  DESPLIEGUE OFICIAL A GITHUB & GITHUB PAGES")
    print("  Proyecto: Tablero de Seguros (SSN Argentina)")
    print("=" * 75)

    token = get_token()
    if not token:
        print("[ERROR CRITICO] Token de GitHub no disponible.")
        return False

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Mozilla/5.0"
    }

    # 1. Obtener usuario
    user_res = requests.get("https://api.github.com/user", headers=headers)
    if user_res.status_code != 200:
        print(f"[ERROR] Token invalido: {user_res.status_code}")
        return False
    user_login = user_res.json().get("login")
    repo = f"{user_login}/{REPO_NAME}"
    print(f"[OK] Conectado a GitHub como: {user_login}")

    # 2. Asegurar repositorio
    r_check = requests.get(f"https://api.github.com/repos/{repo}", headers=headers)
    if r_check.status_code == 404:
        print(f"[*] Creando repositorio '{repo}'...")
        create_payload = {
            "name": REPO_NAME,
            "description": REPO_DESC,
            "private": False,
            "auto_init": True
        }
        r_create = requests.post("https://api.github.com/user/repos", headers=headers, json=create_payload)
        if r_create.status_code not in [200, 201]:
            print(f"[ERROR] Error al crear repo: {r_create.status_code} - {r_create.text}")
            return False
        print("[OK] Repositorio creado.")
        time.sleep(2)
    else:
        print(f"[OK] Repositorio '{repo}' verificado.")

    # 3. Ejecutar actualizador y auditoría de datos local antes de subir
    print("\n1. Ejecutando actualizador de datos y auditoría SSN...")
    from actualizar_tablero import update_insurance_data
    update_insurance_data()

    # 4. Crear .nojekyll local si no existe
    nojekyll_path = os.path.join(BASE_DIR, ".nojekyll")
    if not os.path.exists(nojekyll_path):
        with open(nojekyll_path, "w", encoding="utf-8") as f:
            f.write("")

    # 5. Lista de archivos a subir
    print("\n2. Subiendo archivos al repositorio de GitHub...")
    files_to_upload = [
        (".nojekyll", nojekyll_path, "Bypass Jekyll build"),
        ("index.html", os.path.join(BASE_DIR, "index.html"), "Feat: Tablero interactivo SPA Mercado Asegurador"),
        ("README.md", os.path.join(BASE_DIR, "README.md"), "Docs: Manual y descripcion del proyecto"),
        ("actualizar_tablero.py", os.path.join(BASE_DIR, "actualizar_tablero.py"), "Feat: Script maestro de actualizacion de datos"),
        ("deploy_to_github.py", os.path.join(BASE_DIR, "deploy_to_github.py"), "Feat: Script de despliegue a GitHub Pages"),
        (".gitignore", os.path.join(BASE_DIR, ".gitignore"), "Chore: Configuracion .gitignore"),
        ("data/insurance_dataset.json", os.path.join(BASE_DIR, "data", "insurance_dataset.json"), "Data: Base de datos unificada SSN"),
        ("data/insurance_data.js", os.path.join(BASE_DIR, "data", "insurance_data.js"), "Data: Dataset JS para ejecucion directa"),
        ("src/verify_all_values.py", os.path.join(BASE_DIR, "src", "verify_all_values.py"), "Feat: Auditor y verificador diario de valores"),
        (".github/workflows/daily_update.yml", os.path.join(BASE_DIR, ".github", "workflows", "daily_update.yml"), "CI/CD: Workflow de auto-actualizacion y verificacion diaria")
    ]

    # Agregar scrapers
    scrapers_dir = os.path.join(BASE_DIR, "src", "scrapers")
    if os.path.exists(scrapers_dir):
        for sf in os.listdir(scrapers_dir):
            if sf.endswith(".py"):
                files_to_upload.append((
                    f"src/scrapers/{sf}",
                    os.path.join(scrapers_dir, sf),
                    f"Feat: Scraper SSN {sf}"
                ))

    success_count = 0
    for repo_path, local_path, msg in files_to_upload:
        if os.path.exists(local_path):
            if update_file_on_github(repo, headers, repo_path, local_path, msg):
                success_count += 1

    # 6. Habilitar y Configurar GitHub Pages
    print("\n3. Verificando configuracion de GitHub Pages...")
    pages_url = f"https://api.github.com/repos/{repo}/pages"
    r_pages = requests.get(pages_url, headers=headers)
    if r_pages.status_code == 404:
        pages_payload = {
            "source": {
                "branch": "main",
                "path": "/"
            }
        }
        r_page_create = requests.post(pages_url, headers=headers, json=pages_payload)
        if r_page_create.status_code in [200, 201]:
            print("  [OK] GitHub Pages habilitado correctamente.")
        else:
            print(f"  [INFO] Estado Pages: {r_page_create.status_code}")
    else:
        print("  [OK] GitHub Pages ya se encuentra activo.")

    print("\n" + "=" * 75)
    live_url = f"https://{user_login.lower()}.github.io/{REPO_NAME}/"
    repo_web = f"https://github.com/{user_login}/{REPO_NAME}"
    print(f"  [EXITO] {success_count} ARCHIVOS SINCRONIZADOS EXITOSAMENTE")
    print(f"  Repositorio GitHub: {repo_web}")
    print(f"  URL Publica (GitHub Pages): {live_url}")
    print("=" * 75)
    return True

if __name__ == "__main__":
    deploy()
