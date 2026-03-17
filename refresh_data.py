#!/usr/bin/env python3
# refresh_data.py – Wrapper für Hintergrund-Aktualisierung
import os, subprocess, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPDATE_SCRIPT = BASE_DIR / "update_csv.py"

def run_refresh():
    print(f"--- Starte Daten-Refresh: {UPDATE_SCRIPT} ---")
    # Wir setzen QUICK=1 für einen schnelleren Durchlauf, falls gewünscht
    # env = os.environ.copy()
    # env["QUICK"] = "1"
    
    try:
        # Führe das bestehende Update-Skript aus
        result = subprocess.run(
            [sys.executable, str(UPDATE_SCRIPT)],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("--- Refresh erfolgreich beendet ---")
    except subprocess.CalledProcessError as e:
        print(f"--- FEHLER beim Refresh ---")
        print(e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_refresh()
