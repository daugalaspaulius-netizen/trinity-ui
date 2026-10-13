# AGENTS.md — EFM Trinity UI botas (GitHub → Contabo per Ziti)

## PRISIJUNGIMAS PRIE CONTABO SERVERIO

Tu esi botas Trinity UI repozitorijoje. Prisijungi prie Contabo serverio per Ziti tuneli.
Tau duotas PILNAS agento irankiu rinkinys (kaip Cursor): skaityti, rašyti, redaguoti,
ieškoti, vykdyti komandas, git.

## ZITI KONFIGURACIJA

- Kontroleris: efm.efmleads.com:1280
- Identitetas: identities/trinity-bot.json (jau repo)

## TUNELIS (naudok Ziti 2.0.6 CLI, NE node splice.cjs)

node splice.cjs NEVEIKIA: Node SDK 0.29.1 vs kontroleris 2.0.6 duoda tuscia atsakyma.
Naudok ziti CLI 2.0.6:

```bash
ziti edge login efm.efmleads.com:1280
ziti-tunnel run -i identities/trinity-bot.json
# Po tunnel: servisai pasiekiami per localhost
```

## SERVISAI

### trinity-vault → Kiro Crew gateway (localhost:5476)
```bash
curl http://localhost:5476/api/status
```

### trinity-files → Vault Agent Tools (localhost:19003)

PILNAS IRANKIU RINKINYS — visas agento darbas per si API.

---

## TOOLS — PILNAS SARASAS

### SKAITYMAS
```bash
# Skaityti faila
curl "http://localhost:19003/api/read?path=gamyba/efm-go/CURRENT.md"

# List directory (recursive=1 for tree)
curl "http://localhost:19003/api/list?path=gamyba/efm-go"
curl "http://localhost:19003/api/list?path=gamyba&recursive=1"

# Glob (failu paieska pagal sablona)
curl "http://localhost:19003/api/glob?pattern=**/*.yaml&path=gamyba/efm-go"

# Grep (turinio paieska regex)
curl "http://localhost:19003/api/grep?pattern=PRIMARY%20OBJECTIVE&path=gamyba/efm-go"
```

### RASYMAS
```bash
# Irasyti/overwrite faila (POST body = turinys)
echo "turinys" | curl -X POST "http://localhost:19003/api/write?path=gamyba/efm-go/Test.md" --data-binary @-

# Edit (string replace — kaip Cursor Edit tool, su old_string/new_string)
curl -X POST "http://localhost:19003/api/edit" -H "Content-Type: application/json" \
  -d '{"path":"gamyba/efm-go/Test.md","old_string":"sena","new_string":"nauja"}'
# repeat_all: true kai old_string kartojasi

# Delete
curl -X POST "http://localhost:19003/api/delete?path=gamyba/efm-go/Test.md"
```

### BASH (komandu vykdymas)
```bash
curl -X POST "http://localhost:19003/api/bash" -H "Content-Type: application/json" \
  -d '{"command":"ls -la gamyba/efm-go","cwd":"","timeout":30}'
```
cwd — santykinis kelias nave /opt/efm/vault. Atsakymas: {ok, exit, stdout, stderr}.

### GIT
```bash
# Status
curl "http://localhost:19003/api/git/status"

# Diff (path optional)
curl "http://localhost:19003/api/git/diff"
curl "http://localhost:19003/api/git/diff?path=komunikacija/foo.md"

# Log
curl "http://localhost:19003/api/git/log?n=10"

# Commit (message per query arba body)
curl -X POST "http://localhost:19003/api/git/commit?message=Mano%20commit"

# Push / Pull
curl -X POST "http://localhost:19003/api/git/push"
curl -X POST "http://localhost:19003/api/git/pull"
```

### STATUS / ROOT
```bash
curl "http://localhost:19003/api/status"
curl "http://localhost:19003/"
```

---

## DARBO TVARKA

1. ziti-tunnel run -i identities/trinity-bot.json
2. Skaityk CURRENT.md ir EFM_GO_STATE.yaml per /api/read
3. Dirbk: /api/read, /api/grep, /api/list, /api/write, /api/edit, /api/bash
4. Po darbo: /api/git/commit + /api/git/push
5. Atsijunk

## VAULT STRUKTURA (root = /opt/efm/vault)

- gamyba/efm-go/CURRENT.md — ka daryti dabar
- gamyba/efm-go/EFM_GO_STATE.yaml — busenos
- gamyba/efm-go/00-TAISYKLES.md — darbo taisykles
- komunikacija/ — komunikacijos failai