"""AES-GCM-versleuteling met een sleutel afgeleid van de toegangscode (PBKDF2-SHA256)."""
import base64, json, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 310000

def _key(code, salt, it):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=it).derive(code.encode())

def encrypt(obj, code, extra=None):
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(code, salt, ITER)).encrypt(iv, json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode(), None)
    out = {'v': 1, 'iter': ITER, 'salt': base64.b64encode(salt).decode(), 'iv': base64.b64encode(iv).decode(), 'ct': base64.b64encode(ct).decode()}
    out.update(extra or {})
    return out

def decrypt(env, code):
    salt, iv, ct = (base64.b64decode(env[k]) for k in ('salt', 'iv', 'ct'))
    return json.loads(AESGCM(_key(code, salt, env['iter'])).decrypt(iv, ct, None))
