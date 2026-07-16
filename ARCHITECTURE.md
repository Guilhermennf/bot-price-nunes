# Arquitetura — Deal Bot (canal de ofertas tech no Telegram)

> Documento de referência para explicar o projeto camada por camada — inclusive
> em entrevistas. Cada seção traz **o que faz**, **como faz** e **por que foi
> feito assim** (as decisões de engenharia são o que diferencia o projeto).

## Visão em 30 segundos (elevator pitch)

Pipeline autônomo que descobre promoções de tecnologia em agregadores
brasileiros, **valida se o desconto é real** usando histórico de preços,
usa um LLM como curador (nota 0–100 + texto de venda em PT-BR) e publica no
Telegram com link direto da loja — rodando **100% em free tier** (GitHub
Actions + Supabase + Gemini + Telegram + Vercel). O sistema é *stateless por
execução*: toda memória vive no banco, o que permite usar cron efêmero em vez
de servidor 24/7 — essa decisão é o que zera o custo.

```
GitHub Actions (cron 30min)
   └─> 1. EXTRAÇÃO      Promobit (__NEXT_DATA__) + Pelando (API REST interna)
   └─> 2. CURADORIA     whitelist de 5 lojas + filtro tech (keywords)
   └─> 3. VALIDAÇÃO     preço atual vs mediana histórica (Supabase)
   └─> 4. IA            Gemini: legit? score? é tech? + copy persuasiva
   └─> 5. DEDUPE        já postado? só repete se ficou >1% mais barato
   └─> 6. LINK DIRETO   resolve cadeia de afiliado -> URL limpa da loja
   └─> 7. PUBLICAÇÃO    Telegram Bot API (canal)
        └─> Supabase registra: deal postado, série de preços, métricas da run
             └─> Dashboard Next.js (Vercel) lê e mostra a saúde do pipeline
```

## Camada 1 — Agendamento (GitHub Actions)

**O quê:** workflow `deals.yml` com `schedule: */30` + `workflow_dispatch`.

**Como:** job único que instala Python 3.12 + deps e roda `python -m app.main`.
Segredos via GitHub Secrets. `concurrency` evita runs sobrepostas.

**Decisões:**
- *Por que não um servidor?* O pipeline roda por ~2 min a cada 30 min. Um worker
  24/7 desperdiça 93% do tempo. Cron efêmero + estado no banco = custo zero.
- Workflows agendados são **desativados após 60 dias sem commits**; um step de
  keepalive chama a própria API de enable a cada run, resetando o contador.
- Runner é IP de datacenter — implicação direta na camada de extração (abaixo).

## Camada 2 — Extração (scraping estratégico)

**O quê:** coleta candidatos de dois agregadores comunitários; e-commerce
direto só para *confirmar* preço, nunca para descobrir.

**Como (cada fonte exigiu engenharia própria):**
- **Promobit** (Next.js): parse do JSON `__NEXT_DATA__` embutido no HTML —
  muito mais estável que seletores CSS. Schema real verificado ao vivo:
  `offerTitle/offerPrice/offerOldPrice/offerCoupon/offerSlug/storeName`.
- **Pelando** (Astro, client-rendered): HTML vem vazio. A solução foi descobrir
  a API REST interna (`api-web.pelando.com.br/feed/highlights`) observando o
  tráfego do site — ela só exige um header de visitante anônimo
  (`x-sosho-unlogged-id: <UUID qualquer>`). Sem browser, sem login.
- **Mercado Livre / Amazon direto**: ambos bloqueiam IPs de datacenter
  (redirect para `account-verification` / CAPTCHA). Por isso a confirmação
  direta é *best-effort*: falhou → confia no preço do agregador. O fallback de
  browser headless existe mas fica **desligado** (flag), porque a muralha pega
  ele também.

**Decisões:**
- *Agregador primeiro*: a comunidade já filtrou o lixo; a superfície de
  scraping é 2 páginas estáveis em vez de N lojas hostis.
- **Fail-soft em tudo**: cada fonte que quebra loga warning e retorna lista
  vazia. Uma fonte fora do ar nunca derruba a run (na prática: Pelando retorna
  403 no runner do Actions — o pipeline segue só com Promobit e se recupera
  nas execuções locais).

## Camada 3 — Curadoria (whitelist + nicho tech)

