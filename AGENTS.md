# AGENTS.md — EFM Trinity UI botas (GitHub → Contabo per Ziti)

## KAIP VEIKIA PRISIJUNGIMAS

OpenZiti = Tailscale. Tai overlay tinklas, tuneliuoja TCP. Tu neesi atskiras botas su
„API irankiais" — tu gauni PILNA ROOT SHELL per SSH, lygiai kaip Tailscale.

## ZITI KONFIGURACIJA

- Kontroleris: efm.efmleads.com:1280
- Identitetas: identities/trinity-bot.json (jau repo)
- SSH raktas: ssh-keys/trinity-bot_id_ed25519 (jau repo, root prieiga)

## PRISIJUNGIMAS (SSH PER ZITI — PAGRINDINIS BUDAS)

```bash
# 1. npm install (splice.cjs priklausomybe)
npm install @openziti/ziti-sdk-nodejs

# 2. Dial SSH servisa i localhost:2222
node splice.cjs dial identities/trinity-bot.json 2222 trinity-ssh

# 3. SSH i serveri per Ziti (pilnas root shell)
ssh -i ssh-keys/trinity-bot_id_ed25519 -p 2222 \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  root@127.0.0.1
```

Po siu zingsniu turi PILNA root shell. Gali: ls, cat, vim/nano, git, python, bash —
viskas, ka moka normalus kompiuteris. Jokiu papildomu „tool'u" nereikia.

## VIENA-KARTE SU-KOMANDA (praktiskai)

```bash
node splice.cjs dial identities/trinity-bot.json 2222 trinity-ssh &
sleep 3
ssh -i ssh-keys/trinity-bot_id_ed25519 -p 2222 \
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  root@127.0.0.1 'ls /opt/efm/vault/gamyba/efm-go/'
```

## VAULT VIETA

Vault (visa EFM Go dokumentacija ir kodas): /opt/efm/vault
- gamyba/efm-go/CURRENT.md — ka daryti dabar
- gamyba/efm-go/EFM_GO_STATE.yaml — busenos
- gamyba/efm-go/00-TAISYKLES.md — taisykles

## DARBO TVARKA

1. splice.cjs dial → SSH
2. Skaityk CURRENT.md, dirbk kaip normalus agentas (ls, cat, git, python)
3. Po darbo: git add/commit/push /opt/efm/vault
4. Atsijunk

## PASTABA

node splice.cjs veikia tik su ivykdyta npm install @openziti/ziti-sdk-nodejs
(jau repo package.json). Jei dial duoda tuscia atsakyma — patikrink ar node_modules yra.