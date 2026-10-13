# AGENTS.md — EFM Trinity UI botas (GitHub → Contabo serveris per Ziti)

## PRISIJUNGIMAS PRIE CONTABO SERVERIO PER ZITI

Tu esi botas, kuris gyvena sitame Trinity UI repozitorijoje. Tavo darbas — prisijungti
prie Contabo serverio per Ziti tuneli ir dirbti su EFM Go projektu.

### ZITI PRISIJUNGIMO INSTRUKCIJA

1. **Ziti kontroleris:** efm.efmleads.com:1280
2. **Ziti servisas:** trinity-vault
3. **Identiteto failas:** identities/trinity-bot.json (yra repo)

### KAIP NAUDOTI

```bash
# 1. Nusiklonuok repo
git clone https://github.com/daugalaspaulius-netizen/trinity-ui.git
cd trinity-ui

# 2. Ziti SDK reikia
npm install @openziti/ziti-sdk-nodejs

# 3. Dial per Ziti prie Kiro Crew gateway (Contabo serveris, portas 5476)
node splice.cjs dial identities/trinity-bot.json 5476 trinity-vault

# 4. Dabar gali pasiekti Kiro Crew API per localhost:5476
curl http://localhost:5476/api/status
```

### SERVERIO INFO

- Kiro Crew gateway: per Ziti → localhost:5476 (Contabo serveryje)
- Vault: /opt/efm/vault (pasiekiamas per Kiro Crew API)
- EFM Go projektas: gamyba/efm-go/

### DARBO TVARKA

1. Prisijunk per Ziti (instrukcija auksciau)
2. Per Kiro Crew API skaityk/rasyk Vault failus
3. Po darbo atsijunk