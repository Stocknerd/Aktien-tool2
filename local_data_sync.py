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
        subprocess.run(["git", "add", "stock_data.csv"], cwd=BASE_DIR, check=True)
        # Check if there are changes
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=BASE_DIR)
        if status.stdout:
            subprocess.run(["git", "commit", "-m", f"Automated Data Update {datetime.now().strftime('%Y-%m-%d')}"], cwd=BASE_DIR, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=True)
            print("Git Push: Done.")
        else:
            print("Git Push: No data changes detected.")
    except Exception as e:
        print(f"Git Warning: {e}")
    
    # 4. Trigger Remote Deployment
    print("--- Triggering Remote Deploy via SSH ---")
    
    possible_keys = [
        os.path.join(os.path.expanduser("~"), ".ssh", "id_rsa_antigravity_2048"),
        os.path.join(os.path.expanduser("~"), "Downloads", "LightsailDefaultKey-eu-central-1.pem"),
        "C:/Users/fhofm/Downloads/LightsailDefaultKey-eu-central-1.pem",
        os.path.join(os.path.expanduser("~"), ".ssh", "aws-eb")
    ]
    ssh_key = None
    for key in possible_keys:
        if os.path.exists(key):
            ssh_key = key
            break
            
    if not ssh_key:
        print("ERROR: No suitable SSH key found for deployment.")
        return
        
    print(f"Using SSH key: {ssh_key}")

    ssh_cmd = [
        "ssh", "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "ubuntu@3.71.191.12",
        "cd /home/ubuntu/aktien-tool2 && bash deploy.sh && sudo systemctl restart aktien-tool.service"
    ]
    res = subprocess.run(ssh_cmd)
    
    if res.returncode == 0:
        print("\n" + "="*40)
        print("✅ SUCCESS: Data updated and deployed to server!")
        print("="*40)
    else:
        print("\n" + "="*40)
        print("❌ FAILED: Deployment trigger failed.")
        print("="*40)

if __name__ == "__main__":
    main()
