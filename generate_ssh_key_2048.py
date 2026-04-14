import subprocess
import os

key_path = r"C:\Users\fhofmann\.ssh\id_rsa_antigravity_2048"

# Check if .ssh directory exists
ssh_dir = os.path.dirname(key_path)
if not os.path.exists(ssh_dir):
    os.makedirs(ssh_dir)

# 2048-bit RSA for better compatibility with older SSH implementations
cmd = ["ssh-keygen", "-t", "rsa", "-b", "2048", "-f", key_path, "-N", "", "-C", "Antigravity_WP_Sync"]

print(f"Executing: {' '.join(cmd)}")
try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    if result.returncode == 0:
        print("Success! 2048-bit SSH Key generated.")
        pub_path = key_path + ".pub"
        with open(pub_path, "r") as f:
            print("\n--- PUBLIC KEY (2048) ---")
            print(f.read().strip())
            print("-------------------------\n")
    else:
        print(f"Error: {result.stderr}")
except Exception as e:
    print(f"Exception: {e}")
