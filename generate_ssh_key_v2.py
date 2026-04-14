import subprocess
import os

key_path = r"C:\Users\fhofmann\.ssh\id_rsa_antigravity"

# Check if .ssh directory exists
ssh_dir = os.path.dirname(key_path)
if not os.path.exists(ssh_dir):
    os.makedirs(ssh_dir)

# Prepare command as a list to avoid shell parsing issues
cmd = ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", key_path, "-N", "", "-C", "Antigravity_WP_Sync"]

print(f"Executing: {' '.join(cmd)}")
try:
    # Use shell=False to ensure the list is passed directly to the OS
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    if result.returncode == 0:
        print("Success! SSH Key generated.")
        # Read the public key
        pub_path = key_path + ".pub"
        if os.path.exists(pub_path):
            with open(pub_path, "r") as f:
                print("\n--- PUBLIC KEY ---")
                print(f.read().strip())
                print("------------------\n")
    else:
        print(f"Error: ssh-keygen failed with code {result.returncode}")
        print(f"Stderr: {result.stderr}")
        print(f"Stdout: {result.stdout}")
except Exception as e:
    print(f"Exception happened: {e}")
