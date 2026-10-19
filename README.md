# Contencioso Tributário (Argos 👁️⚖️)

Painel de gestão do contencioso tributário da Veiga: agenda de prazos (meta interna e fatal), quadro de demandas por status, carga por pessoa, métricas de gestão (risco de prazo, bola com quem, tempo parado, tempo com cada pessoa, ritmo) e manual da controladoria.

**Acesso:** https://veigalaw.github.io/contencioso/ (senha do time).

- Os dados ficam em `data/demandas.enc.json`, criptografados (AES-256-GCM). O repo é público, mas sem a senha ninguém lê cliente, processo ou histórico.
- O robô **Argos** roda na nuvem (rotina no claude.ai, conector Microsoft 365) às 7h45 e 19h45: lê o grupo "CONTENCIOSO TRIBUTÁRIO - INTERNO" no Teams, atualiza as demandas e, às 7h45 dos dias úteis, posta a agenda do dia no grupo. Detalhes em [`robot/ROBO.md`](robot/ROBO.md).
