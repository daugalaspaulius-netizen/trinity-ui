# AGENTS.md — EFM Trinity UI botas (GitHub → Contabo per Ziti)

## PRISIJUNGIMAS PRIE CONTABO SERVERIO

Tu esi botas Trinity UI repozitorijoje. Tavo uzduotis — prisijungti prie Contabo serverio
per Ziti tuneli ir dirbti su EFM Go projektu.

## ZITI KONFIGURACIJA

- Kontroleris: efm.efmleads.com:1280
- Identitetas: identities/trinity-bot.json (jau repo)

## DU SERVISAI

### 1. trinity-vault — Kiro Crew gateway (agento API)
```bash
npm install @openziti/ziti-sdk-nodejs
node splice.cjs dial identities/trinity-bot.json 5476 trinity-vault
# Po dial: Kiro Crew API per http://localhost:5476
curl http://localhost:5476/api/status
```

### 2. trinity-files — Vault failu serveris (skaityti/rasyti failus)
```bash
node splice.cjs dial identities/trinity-bot.json 19003 trinity-files
# Po dial: Vault failai per http://localhost:19003

# Sarasas:
curl "http://localhost:19003/api/list?path=gamyba/efm-go"

# Skaityti faila:
curl "http://localhost:19003/api/read?path=gamyba/efm-go/CURRENT.md"

# Skaityti root:
curl "http://localhost:19003/api/read?path=AGENTS.md"
```

## DARBO TVARKA

1. `npm install @openziti/ziti-sdk-nodejs`
2. Paleisk dial abiem servisam (skirtinguose terminaluose arba fone)
3. Skaityk CURRENT.md per trinity-files
4. Skaityk EFM_GO_STATE.yaml per trinity-files
5. Dirbk per Kiro Crew API (trinity-vault)
6. Po darbo atsijunk

## VAULT STRUKTURA

- gamyba/efm-go/ — EFM Go projektas
- gamyba/efm-go/CURRENT.md — ka daryti dabar
- gamyba/efm-go/EFM_GO_STATE.yaml — busenos
- gamyba/efm-go/00-TAISYKLES.md — darbo taisykles
- komunikacija/ — komunikacijos failai