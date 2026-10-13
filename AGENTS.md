# AGENTS.md — EFM Trinity UI botas (GitHub → Contabo per Ziti)

## PRISIJUNGIMAS PRIE CONTABO SERVERIO

Tu esi botas Trinity UI repozitorijoje. Prisijungi prie Contabo serverio per Ziti tuneli.

## ZITI KONFIGURACIJA

- Kontroleris: efm.efmleads.com:1280
- Identitetas: identities/trinity-bot.json (jau repo)

## TUNELIS (naudok Ziti 2.0.6 CLI, NE node splice.cjs)

node splice.cjs NEVEIKIA: Node SDK 0.29.1 vs kontroleris 2.0.6 duoda tuscia atsakyma.
Naudok ziti CLI 2.0.6:

```bash
# Ziti tunnel:
ziti edge login efm.efmleads.com:1280 -u <user>
# arba tiesiogiai su identitetu:
ziti-tunnel run -i identities/trinity-bot.json
```

Po tunnel: pasieki servisus per localhost.

## DU SERVISAI

### 1. trinity-vault → Kiro Crew gateway (5476)
```bash
curl http://localhost:5476/api/status
```

### 2. trinity-files → Vault failu serveris (19003)

#### SKAITYTI
```bash
# Failu sarasas:
curl "http://localhost:19003/api/list?path=gamyba/efm-go"

# Failo turinys:
curl "http://localhost:19003/api/read?path=gamyba/efm-go/CURRENT.md"

# Root AGENTS.md:
curl "http://localhost:19003/api/read?path=AGENTS.md"
```

#### RASYTI
```bash
# Irasyti faila (POST body = failo turinys):
curl -X POST "http://localhost:19003/api/write?path=gamyba/efm-go/NaujasFailas.md" \
  --data-binary @failas.md

# arba tiesiogiai:
echo "turinys" | curl -X POST "http://localhost:19003/api/write?path=test.txt" --data-binary @-
```

#### ISTRINTI
```bash
curl -X POST "http://localhost:19003/api/delete?path=gamyba/efm-go/SenasFailas.md"
```

#### COMMIT (git add + commit serveryje)
```bash
curl -X POST "http://localhost:19003/api/commit?message=Mano%20commit%20zinute"
# URL-encode tarpai kaip %20
```

#### PUSH (git push i origin)
```bash
curl -X POST "http://localhost:19003/api/push"
```

#### STATUS
```bash
curl "http://localhost:19003/api/status"
```

## DARBO TVARKA

1. Prisijunk per Ziti tunnel (ziti-tunnel run -i identities/trinity-bot.json)
2. Skaityk CURRENT.md ir EFM_GO_STATE.yaml per /api/read
3. Dirbk: rasai failus per /api/write
4. Po darbo: /api/commit + /api/push
5. Atsijunk

## VAULT STRUKTURA

- gamyba/efm-go/ — EFM Go projektas
- gamyba/efm-go/CURRENT.md — ka daryti dabar
- gamyba/efm-go/EFM_GO_STATE.yaml — busenos
- gamyba/efm-go/00-TAISYKLES.md — darbo taisykles
- komunikacija/ — komunikacijos failai