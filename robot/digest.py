"""Mensagem diária do Argos (HTML do Teams) para o grupo do contencioso, por pessoa.

  python robot/digest.py      grava private/digest.html e imprime o HTML

Seções (só aparecem se tiverem itens): fatal vencido, prazos de hoje e dos próximos 3 dias úteis,
aguardando cliente há mais de 5 dias, parados além do máximo, sem prazo, novas e concluídas desde o último dia útil.
A primeira linha começa com 🤖 para o robô não reprocessar a própria mensagem.
"""
import json
from datetime import date, timedelta
from html import escape

from lib import ROOT

SRC = ROOT / "private" / "demandas.json"
DASH = "https://veigalaw.github.io/contencioso/"
SLA = {"entrada": 1, "a_fazer": 3, "elaboracao": 5, "revisao": 2, "aguardando_cliente": 5, "protocolar": 1}
DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def mais_uteis(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def anterior_util(d):
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def item(x, extra=""):
    proc = f" · {escape(x['processo'])}" if x.get("processo") else ""
    prazos = []
    if x.get("prazo_fatal"):
        prazos.append(f"fatal {x['prazo_fatal'][8:10]}/{x['prazo_fatal'][5:7]}")
    if x.get("prazo_interno") and x.get("prazo_interno") != x.get("prazo_fatal"):
        prazos.append(f"interno {x['prazo_interno'][8:10]}/{x['prazo_interno'][5:7]}")
    pz = f" [{', '.join(prazos)}]" if prazos else ""
    return f"<li><b>{escape(x['cliente'])}</b>{proc}: {escape(x.get('proximo_passo') or x['providencia'])}{pz}{extra}</li>"


def secao(titulo, itens, fmt=item):
    if not itens:
        return ""
    pessoas = sorted({x.get("responsavel") or "Sem responsável" for x in itens})
    corpo = "".join(f"<p><i>{escape(p)}</i></p><ul>{''.join(fmt(x) for x in itens if (x.get('responsavel') or 'Sem responsável') == p)}</ul>" for p in pessoas)
    return f"<p><b>{titulo}</b> ({len(itens)})</p>{corpo}"


def main():
    db = json.loads(SRC.read_text(encoding="utf-8"))
    hoje = date.today()
    h = hoje.isoformat()
    lim3 = mais_uteis(hoje, 3).isoformat()
    desde = anterior_util(hoje).isoformat()
    ab = [x for x in db["demandas"] if x["status"] != "concluido"]
    agenda = lambda x: x.get("prazo_interno") or x.get("prazo_fatal") or x.get("proxima_data") or ""
    parado = lambda x: (hoje - date.fromisoformat(x["ultimo_movimento"])).days if x.get("ultimo_movimento") else 0

    vencidos = [x for x in ab if x.get("prazo_fatal") and x["prazo_fatal"] < h]
    venc_ids = {x["id"] for x in vencidos}
    hoje_l = [x for x in ab if x["id"] not in venc_ids and (agenda(x) <= h and agenda(x))]
    prox = [x for x in ab if x["id"] not in venc_ids and h < agenda(x) <= lim3]
    cliente = [x for x in ab if x["status"] == "aguardando_cliente" and parado(x) > 5]
    parados = [x for x in ab if x["status"] in SLA and x["status"] != "aguardando_cliente" and parado(x) > SLA[x["status"]]
               and x not in hoje_l and x not in prox and x["id"] not in venc_ids]
    sem_prazo = [x for x in ab if not x.get("prazo_fatal") and not x.get("proxima_data")]
    novas = [x for x in db["demandas"] if (x.get("criado_em") or "") >= desde]
    concl = [x for x in db["demandas"] if x["status"] == "concluido" and (x.get("status_desde") or "") >= desde]

    p = [f"<p>🤖 <b>Argos · agenda do contencioso ({DOW[hoje.weekday()]} {hoje:%d/%m})</b></p>"]
    if concl:
        p.append("<p>✅ <b>Concluídas</b></p><ul>" + "".join(f"<li>{escape(x['cliente'])}: {escape(x['providencia'])}</li>" for x in concl) + "</ul>")
    if novas:
        p.append("<p>🆕 <b>Novas demandas</b></p><ul>" + "".join(item(x, f" · {escape(x.get('responsavel') or 'sem responsável')}") for x in novas) + "</ul>")
    duv = [f"<b>{escape(x['cliente'])}</b>: {escape(x['duvida'])}" for x in db["demandas"] if x.get("duvida")] + [escape(q) for q in db.get("duvidas_gerais", [])]
    if duv:
        p.append("<p>❓ <b>Dúvidas do robô: respondam aqui no grupo</b> (pode ser em texto livre; leio na próxima rodada)</p><ol>" + "".join(f"<li>{q}</li>" for q in duv) + "</ol>")
    p.append(secao("🚨 Prazo fatal vencido", vencidos))
    p.append(secao("📅 Para hoje (meta interna ou fatal)", hoje_l))
    p.append(secao("⏳ Próximos 3 dias úteis", prox))
    p.append(secao("📨 Com o cliente há mais de 5 dias: cobrar", cliente, lambda x: item(x, f" · falta: {escape(x.get('pendencia') or '?')} · {parado(x)}d")))
    p.append(secao("🧊 Parados além do máximo do status", parados, lambda x: item(x, f" · {parado(x)}d parado")))
    if sem_prazo:
        p.append("<p>❓ <b>Sem prazo nem data de ação (definir)</b></p><ul>" + "".join(f"<li>{escape(x['cliente'])}: {escape(x['providencia'])}</li>" for x in sem_prazo) + "</ul>")
    if len([s for s in p if s]) == 1:
        p.append("<p>Nada vencendo e nada parado. 👏</p>")
    p.append(f'<p>Painel: <a href="{DASH}">{DASH}</a> · Atualize aqui: ATUALIZAÇÃO | CLIENTE | processo | o que aconteceu | próximo passo | dd/mm #status</p>')
    html = "\n".join(s for s in p if s)
    (ROOT / "private" / "digest.html").write_text(html, encoding="utf-8")
    print(html)


if __name__ == "__main__":
    main()
