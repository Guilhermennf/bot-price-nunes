# Deploy 24/7 — Oracle Cloud Always Free

Substitui o GitHub Actions + cron-job.org por uma VM sempre ligada, de graça
de verdade (não é trial). Coleta a cada 30 min pontual + post a cada 15 min,
sem limite de 60 dias, sem atraso de scheduler.

## 1. Criar a VM (uma vez, ~15 min)

1. Conta em [oracle.com/cloud/free](https://www.oracle.com/cloud/free/) —
   pede cartão só para verificação, o tier Always Free não cobra.
2. Console → Compute → Instances → **Create instance**:
   - Image: **Ubuntu 24.04** (aarch64)
   - Shape: **VM.Standard.A1.Flex** — até 4 OCPUs / 24 GB RAM no Always Free
     (2 OCPU / 8 GB já sobra para o bot)
   - Adicione sua chave SSH pública.
3. Anote o IP público e conecte: `ssh ubuntu@IP`.

## 2. Instalar o bot

```bash
git clone https://github.com/Guilhermennf/bot-price-nunes.git
cd bot-price-nunes
bash deploy/oracle/install.sh
nano .env        # preencher os secrets reais
sudo systemctl restart dealbot-collect.timer dealbot-post.timer
```

## 3. Operação

```bash
systemctl list-timers 'dealbot-*'          # próximas execuções
journalctl -u dealbot-collect -n 50        # log da coleta
journalctl -u dealbot-post -n 50           # log da postagem
cd ~/bot-price-nunes && git pull           # atualizar o código
```

## Depois de migrar

- Desative o cronjob no cron-job.org (ou deixe — o dedupe impede post duplo,
  mas gasta chamada à toa).
- O workflow `deals.yml` pode ficar como backup manual (`workflow_dispatch`);
  o `schedule` pode ser removido para não coletar em dobro.
- Bônus: IP/ASN diferente do GitHub — teste se o Pelando volta a responder
  (`python -m app.main --dry-run` e olhe o log da fonte pelando).
