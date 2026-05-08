import os
import sys
import subprocess
from datetime import datetime

# Path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXEC = sys.executable

def run_script(script_name):
    print(f"--- Running {script_name} ---")
    res = subprocess.run([PYTHON_EXEC, script_name], cwd=BASE_DIR)
    if res.returncode != 0:
        print(f"ERROR: {script_name} failed!")
        return False
    return True

def main():
    print(f"Starting Local-to-Server Sync at {datetime.now()}")
    
    # 1. Update CSV with full data
    if not run_script("update_csv_local.py"): return
    
    # 2. Refresh specifically Dividends (optional but good for calendar)
    if os.path.exists("tmp/refresh_dividends.py"):
        if not run_script("tmp/refresh_dividends.py"): return
    
    # 3. Commit and Push to GitHub
    print("--- Pushing data to GitHub ---")
    try:
        subprocess.run(["git", "add", "stock_data.csv"], cwd=BASE_DIR)
        subprocess.run(["git", "commit", "-m", f"Automated Data Update {datetime.now().strftime('%Y-%m-%d')}"], cwd=BASE_DIR)
        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR)
    except Exception as e:
        print(f"Git Error: {e}")
        # Not fatal if already up to date
    
    # 4. Trigger Remote Deployment
    print("--- Triggering Remote Deploy via SSH ---")
    # Using the key that worked: id_rsa_antigravity_2048
    ssh_cmd = [
        "ssh", "-i", "C:/Users/fhofmann/.ssh/id_rsa_antigravity_2048",
        "ubuntu@3.71.191.12",
        "cd /home/ubuntu/aktien-tool2 && bash deploy.sh && sudo systemctl restart compare-app.service"
    ]
    res = subprocess.run(ssh_cmd)
    
    if res.returncode == 0:
        print("✅ SUCCESS: Data updated and deployed to server!")
    else:
        print("❌ FAILED: Deployment trigger failed.")

if __name__ == "__main__":
    main()
