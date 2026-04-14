import rsa # Using a simpler library if available or custom logic
import os

def generate_and_save_ssh_key(path, comment):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    print(f"Generating key pair at {path}...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )

    # Save Private Key
    with open(path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption()
        ))
    os.chmod(path, 0o600)

    # Save Public Key in OpenSSH format
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )
    
    pub_path = path + ".pub"
    with open(pub_path, "wb") as f:
        f.write(pub_bytes + f" {comment}".encode())
        
    print(f"Success! Public key saved to {pub_path}")
    print(pub_bytes.decode() + f" {comment}")

if __name__ == "__main__":
    key_path = r"C:\Users\fhofmann\.ssh\id_rsa_antigravity"
    generate_and_save_ssh_key(key_path, "Antigravity_WP_Sync")