**O quê:** só passam ofertas das 5 lojas-alvo (Amazon, Mercado Livre,
AliExpress, Shopee, Magalu) e com cara de tecnologia.

**Como:** `app/stores.py` é a fonte única de identidade de loja (match por
nome do feed *ou* por host da URL). O filtro tech tem **duas camadas**:
keywords amplas e baratas antes da IA (corta o óbvio sem gastar quota) e o
veredito estrito `is_tech` do Gemini depois (mesma chamada, custo zero extra).

**Decisão:** filtro barato primeiro, filtro caro depois — padrão funil. Na
prática corta ~80% dos candidatos antes de tocar na API paga por quota.

## Camada 4 — Validação de preço (o coração anti-fraude)

**O quê:** rejeita o clássico "de R$ 999 por R$ 499" com preço "de" inflado.

**Como:** cada observação de preço vira uma linha em `price_history`
(chave = hash da URL normalizada, sem parâmetros de tracking). A oferta só
passa se o preço atual estiver X% abaixo da **mediana da própria série** na
janela de 90 dias — o desconto é calculado contra o histórico real, não contra
o que a loja alega. Detalhe importante: a observação atual é gravada **depois**
do julgamento, senão ela contaminaria a própria mediana.

**Decisão:** mediana (não mínimo) como referência — robusta a outliers de
erro de preço. Produto sem histórico ainda passa (primeira vez), e a IA vira
o segundo portão.

## Camada 5 — IA como curador (Gemini)

**O quê:** para cada candidato, o Gemini responde JSON estruturado:
`{legit, score 0-100, is_tech, category, reason, copy}` — a `copy` é o texto
persuasivo em PT-BR com emojis que vai pro canal.

**Como:** `gemini-flash-latest` com `response_mime_type: application/json`.
Free tier sofre 503 sob carga → retry com backoff + fallback automático para
`gemini-flash-lite-latest`. Score < 70 ou `legit=false` → descarte.

**Resultados reais dos logs** (o LLM pegando fraude que regra nenhuma pegaria):
- Galaxy S26 a preço suspeito → score 20: *"ainda não foi lançado oficialmente;
  provavelmente erro de cadastro ou preço fictício"*.
- Smart TV OLED "52% off" → score 45: *"o preço de tabela informado é inflado;
  o desconto é enganoso"*.

**Decisão de custo:** a IA é o estágio mais caro (quota), então roda **por
último** no funil, só em quem já passou por tudo. Candidatos são ranqueados
por desconto antes do corte `MAX_DEALS_PER_RUN`, então a quota vai primeiro
para as melhores ofertas.

## Camada 6 — Persistência e dedupe (Supabase/Postgres)

**O quê:** 3 tabelas — `deals` (o que já foi postado), `price_history`
(série temporal), `runs` (métricas por execução, alimenta o dashboard).

**Como:** a identidade de um produto é o hash SHA-256 da URL **normalizada**
(host minúsculo, sem fragmento, sem ~30 parâmetros de tracking — `utm_*`,
`matt_*` do ML, `aff_*`, etc.). Dedupe: mesma oferta só é repostada se o preço
novo for >1% menor que o do último post dentro da janela de cooldown.

**Decisões:**
- Normalizar a URL é o que faz o mesmo produto vindo de fontes diferentes
  colidir na mesma chave.
- RLS (Row Level Security) habilitado: papel `anon` só lê — o bot escreve com
  a service key (que bypassa RLS). Defesa em profundidade para o dashboard.
- Free tier do Supabase pausa após 7 dias inativo — o próprio tráfego do bot
  mantém o projeto acordado.

## Camada 7 — Link direto + afiliados

**O quê:** o feed do Promobit não tem o link da loja — só a página deles.
O usuário final quer o link direto.

**Como:** descobri que `promobit.com.br/Redirect/to/<offerId>/` embute o link
de afiliado (linksynergy/awin), que por sua vez redireciona à loja. O resolvedor
segue a cadeia inteira e **só aceita se o host final for uma das 5 lojas** —
cadeia morta ("bad merchant") ou volta pro Promobit = oferta descartada.
Antes de publicar, a URL passa por `affiliate.apply()`: módulo dormante que
anexa a identidade de afiliado por loja (ex.: `?tag=` da Amazon) quando as
env vars existirem — arquitetura pronta para monetizar sem refactor.

