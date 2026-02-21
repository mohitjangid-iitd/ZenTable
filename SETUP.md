# 🚀 Quick Setup Guide

## Step-by-Step Implementation

### 1️⃣ File Structure Setup (5 mins)

```bash
# Create directories
mkdir -p templates
mkdir -p data
mkdir -p static/assets/clint_one
mkdir -p static/assets/clint_two

# Move files
mv main.py ./
mv requirements.txt ./
mv home.html templates/
mv ar_menu.html templates/
mv clint_one.json data/
mv clint_two.json data/
```

### 2️⃣ Install Dependencies (2 mins)

```bash
pip install -r requirements.txt
```

### 3️⃣ Add Your Assets (15 mins)

For each restaurant (`clint_one`, `clint_two`), add:

```
static/assets/clint_one/
├── logo.png          # Restaurant logo (transparent PNG, 500x500px)
├── banner.jpg        # Hero banner (1920x1080px)
├── targets.mind      # AR target file (from MindAR compiler)
├── butter_chicken.jpg
├── dal_makhani.jpg
├── paneer_tikka.jpg
└── *.glb            # 3D models (casio.glb, Donut.glb, perk.glb)
```

### 4️⃣ Configure Restaurant Data (10 mins)

Edit `data/clint_one.json`:
- Update restaurant name, description, contact info
- Set theme colors and fonts
- Add featured dishes with image paths
- Configure AR menu items

### 5️⃣ Create AR Targets (10 mins)

1. Go to: https://hiukim.github.io/mind-ar-js-doc/tools/compile
2. Upload your target image (restaurant logo or custom marker)
3. Download `targets.mind`
4. Place in `static/assets/{client_id}/targets.mind`

### 6️⃣ Get 3D Models (20 mins)

**Option A: Use Free Models**
- Sketchfab: https://sketchfab.com/feed
- Search for "food", download as `.glb`

**Option B: Use Placeholder**
- Copy existing models from your current setup
- Update paths in JSON config

### 7️⃣ Test Locally (5 mins)

```bash
# Start server
python main.py

# Access in browser:
# Home: http://localhost:8000/clint_one
# AR:   http://localhost:8000/clint_one/ar-menu
```

### 8️⃣ Test on Phone (10 mins)

**For local testing:**
```bash
# Find your local IP
ipconfig getifaddr en0  # Mac
ipconfig               # Windows

# Access from phone on same WiFi:
http://YOUR_IP:8000/clint_one/ar-menu
```

**Note:** AR requires HTTPS in production!

---

## 📱 Testing Checklist

- [ ] Home page loads with correct branding
- [ ] All images display properly
- [ ] Theme colors match restaurant brand
- [ ] Contact info is accurate
- [ ] AR menu page loads
- [ ] Camera permission works
- [ ] QR/Marker detection works
- [ ] 3D models load and display
- [ ] Carousel scrolls smoothly
- [ ] Rotation controls work
- [ ] Screenshot button works
- [ ] Share button works
- [ ] "View Menu" button navigates correctly

---

## 🎨 Quick Customization

### Change Colors Only:
Edit `data/clint_one.json` → `theme` section

### Change Content Only:
Edit `data/clint_one.json` → `restaurant` section

### Change Both:
Edit entire JSON + replace images in `static/assets/`

---

## 🐛 Common Issues & Fixes

### Issue: Models not loading
**Fix:** Check file paths in JSON match actual files

### Issue: AR camera not starting
**Fix:** Must use HTTPS in production (camera API requirement)

### Issue: Target not detecting
**Fix:** 
- Use high-contrast target image
- Ensure good lighting
- Print QR/marker at decent size (10cm+)

### Issue: Styling broken
**Fix:** Check if Google Fonts are loading (internet required)

---

## 🚀 Deploy to Production

### Using DigitalOcean App Platform:

1. Push code to GitHub
2. Connect repository to App Platform
3. Set Python version: 3.11
4. Run command: `uvicorn main:app --host 0.0.0.0 --port 8080`
5. Add custom domain
6. **Enable HTTPS** (automatic with custom domain)

### Using Heroku:

1. Install Heroku CLI
2. ```bash
   heroku create your-app-name
   git push heroku main
   ```
3. App will have HTTPS by default

---

## 💰 Client Onboarding Process

1. **Initial Meeting**
   - Gather: logo, photos, menu, branding guidelines
   - Discuss: theme preferences, featured dishes

2. **Setup (1-2 days)**
   - Create JSON config
   - Process images
   - Find/create 3D models
   - Generate AR targets

3. **Review & Revisions**
   - Client reviews staging site
   - Make requested changes

4. **Launch**
   - Deploy to production
   - Generate QR codes
   - Provide marketing materials

5. **Ongoing**
   - Monthly updates (optional)
   - New dish additions
   - Seasonal themes

---

## 📊 Pricing Suggestion

- **Setup Fee:** ₹15,000 - ₹25,000
  - Includes: Initial setup, custom theme, 10 AR models
  
- **Monthly:** ₹2,000 - ₹5,000
  - Updates, hosting, support
  
- **Premium Customization:** ₹10,000+
  - Fully custom design, animations, effects

---

**Need help? Create an issue or contact support!**
