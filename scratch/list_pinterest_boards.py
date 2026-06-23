#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

def main():
    # Load existing env
    load_dotenv()
    
    token = os.environ.get("PINTEREST_ACCESS_TOKEN")
    
    print("=========================================================")
    print("Pinterest Boards Finder (Using Access Token Only)")
    print("=========================================================")
    
    if not token:
        print("PINTEREST_ACCESS_TOKEN wurde nicht in der .env gefunden.")
        token = input("Bitte füge deinen 30-Tage Pinterest Access Token ein: ").strip()
        if not token:
            print("[ERR] Kein Token eingegeben. Abbruch.")
            return
    else:
        print("Nutze den PINTEREST_ACCESS_TOKEN aus der .env-Datei.")
        
    url = "https://api.pinterest.com/v5/boards"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\nRufe Pinterest Boards ab...")
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            items = data.get("items", [])
            if not items:
                print("\n[OK] Verbindung erfolgreich, aber keine Boards gefunden.")
                print("Bitte erstelle zuerst ein Board auf Pinterest.com.")
            else:
                print("\n🎉 Verbindung erfolgreich! Folgende Boards wurden gefunden:")
                print("-" * 60)
                print(f"{'BOARD ID':<25} | {'NAME'}")
                print("-" * 60)
                for item in items:
                    print(f"{item.get('id'):<25} | {item.get('name')}")
                print("-" * 60)
                print("\nWähle die ID deines gewünschten Boards aus und trage sie in deine .env ein:")
                print(f"PINTEREST_ACCESS_TOKEN={token}")
                print("PINTEREST_BOARD_ID=deine_ausgewaehlte_board_id")
        else:
            print(f"\n[ERR] Pinterest API Fehler ({r.status_code}): {r.text}")
            print("Stelle sicher, dass der Token noch gültig ist und die nötigen Berechtigungen (boards:read) besitzt.")
    except Exception as e:
        print(f"\n[ERR] Verbindung fehlgeschlagen: {e}")

if __name__ == "__main__":
    main()