**Decisão sutil:** o afiliado é aplicado **depois** do dedupe/normalização,
então parâmetros de afiliado nunca contaminam a identidade do produto.

## Camada 8 — Publicação (Telegram) e Dashboard (Next.js/Vercel)

**Telegram:** POST direto na Bot API (HTML) — um framework de bot seria peso
morto para mão única. A foto do produto (`og:image` da página final da loja,
buscada em `fetch_image()` no momento da publicação) vai via `sendPhoto`, com
título/preço/cupom/loja/link como legenda — em vez de depender do preview
automático de link do Telegram, que puxa título/descrição da própria loja e
podia inflar a mensagem. Sem imagem (ou se o `sendPhoto` falhar), cai para
`sendMessage` com preview desligado.

**Dashboard:** Next.js App Router na Vercel, ISR de 2 min. Server Components
buscam do Supabase **no servidor** (a service key nunca chega ao browser).
Mostra: tiles (ofertas 7d, runs 24h, score médio, taxa do funil), gráfico de
posts/dia, funil da última run (quantos morreram em cada portão), tabela das
últimas ofertas e saúde das runs — o funil torna visível, por exemplo, o
Pelando caindo para 0 no CI (403) enquanto o Promobit segue.

## Camada 9 — Autenticação do dashboard (Auth.js v5)

**O quê:** dashboard é restrito a admins — login em `/login`, todo o resto
protegido por middleware.

**Como:** Auth.js (NextAuth v5) com Credentials provider: email + senha
verificados contra `admin_users` no Supabase (hash bcrypt, custo 12), sessão
JWT. O middleware roda em **runtime Node** (não edge) porque o provider importa
`bcryptjs` e `supabase-js`. A tabela `admin_users` tem RLS ligado **sem
policies** — o papel `anon` não consegue nem ler; só a service key server-side
alcança. Input validado com Zod nos dois lados (form e authorize).

**Decisão:** Credentials + tabela própria em vez de OAuth — zero dependência
externa, allowlist explícita de admins, e o seed é um comando
(`npm run seed:admin`).

## Camada 10 — Qualidade e testes

- **Bot (pytest, 37 testes):** parsers testados contra **fixtures gravadas dos
  sites reais** (o teste quebra se o parsing regride, sem depender de rede);
  normalização de URL; filtros de loja/tech; casos da validação de preço
  (queda real, "de/por" inflado, sem histórico, banco fora); afiliados;
  template de mensagem.
- **Dashboard:** Vitest + Testing Library (componentes, estados de paginação)
  e Playwright e2e local (redirect de não-autenticado, senha errada, login
  válido, paginação de /deals).
- **Gate estático:** ruff + mypy (Python), tsc estrito (TS).
- **CI:** dois jobs paralelos em todo push/PR ([ci.yml](.github/workflows/ci.yml));
  Dependabot semanal para pip, npm e actions.
- **Observabilidade:** Sentry nos dois lados, ativado por env var (no-op sem
  DSN — zero acoplamento).

## Incidentes reais (histórias boas de contar)

1. **O BOM invisível:** secrets setados via pipe do PowerShell 5.1 chegaram ao
   GitHub com U+FEFF na frente — quebrou o header do Gemini e a URL do Supabase
   só no CI. Fix duplo: `gh secret set --body` (sem stdin) + scrub defensivo de
   BOM/whitespace em todas as settings. Lição: fronteiras de encoding importam.
2. **Paredes anti-bot:** ML/Amazon bloqueiam datacenter até com browser real.
   Em vez de guerra de evasão, mudei o desenho: confirmação vira best-effort e
   a fonte de verdade é o agregador. Lição: às vezes a resposta é redesenhar,
   não escalar a briga.
3. **Registro fantasma do workflow:** o push inicial via `gh repo create --push`
   não registrou o workflow agendado; precisou de um segundo push. Lição:
   automação de plataforma tem arestas — verifique o estado real, não o esperado.

## Números (verificados em produção)

- Coleta típica: 30–75 candidatos/run; curadoria corta ~80% antes da IA.
- Run completa: ~2 min no runner free.
- Custo mensal: **R$ 0,00** (Actions público + Supabase free + Gemini free +
  Telegram + Vercel hobby).
