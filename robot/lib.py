"""Funções comuns do robô: caminhos, criptografia, leitura/gravação da base e busca de leads."""
import base64, json, os, re, unicodedata
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "private" / "leads.json"
KEY = ROOT / "private" / ".senha"
OUT = ROOT / "data" / "demandas.enc.json"
ITER = 310_000

STOP = {"ltda", "sa", "s", "a", "grupo", "de", "do", "da", "e", "the", "advogados", "advocacia", "contabilidade",
        "construtora", "empreendimentos", "industria", "comercio", "brasil", "do", "dos", "das", "&", "cia"}


def senha() -> str:
    # na nuvem a senha vem da variável DASH_SENHA; no PC, de private/.senha
    return os.environ.get("DASH_SENHA") or KEY.read_text(encoding="utf-8").strip()


def _kdf(salt: bytes, pw: str) -> bytes:
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw.encode())


def encrypt(payload: bytes, pw: str) -> dict:
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_kdf(salt, pw)).encrypt(iv, payload, None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITER, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def decrypt(blob: dict, pw: str) -> dict:
    d = lambda s: base64.b64decode(s)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=d(blob["salt"]), iterations=blob["iter"]).derive(pw.encode())
    return json.loads(AESGCM(key).decrypt(d(blob["iv"]), d(blob["ct"]), None))


def load() -> dict:
    return json.loads(SRC.read_text(encoding="utf-8"))


def save(db: dict):
    SRC.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def slug(s: str) -> str:
    return norm(s).replace(" ", "-")[:40]


def tokens(empresa: str) -> set:
    return {t for t in norm(empresa).split() if t not in STOP and len(t) > 2}


def find_lead(db: dict, empresa: str = "", nome: str = "", email: str = ""):
    """Acha o lead por e-mail, depois por empresa (tokens em comum) + nome. Devolve o lead ou None."""
    if email:
        e = email.lower()
        for l in db["leads"]:
            if e in [x.lower() for x in l.get("email", [])]:
                return l
    te = tokens(empresa)
    pn = norm(nome).split()
    best, score = None, 0
    for l in db["leads"]:
        common = te & tokens(l["empresa"])
        s = len(common) * 2
        ln = norm(l["nome"])
        if pn and pn[0] in ln.split():
            s += 1
        if s > score:
            best, score = l, s
    return best if score >= 2 else None
