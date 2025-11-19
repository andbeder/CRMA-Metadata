"""
Salesforce JWT Authentication
Python port of sfdcJwtAuth.js
"""
import os
import time
import json
import hashlib
import subprocess
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import requests

class TokenCache:
    """In-memory token cache"""
    def __init__(self):
        self.access_token = None
        self.instance_url = None
        self.expiry = None

    def is_valid(self):
        """Check if cached token is still valid"""
        if not self.access_token or not self.expiry:
            return False
        return time.time() < self.expiry

    def set(self, access_token, instance_url, lifetime_seconds=7200):
        """Cache a new token"""
        self.access_token = access_token
        self.instance_url = instance_url
        self.expiry = time.time() + lifetime_seconds

    def clear(self):
        """Clear the cache"""
        self.access_token = None
        self.instance_url = None
        self.expiry = None


class SalesforceJWTAuth:
    """Salesforce JWT Authentication Handler"""

    def __init__(self, client_id=None, username=None, login_url=None,
                 encrypted_key_path=None, key_pass=None):
        """
        Initialize the JWT authentication handler

        Args:
            client_id: Salesforce connected app client ID
            username: Salesforce username
            login_url: Salesforce login URL
            encrypted_key_path: Path to encrypted JWT key file
            key_pass: Password to decrypt the JWT key
        """
        from config import Config

        self.client_id = client_id or Config.SFDC_CLIENT_ID
        self.username = username or Config.SFDC_USERNAME
        self.login_url = login_url or Config.SFDC_LOGIN_URL
        self.encrypted_key_path = encrypted_key_path or Config.ENCRYPTED_KEY_FILE
        self.key_pass = key_pass or Config.KEY_PASS
        self.instance_url = Config.SF_INSTANCE_URL or self.login_url

        self.token_cache = TokenCache()
        self.alias = "myJwtOrg"

    def decrypt_jwt_key(self):
        """
        Decrypt the encrypted JWT key file using AES-256-CBC with PBKDF2
        Compatible with OpenSSL encryption
        """
        try:
            with open(self.encrypted_key_path, 'rb') as f:
                encrypted_data = f.read()

            # OpenSSL format: "Salted__" + 8-byte salt + encrypted data
            if encrypted_data[:8] != b'Salted__':
                raise ValueError('Invalid OpenSSL encrypted file format')

            salt = encrypted_data[8:16]
            encrypted = encrypted_data[16:]

            # Derive key and IV using PBKDF2 (matching OpenSSL's EVP_BytesToKey)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=48,  # 32 bytes for key + 16 bytes for IV
                salt=salt,
                iterations=10000,
                backend=default_backend()
            )
            key_and_iv = kdf.derive(self.key_pass.encode('utf-8'))
            key = key_and_iv[:32]
            iv = key_and_iv[32:48]

            # Decrypt
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted) + decryptor.finalize()

            # Remove PKCS7 padding
            padding_length = decrypted[-1]
            decrypted = decrypted[:-padding_length]

            return decrypted.decode('utf-8')

        except Exception as e:
            raise Exception(f"Failed to decrypt JWT key: {str(e)}")

    def is_token_accepted(self, token, instance_url):
        """
        Verify if a token is valid by making a test API call
        """
        try:
            headers = {'Authorization': f'Bearer {token}'}
            url = f"{instance_url}/services/data/v60.0"
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def authorize(self):
        """
        Perform JWT-based SFDX login and return access token
        Returns: dict with 'accessToken' and 'instanceUrl'
        """
        # Validate required configuration
        if not self.key_pass:
            raise ValueError("KEY_PASS is required to decrypt JWT key")
        if not self.client_id:
            raise ValueError("SFDC_CLIENT_ID is required")
        if not self.username:
            raise ValueError("SFDC_USERNAME is required")

        try:
            # Check for environment token first
            env_token = os.environ.get('SF_ACCESS_TOKEN')
            if env_token:
                if self.is_token_accepted(env_token, self.instance_url):
                    print("✔ Using SF_ACCESS_TOKEN from environment")
                    self.token_cache.set(env_token, self.instance_url)
                    return {
                        'accessToken': env_token,
                        'instanceUrl': self.instance_url
                    }
                print("ℹ Provided SF_ACCESS_TOKEN was rejected; obtaining new token...")

            # Check cached token
            if self.token_cache.is_valid():
                if self.is_token_accepted(self.token_cache.access_token, self.instance_url):
                    print("✔ Reusing cached access token")
                    os.environ['SF_ACCESS_TOKEN'] = self.token_cache.access_token
                    os.environ['SF_INSTANCE_URL'] = self.token_cache.instance_url
                    return {
                        'accessToken': self.token_cache.access_token,
                        'instanceUrl': self.token_cache.instance_url
                    }
                print("ℹ Cached access token rejected; obtaining new token...")
                self.token_cache.clear()
            elif self.token_cache.access_token:
                print("ℹ Cached token expired; obtaining new token...")
                self.token_cache.clear()

            # Decrypt the JWT key
            decrypted_key = self.decrypt_jwt_key()

            # Create temporary file with restricted permissions
            import tempfile
            import secrets
            temp_dir = Path('tmp')
            temp_dir.mkdir(exist_ok=True)

            temp_key_file = temp_dir / f"jwt_{int(time.time())}_{secrets.token_hex(4)}.key"

            try:
                # Write with restricted permissions
                temp_key_file.write_text(decrypted_key)
                os.chmod(temp_key_file, 0o600)

                # Log in via JWT using sf CLI
                cmd = [
                    'sf', 'org', 'login', 'jwt',
                    '-i', self.client_id,
                    '--jwt-key-file', str(temp_key_file),
                    '--username', self.username,
                    '--alias', self.alias,
                    '--instance-url', self.login_url,
                    '--set-default'
                ]

                # Use shell=True on Windows to find sf.cmd
                subprocess.run(cmd, check=True, capture_output=True, text=True, shell=True)

            finally:
                # Securely delete temporary key file
                if temp_key_file.exists():
                    # Overwrite with random data
                    temp_key_file.write_bytes(os.urandom(len(decrypted_key)))
                    temp_key_file.unlink()

            # Retrieve org info as JSON
            result = subprocess.run(
                ['sf', 'org', 'display', '--target-org', self.alias, '--json'],
                capture_output=True,
                text=True,
                check=True,
                shell=True
            )

            info = json.loads(result.stdout).get('result', {})
            token = info.get('accessToken')

            if not token:
                raise ValueError("No accessToken found in sf org display output")

            if info.get('instanceUrl'):
                self.instance_url = info['instanceUrl']
                os.environ['SF_INSTANCE_URL'] = self.instance_url

            os.environ['SF_ACCESS_TOKEN'] = token

            # Cache token in memory
            self.token_cache.set(token, self.instance_url)
            print("✔ Access token cached in memory")

            return {
                'accessToken': token,
                'instanceUrl': self.instance_url
            }

        except Exception as e:
            raise Exception(f"Error during JWT login: {str(e)}")

    def get_token(self):
        """
        Get a valid access token (from cache or by authenticating)
        Returns: dict with 'accessToken' and 'instanceUrl'
        """
        if self.token_cache.is_valid():
            return {
                'accessToken': self.token_cache.access_token,
                'instanceUrl': self.token_cache.instance_url
            }
        return self.authorize()
