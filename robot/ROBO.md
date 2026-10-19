# Robô Argos → Dash do Contencioso Tributário

Roda na nuvem (rotina "Robô Contencioso (Argos)" no claude.ai) às **7h45 e 19h45**. Lê o grupo **CONTENCIOSO TRIBUTÁRIO - INTERNO** no Teams e atualiza o painel https://veigalaw.github.io/contencioso/. Às 7h45 dos dias úteis posta a agenda do dia no grupo.

## Arquivos

| Arquivo | O que é | Vai pro GitHub? |
|---|---|---|
| `private/demandas.json` | Base em texto aberto, regenerada a partir do publicado em cada rodada | **Não** |
| `data/demandas.enc.json` | Base criptografada (fonte da verdade; é o que o painel lê) | Sim |
| `robot/build.py` | `--pull` puxa e decripta; sem flag valida, calcula prazo interno e criptografa; `--push` publica | Sim |
| `robot/digest.py` | Monta a mensagem diária do Argos | Sim |

## Modelo de cada demanda

`id` (slug cliente-providência), `cliente`, `parte_contraria`, `processo` (CNJ ou nº do PA), `lm` (código do Legal Manager, ex. "LM 6958"), `orgao`, `esfera` (`judicial` | `administrativo` | `interno`), `assunto`, `providencia`, `status`, `responsavel`, `revisor`, `prazo_fatal`, `prazo_interno` (se não vier, o build calcula fatal − 2 dias úteis), `prioridade` (`alta`|`normal`), `pendencia` (o que falta e de quem), `motivo_parado`, `proximo_passo`, `proxima_data`, `criado_em`, `ultimo_movimento`, `status_desde`, `responsavel_desde`, `revisar` (true quando o robô inferiu algo e o time precisa confirmar), `historico` [{data, autor, texto, fonte}].

**Status** (`status`): `entrada` → `a_fazer` → `elaboracao` → `revisao` → `protocolar` → `aguardando_orgao` → `concluido`, e `aguardando_cliente` a qualquer momento.

## Passo a passo de cada execução

1. `python robot/build.py --pull`
2. Abrir `private/demandas.json`; pegar `teams.chat_id` e `teams.ultima_msg`.
3. Ler as mensagens novas do chat (depois de `ultima_msg`). **Considere somente mensagens desse chat.** Ignore mensagens que começam com 🤖 (são do próprio robô) e mensagens de sistema. Converta HTML em texto; se for resposta a outra mensagem, leia a original para ter contexto.
4. Aplicar cada movimento, casando a demanda por **número do processo** (prioridade), código LM, ou cliente + providência (sem acento, sem caixa):
   - **Card de prazo** (modelo do Murilo): `PRAZO | CLIENTE | processo | providência - FATAL dd/mm` seguido de "Processo / Cliente / Status (Legal Manager) / Prazo em aberto / Providência". Se não existe, criar a demanda: `esfera` judicial (ou administrativo se for PA/órgão administrativo; "PRAZO INTERNO" sem processo = interno), `status = a_fazer`, `responsavel` = quem postou (ou o citado), `prazo_fatal`, `providencia`, `lm`, `parte_contraria` (o que vem depois do "x"), `criado_em` = data da mensagem. Se já existe, atualizar o que mudou.
   - **Atualização**: `ATUALIZAÇÃO | CLIENTE | processo | o que aconteceu | próximo passo | dd/mm [| FATAL dd/mm] [| responsável: Nome] [#status]`.
   - `#concluido CLIENTE | ...` → `status = concluido`. `#novo esfera | CLIENTE | processo | providência | FATAL dd/mm` → nova demanda.
   - `CLIENTE | responsável: Nome` → troca o responsável e grava `responsavel_desde` = data da mensagem.
   - `CLIENTE | pendência: ...` → grava `pendencia`; com `#aguardando_cliente` muda o status.
   - **Texto livre** também vale: "protocolei", "distribuí" → `aguardando_orgao` (ou `concluido` se não há mais nada a acompanhar); "minuta pronta / mandei para revisão" → `revisao` (revisor = quem foi citado); "aguardando procuração/documentos do cliente" → `aguardando_cliente` com `pendencia`; "concluso / aguardando decisão" → `aguardando_orgao`; "ganhamos a liminar", "sentença" → registrar no histórico e definir próximo passo.
   - Em toda mudança: acrescentar no `historico` `{data, autor, texto, fonte:"Contencioso interno (Teams)"}`, atualizar `ultimo_movimento` = data da mensagem; se o status mudou, `status_desde` = data da mensagem. Se a mensagem trouxer data de próxima ação, gravar `proxima_data` e `proximo_passo`.
   - **Prazos:** nunca inventar prazo fatal. Só gravar o que estiver escrito. Se a mensagem trouxer "prazo interno", gravar `prazo_interno` e apagar `prazo_interno_auto`.
   - Mensagem ambígua (não dá para saber a qual demanda se refere): registrar só no `feed` com prefixo "[revisar]".
5. **Feed:** inserir no topo de `feed` um item por movimento relevante `{data, autor, texto}` em uma linha. Máximo 200 itens.
6. `teams.ultima_msg` = `createdDateTime` da mensagem mais nova lida; `atualizado_em` = agora (UTC ISO).
7. `python robot/build.py --push` (**sempre**, mesmo sem mensagens novas: os alertas do painel dependem da data de publicação)
8. **Só na rodada da manhã (antes das 12h, dia útil):** `python robot/digest.py` e postar o HTML de `private/digest.html` no chat (uma mensagem, formato HTML), se ainda não houver mensagem de hoje começando com 🤖 "Argos · agenda do contencioso".

## Dúvidas (perguntar ao time pelo grupo)

- Quando o robô **não tiver certeza** (a qual item a mensagem se refere, se algo foi entregue/protocolado, quem é o responsável, um valor ou data ambíguos), ele **não chuta**: grava a pergunta no campo `duvida` do item (e `revisar: true`), ou em `duvidas_gerais` (lista na raiz) se não for de um item só.
- As dúvidas abertas saem na agenda das 7h45, na seção "❓ Dúvidas do robô" (o `digest.py` já monta). É a mesma mensagem do dia: não mandar mensagem separada.
- Em cada rodada, procurar no grupo **respostas** às dúvidas (mensagens que respondem à agenda do robô ou que citam o item). Ao aplicar a resposta: atualizar o item, registrar no `historico` ("Dúvida respondida por Fulano: ..."), apagar `duvida` e pôr `revisar: false`; tirar de `duvidas_gerais` o que foi respondido.
- Se a resposta não resolver, reescrever a `duvida` de forma mais objetiva.

## Regras

- O robô só **lê** o Teams. A única coisa que escreve é a agenda do dia (passo 8).
- Nunca apagar demanda. Para encerrar: `concluido`.
- Não inventar processo, prazo ou cliente. Só gravar o que está escrito.
- Datas AAAA-MM-DD, fuso de São Paulo.
- Nunca exibir a senha.
