# Reels Maker — GitHub push → auto-deploy (Docker, GCP VM)

Ekbar setup korle: **`git push` → GitHub Action → VM e auto pull + rebuild + restart**. Website er moto.

Flow: local code → GitHub repo → (push) → GitHub Actions → SSH into GCP VM → `docker compose up --build`.

---

## Phase 0 — Code GitHub e tolo (local PC theke, ekbar)

Git repo already init + commit kora ache (ei folder e). Ekhon GitHub e tolo:

1. [github.com/new](https://github.com/new) → repo name dao (jemon `reels-maker`) → **Private** rakho
   (kono README/gitignore add koro NA) → **Create repository**
2. **Push koro** — 2 way:

   **Sohoj (GitHub Desktop):** [desktop.github.com](https://desktop.github.com) install → File → *Add Local
   Repository* → ei folder select → *Publish repository* (Private rekho).

   **Ba CLI:** (password chaile GitHub **Personal Access Token** lagbe, account password na)
   ```powershell
   git remote add origin https://github.com/<TOMAR_USER>/reels-maker.git
   git push -u origin main
   ```

> `.env`, `engine/.env`, model, output — gitignore e ache, GitHub e jabe na (secret safe)।

---

## Phase 1 — GCP VM ready koro (ekbar)

VM er **SSH (browser)** window e:

```bash
# 1. Docker install
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# ei point e SSH window bondho kore abar kholo (group refresh er jonno)

# 2. repo clone (private hole username + PAT chaibe)
git clone https://github.com/<TOMAR_USER>/reels-maker.git ~/reels-maker
cd ~/reels-maker

# 3. secrets file banao
cp .env.example .env
nano .env      # REELS_LLM_API_KEY + REELS_UI_PASSWORD boshao (Ctrl+O, Enter, Ctrl+X)

# 4. prothom build + run
docker compose up -d --build      # prothombar 5-10 min (image build)
docker compose ps                 # cholche kina
docker compose logs -f            # log (Ctrl+C ber hote)
```

**Firewall (port 5000):** GCP Console → **VPC network → Firewall → Create firewall rule**
- Name `allow-reels-5000` · Ingress · Targets: All instances · Source `0.0.0.0/0` · TCP `5000` → Create

Ekhon browser e **http://VM-EXTERNAL-IP:5000** → password diye login → kaaj korche! ✅
(External IP: Console → Compute Engine → VM instances → "External IP")

---

## Phase 2 — Auto-deploy chalu koro (GitHub Actions)

Ekhon `git push` korlei VM auto-update hobe. 3 ta GitHub Secret lagbe.

**1. VM e ekta deploy SSH key banao** (VM terminal e):
```bash
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/deploy_key           # ei PRIVATE key ta pura copy koro (niche lagbe)
whoami                          # ei username o note koro
```

**2. GitHub repo → Settings → Secrets and variables → Actions → New repository secret** (3 ta):
| Secret name | Value |
|-------------|-------|
| `VM_HOST` | VM er External IP |
| `VM_USER` | upore `whoami` er output |
| `VM_SSH_KEY` | upore copy kora **private key** (pura, `-----BEGIN...END-----` soho) |

**3. Test:** local e kono kichu change kore `git push` koro → GitHub repo er **Actions** tab e deploy
   cholte dekhbe → shesh hole VM auto-updated. ✅

> GCP e "OS Login" enabled thakle `authorized_keys` kaj nao korte pare — sekhetre key ta VM →
> Edit → SSH Keys e add korte hobe. Atke gele bolba, dekhabo.

---

## Rojkar use
- **Code change → `git push`** → auto-deploy. Baস।
- Manual update (Action chara): VM e `bash deploy/update.sh`
- Restart: `docker compose restart` · Logs: `docker compose logs -f` · Bondho: `docker compose down`
