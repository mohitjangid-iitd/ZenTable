# 🍽️ AR Restaurant Menu Platform

A modern web application that brings restaurant menus to life through **Augmented Reality (AR)**. Customers can scan QR codes to view 3D models of dishes in AR, and explore beautiful customizable restaurant home pages.

## 🌟 Features

### For Customers:
- 📱 **AR Menu Experience** - Scan QR codes to view dishes in 3D using your phone camera
- 🏠 **Restaurant Home Page** - Beautiful landing pages for each restaurant
- 📸 **Screenshot & Share** - Capture and share AR experiences
- 🔄 **Interactive Controls** - Manual rotation controls for 3D models
- 🎨 **Smooth Animations** - Professional loading screens and transitions

### For Restaurant Owners:
- 🎨 **Full Customization** - Colors, fonts, branding per restaurant
- 📝 **Easy Content Management** - Simple JSON-based configuration
- 🖼️ **Featured Dishes** - Showcase signature items on home page
- 📍 **Contact Integration** - Display timings, location, social media
- 💰 **Recurring Revenue** - Customization services for premium themes

## 🚀 Project Structure

```
ar-menu-platform/
├── main.py                 # FastAPI backend
├── requirements.txt        # Python dependencies
├── data/                   # Restaurant configurations
│   ├── clint_one.json     # Restaurant 1 config
│   └── clint_two.json     # Restaurant 2 config
├── templates/              # HTML templates
│   ├── home.html          # Restaurant home page
│   └── ar_menu.html       # AR menu experience
└── static/                 # Static assets
    └── assets/
        ├── clint_one/     # Restaurant 1 assets
        │   ├── logo.png
        │   ├── banner.jpg
        │   ├── targets.mind
        │   └── *.glb      # 3D models
        └── clint_two/     # Restaurant 2 assets
```

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip

### Setup Steps

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd ar-menu-platform
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Create directory structure**
```bash
mkdir -p data templates static/assets
```

4. **Add your files**
- Place `home.html` and `ar_menu.html` in `templates/`
- Place restaurant JSON configs in `data/`
- Add 3D models and assets in `static/assets/{client_id}/`

5. **Run the application**
```bash
python main.py
```

6. **Access the app**
- Home Page: `http://localhost:8000/{client_id}`
- AR Menu: `http://localhost:8000/{client_id}/ar-menu`
- API: `http://localhost:8000/api/menu/{client_id}`

## 🎯 Routes

| Route | Description |
|-------|-------------|
| `/{client_id}` | Restaurant home/landing page |
| `/{client_id}/ar-menu` | AR menu experience |
| `/api/menu/{client_id}` | JSON API for menu data |

## 📝 Configuration

### Restaurant JSON Structure

Each restaurant has a JSON config file in `data/{client_id}.json`:

```json
{
  "restaurant": {
    "name": "Restaurant Name",
    "tagline": "Your tagline",
    "logo": "/static/assets/client_id/logo.png",
    "banner": "/static/assets/client_id/banner.jpg",
    "description": "About your restaurant...",
    "cuisine_type": "Type of cuisine",
    "phone": "+91 XXXXX XXXXX",
    "email": "contact@restaurant.com",
    "address": "Full address",
    "timings": {
      "lunch": "12:00 PM - 3:00 PM",
      "dinner": "7:00 PM - 11:00 PM",
      "closed": "Monday"
    },
    "social": {
      "instagram": "https://instagram.com/...",
      "facebook": "https://facebook.com/...",
      "twitter": "https://twitter.com/..."
    }
  },
  "theme": {
    "primary_color": "#D4AF37",
    "secondary_color": "#1a1a1a",
    "accent_color": "#8B4513",
    "text_color": "#333333",
    "background": "#ffffff",
    "font_primary": "Playfair Display",
    "font_secondary": "Poppins"
  },
  "featured_dishes": [
    {
      "name": "Dish Name",
      "image": "/static/assets/client_id/dish.jpg",
      "price": "₹450",
      "description": "Brief description"
    }
  ],
  "items": [
    {
      "name": "Dish Name",
      "price": "₹450",
      "model": "client_id/model.glb",
      "position": "0 0 0",
      "scale": "0.5 0.5 0.5",
      "rotation": "0 0 0",
      "auto_rotate": true,
      "rotate_speed": 8000,
      "category": "Main Course"
    }
  ]
}
```

