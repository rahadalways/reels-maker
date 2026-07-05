# Reels Maker — VPS Deploy Guide (Ubuntu/Debian, CPU)

Local PC slow, tai VPS e chalanor guide. Browser theke `http://VPS-IP:5000` diye use korba (password protected).

---

## 🟢 Google Cloud (GCE) quickstart — browser SSH diye

Google Cloud e file neowa sobcheye sohoj (WinSCP/scp lagena):

1. **Upload:** VM er **SSH (browser)** window kholo → upore-dan kone **⚙️ gear icon** → **Upload file**
   → `reels-maker-deploy.zip` beche dao. Home folder e (`~`) chole asbe.
2. **Terminal e:**
   ```bash
   sudo apt-get update && sudo apt-get install -y unzip
   mkdir -p ~/reels-maker && unzip ~/reels-maker-deploy.zip -d ~/reels-maker
   cd ~/reels-maker
   free -h                 # RAM koto dekho (niche note)
   bash deploy/setup.sh
   nano engine/.env        # API key + password boshao
   ```
3. **Firewall (port 5000 kholo)** — GCP e `ufw` na, **VPC firewall rule** lagbe:
   Console → **VPC network → Firewall → Create firewall rule**
   - Name: `allow-reels-5000` · Direction: Ingress · Targets: All instances
   - Source IPv4 ranges: `0.0.0.0/0` · Protocols/ports: TCP = `5000` → **Create**
4. **Chalu:** `bash deploy/run.sh`
5. **External IP** nao: Console → Compute Engine → VM instances → "External IP" column →
   browser e `http://EXTERNAL_IP:5000`

> ⚠️ **RAM check:** `free -h`. Free-tier `e2-micro` (1GB RAM) hole Whisper `small` OOM korte pare —
> `engine/config.yaml` e `transcribe.model_size: base` (ba `tiny`) koro। 4GB+ hole `small` thik ache।

> ⚠️ Browser SSH window bondho korle server theme jay — 24/7 rakhte niche systemd step dekho।

---

## Step 1 — Project ta VPS e nao (onno provider / manual)

**Option A — Git (recommend, jodi GitHub thake):**
```bash
# local e (ekbar):  git init && git add . && git commit -m "reels maker" && git push
# VPS e:
git clone <tomar-repo-url> "Reels Maker"
cd "Reels Maker"
```

**Option B — Direct upload (git chara):**
Local e project folder ta zip koro (`.venv`, `output`, `engine/models`, `engine/.env` baad diye —
`reels-maker-deploy.zip` already project root e banano ache). Tarpor VPS e upload:
```bash
# local (Git Bash / PowerShell) theke:
scp reels-maker-deploy.zip user@VPS-IP:~/

# VPS e:
mkdir -p "Reels Maker" && unzip ~/reels-maker-deploy.zip -d "Reels Maker"
cd "Reels Maker"
```

---

## Step 2 — Setup (ekbar cholabe)
```bash
bash deploy/setup.sh
```
Eta ffmpeg + python + sob dependency install korbe (kichukhon nibe)।

---

## Step 3 — Secrets boshao
```bash
nano engine/.env
```
Duita line thik koro:
```
REELS_LLM_API_KEY=<tomar OpenCode Zen key>
REELS_UI_PASSWORD=<ekta strong password>
```
> ⚠️ Password na dile UI shobar jonno open thakbe. Obosshoi ekta password dao.

---

## Step 4 — Firewall port khulo (5000)
```bash
sudo ufw allow 5000/tcp     # ufw thakle
```
> Cloud VPS (AWS/GCP/Oracle/DigitalOcean) hole panel er **Security Group / Firewall** eo port 5000 allow korte hobe.

---

## Step 5 — Server chalu
```bash
bash deploy/run.sh
```
Ekhon browser e **http://VPS-IP:5000** — password diye login → video drag-drop → Generate!

---

## Server 24/7 rakhte (reboot-proof) — systemd
`deploy/run.sh` terminal bondho korle theme jay. Sob somoy chalate:
```bash
# reels-maker.service e <USER> ar <PATH> edit koro (nano deploy/reels-maker.service)
sudo cp deploy/reels-maker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now reels-maker
sudo systemctl status reels-maker      # cholche kina
journalctl -u reels-maker -f           # live log
```

---

## Notes / tips
- **Speed:** VPS e core beshi thakle transcribe faster. `engine/config.yaml` → `transcribe.model_size`
  `base` korle aro fast (accuracy ektu kom), `medium` korle better but slow.
- **Whisper model** first run e HF theke download hobe (ekbar, ~500MB — VPS e sadharonoto fast).
- **AI backend** API (OpenCode Zen) — internet thakle chole, kono local model download lagbe na.
- **Security:** password base64 e jay (HTTPS na thakle sniff kora possible). Serious hole domain + nginx +
  SSL (Let's Encrypt) add korte hobe — bolba, guide dibo.
- **Disk:** `output/` folder e clip jome — majhe majhe purano job folder muche felba।
