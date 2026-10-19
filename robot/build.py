"""Base do dash do contencioso: puxar, validar, calcular prazos internos, criptografar e publicar.

  python robot/build.py --pull     git pull + decripta data/demandas.enc.json em private/demandas.json
  python robot/build.py            valida, calcula prazo interno e gera data/demandas.enc.json
  python robot/build.py --push     idem + commit + push

A versão publicada (criptografada) é a fonte da verdade.
"""
import json, subprocess, sys
from datetime import date, datetime, timedelta, timezone

import lib
from lib import OUT, ROOT, decrypt, encrypt, senha

lib.SRC = ROOT / "private" / "demandas.json"
SRC = lib.SRC

STATUS = ["entrada", "a_fazer", "elaboracao", "revisao", "aguardando_cliente",
          "protocolar", "aguardando_orgao", "concluido"]
ESFERAS = {"judicial", "administrativo", "interno"}
# Prazo interno padrão: dias úteis antes do prazo fatal (peça pronta e revisada até essa data)
FOLGA_INTERNA = 2

git = lambda *a, **kw: subprocess.run(["git", *a], cwd=ROOT, **kw)


def load():
    return json.loads(SRC.read_text(encoding="utf-8"))


def save(db):
    SRC.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")


def menos_uteis(d: date, n: int) -> date:
    while n > 0:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def validar(db):
    erros, ids = [], set()
    for x in db["demandas"]:
        i = x.get("id")
        if not i or i in ids:
            erros.append(f"id ausente ou repetido: {i}")
        ids.add(i)
        if x.get("status") not in STATUS:
            erros.append(f"{i}: status inválido {x.get('status')}")
        if x.get("esfera") not in ESFERAS:
            erros.append(f"{i}: esfera inválida {x.get('esfera')}")
        for c in ("prazo_fatal", "prazo_interno", "proxima_data", "ultimo_movimento", "status_desde", "responsavel_desde", "criado_em"):
            v = x.get(c)
            if v:
                try:
                    date.fromisoformat(v)
                except ValueError:
                    erros.append(f"{i}: {c} fora do formato AAAA-MM-DD: {v}")
    if erros:
        sys.exit("demandas.json inválido:\n  " + "\n  ".join(erros))


def trilha(x, hoje):
    """Registra cada mudança de status e de responsável (métricas de tempo por status e por pessoa)."""
    t = x.setdefault("trilha", [])
    mudou_status = not t or t[-1]["status"] != x["status"]
    mudou_resp = not t or t[-1].get("responsavel") != x.get("responsavel")
    if not (mudou_status or mudou_resp):
        return
    # o robô grava status_desde / responsavel_desde com a data da mensagem; se não gravou, vale hoje
    ultimo = t[-1]["data"] if t else ""
    def data_de(campo):
        v = x.get(campo) or ""
        return v if (not t or v > ultimo) else hoje
    if mudou_status:
        x["status_desde"] = data_de("status_desde") or hoje
    if mudou_resp:
        x["responsavel_desde"] = data_de("responsavel_desde") or x.get("status_desde") or hoje
    t.append({"status": x["status"], "responsavel": x.get("responsavel"), "data": x["status_desde"] if mudou_status else x["responsavel_desde"]})


def pull():
    git("pull", "--rebase", "--autostash", "-q", check=True)
    remoto = decrypt(json.loads(OUT.read_text(encoding="utf-8")), senha())
    SRC.parent.mkdir(exist_ok=True)
    local = load() if SRC.exists() else {}
    if local.get("publicado_em", "") > remoto.get("publicado_em", ""):
        print(f"local ({local['publicado_em']}) é mais novo que o publicado: mantido o local")
        return
    save(remoto)
    print(f"base atualizada a partir do publicado em {remoto.get('publicado_em')} ({len(remoto['demandas'])} demandas)")


def build(push):
    db = load()
    validar(db)
    hoje = date.today().isoformat()
    calc = 0
    for x in db["demandas"]:
        x.setdefault("criado_em", hoje)
        x.setdefault("ultimo_movimento", x["criado_em"])
        trilha(x, hoje)
        if x.get("prazo_fatal") and (not x.get("prazo_interno") or x.get("prazo_interno_auto")):
            x["prazo_interno"] = menos_uteis(date.fromisoformat(x["prazo_fatal"]), FOLGA_INTERNA).isoformat()
            x["prazo_interno_auto"] = True
            calc += 1
    db["publicado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save(db)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(encrypt(json.dumps(db, ensure_ascii=False).encode(), senha())), encoding="utf-8")
    print(f"{len(db['demandas'])} demandas publicadas ({calc} prazos internos calculados)")
    if push:
        git("add", "data/demandas.enc.json", check=True)
        git("commit", "-q", "-m", f"dados: sync {datetime.now():%Y-%m-%d %H:%M}", check=True)
        if git("push", "-q").returncode:
            git("pull", "--rebase", "-X", "theirs", "-q", check=True)
            git("push", "-q", check=True)
        print("publicado no GitHub")


if __name__ == "__main__":
    pull() if "--pull" in sys.argv else build("--push" in sys.argv)