## 🎨 Customization Guide

### Theme Colors
Customize in JSON config:
- `primary_color` - Main brand color (CTAs, headings)
- `secondary_color` - Dark/contrast color
- `accent_color` - Highlight color
- `text_color` - Body text
- `background` - Page background

### Fonts
Choose from Google Fonts:
- `font_primary` - Headings (serif recommended)
- `font_secondary` - Body text (sans-serif recommended)

Popular combinations:
- Luxury: Playfair Display + Poppins
- Modern: Montserrat + Open Sans
- Classic: Merriweather + Lato

## 🔧 AR Setup

### Creating AR Targets

1. **Get MindAR Compiler**
   - Visit: https://hiukim.github.io/mind-ar-js-doc/tools/compile

2. **Prepare Target Image**
   - Use restaurant logo, menu cover, or custom marker
   - High contrast, detailed images work best
   - Recommended size: 1024x1024px or higher

3. **Compile Target**
   - Upload image to compiler
   - Download `targets.mind` file
   - Place in `/static/assets/{client_id}/targets.mind`

### 3D Model Requirements

- **Format**: `.glb` (compressed GLTF)
- **Size**: < 5MB recommended for fast loading
- **Orientation**: Model should face forward (0, 0, 0)
- **Scale**: Adjust in JSON config

**Free 3D Model Resources:**
- Sketchfab
- TurboSquid
- CGTrader
- Free3D

## 📱 User Flow

### Customer Journey:

1. **QR Code Scan** → Lands on AR Menu page
2. **AR Experience** → Views dishes in 3D AR
3. **"View Menu" Button** → Goes to restaurant home page
4. **Explore Restaurant** → Reads about restaurant, sees featured dishes
5. **"Experience in AR"** → Returns to AR menu

### Flow Diagram:
```
QR Code → AR Menu ←→ Restaurant Home Page
            ↓
    [Screenshot/Share]
```

## 🚀 Deployment

### Production Checklist:

- [ ] Update all placeholder images with real photos
- [ ] Add actual 3D models for all dishes
- [ ] Configure proper domain/hosting
- [ ] Set up HTTPS (required for camera access)
- [ ] Test on multiple devices
- [ ] Optimize images and models
- [ ] Set up analytics (optional)

### Recommended Hosting:
- **DigitalOcean App Platform**
- **Heroku**
- **AWS EC2**
- **Google Cloud Run**

## 💰 Monetization Ideas

1. **Base Package** - Standard template + AR menu
2. **Premium Themes** - Custom designed home pages
3. **Monthly Subscription** - Updates, new features
4. **Analytics Dashboard** - Track customer engagement
5. **Custom 3D Models** - Professional food modeling service

## 🎯 Future Enhancements

- [ ] Admin dashboard for restaurant owners
- [ ] Analytics and insights
- [ ] Order integration
- [ ] Multi-language support
- [ ] Table reservation system
- [ ] Customer reviews section
- [ ] Menu filtering by dietary preferences
- [ ] Real-time menu updates

## 📄 Dependencies

```txt
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
jinja2>=3.1.2
python-multipart>=0.0.6
```

## 🐛 Troubleshooting

### AR not working:
- Ensure HTTPS is enabled (camera requires secure context)
- Check `targets.mind` file exists
- Verify 3D model paths are correct
- Test with good lighting conditions

### Models not loading:
- Check file paths in JSON
- Ensure models are in `.glb` format
- Verify file size (< 10MB recommended)
- Check browser console for errors

### Styling issues:
- Verify Google Fonts are loading
- Check CSS custom properties in theme
- Test on multiple browsers

## 📞 Support

For issues or questions:
- Create an issue on GitHub
- Email: support@yourplatform.com

## 📜 License

MIT License - feel free to use for commercial projects

---

**Built with ❤️ for revolutionizing restaurant dining experiences**
