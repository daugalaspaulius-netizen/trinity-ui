# Trinity Deployment Guide

## 🚀 Quick Deploy Options

### Option 1: Render.com (Recommended - FREE)

1. **Sign up:** https://render.com (Free tier)
2. **Connect GitHub:**
   - Push this folder to GitHub
   - Or use Render's Git integration
3. **Deploy:**
   - Click "New +" → "Web Service"
   - Connect repository
   - Render auto-detects `render.yaml`
   - Click "Create Web Service"
4. **Result:**
   - Live HTTPS URL: `https://trinity-ui-xxxx.onrender.com`
   - Auto SSL certificate
   - Mobile microphone works instantly

**Pros:**
- 100% free
- HTTPS by default
- Easy deployment
- Good for testing

**Cons:**
- Free tier sleeps after 15 min inactivity
- Limited resources (512MB RAM)

---

### Option 2: Google Cloud Run

1. **Prerequisites:**
   - Google Cloud account
   - `gcloud` CLI installed

2. **Build & Deploy:**
   ```powershell
   # Authenticate
   gcloud auth login
   
   # Set project
   gcloud config set project YOUR_PROJECT_ID
   
   # Build image
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/trinity-ui
   
   # Deploy
   gcloud run deploy trinity-ui \
     --image gcr.io/YOUR_PROJECT_ID/trinity-ui \
     --platform managed \
     --region europe-west1 \
     --allow-unauthenticated \
     --port 8000
   ```

3. **Result:**
   - Live URL: `https://trinity-ui-xxxx-ew.a.run.app`
   - Auto-scaling
   - Pay-per-use

**Pros:**
- Professional Google infrastructure
- Auto-scaling
- Good performance

**Cons:**
- Requires Google Cloud billing account
- More complex setup
- Costs money (but minimal for low traffic)

---

### Option 3: Railway.app (Alternative FREE)

1. **Sign up:** https://railway.app
2. **Deploy:**
   - Click "New Project" → "Deploy from GitHub"
   - Select repository
   - Railway auto-detects Docker
3. **Result:**
   - Live HTTPS URL
   - $5 free credit monthly

---

## 📱 Testing After Deployment

Once deployed, you'll get a URL like:
- `https://trinity-ui.onrender.com` (Render)
- `https://trinity-ui-xxxx.a.run.app` (Cloud Run)

**Test on phone:**
1. Open the HTTPS URL
2. Click "Irasyti balsa"
3. Browser asks for microphone permission → Allow
4. Record and send message
5. Trinity responds

---

## 🔧 Current Limitation

**Trinity Backend (Mistral 7B model):**
- Currently runs in MOCK mode (simulated responses)
- Real 7B model needs ~16GB RAM + GPU
- Cloud deployment of full model would be expensive

**Solutions:**
1. Keep UI deployed for testing (works perfectly)
2. Run full model locally when needed
3. Use quantized (4-bit) model for cloud (future optimization)

---

## 🎯 Recommended Path

1. **Deploy UI to Render.com** (5 minutes, free, HTTPS)
2. **Test microphone on phone** (verify it works)
3. **Optimize model later** (quantization for cloud or keep local)

Want me to help with deployment? I can:
- Push to GitHub for you
- Set up Render.com deployment
- Generate deployment script
