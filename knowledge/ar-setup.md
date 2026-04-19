# AR Menu — Setup & How It Works

## AR Menu Kya Hai?
ZenTable ka AR (Augmented Reality) menu ek premium feature hai jisme customer apna phone camera QR code ya kisi specific cheez ke saamne rakhta hai — aur screen pe 3D food model aa jaata hai. Dish ko rotate karke, zoom karke dekha ja sakta hai before ordering. Koi app download nahi chahiye — sirf browser.

---

## Customer Ke Liye Kaise Kaam Karta Hai?
1. Restaurant mein QR code scan karo (table pe hoga ya menu card pe)
2. AR menu link khulega browser mein
3. Camera permission do
4. QR code ya designated target (table card, physical menu) ko camera ke saamne rakho
5. 3D food model screen pe appear ho jaayega
6. Model rotate karo, zoom karo, dish explore karo
7. Order button se seedha order place karo

---

## Restaurant Ke Liye Setup Process

### ZenTable Ka Kaam:
AR menu setup mein restaurant owner ko kuch nahi karna padta. Poora setup ZenTable ki team karti hai:

1. **3D Model Creation** — ZenTable ki team restaurant ke food items ki 3D scanning/modeling karti hai
2. **GLB Files** — 3D models `.glb` format mein ban ke platform pe upload hote hain
3. **AR Targets Setup** — Tracking targets configure kiye jaate hain
4. **Menu Integration** — Models menu items se link ho jaate hain
5. **Testing** — ZenTable team test karke confirm karti hai

Restaurant owner ko sirf batana hai ki kaun se dishes ke 3D models chahiye.

### AR Targets Kya Hote Hain?
AR targets woh physical cheez hoti hai jisko camera "recognize" karta hai aur uske upar 3D model show karta hai. Yeh customize kiye ja sakte hain:
- **Table QR card** — Table pe rakha printed card
- **Physical menu** — Printed menu book
- **Custom printed material** — Restaurant ka koi bhi branded item

ZenTable targets restaurant ke brand ke hisaab se customize kar sakti hai.

---

## Technical Details (Staff ke liye)
- Technology: MindAR + Three.js (web-based AR)
- 3D model format: `.glb` (GL Transmission Format)
- Works on: Android Chrome, iOS Safari (modern browsers)
- Internet connection chahiye AR ke liye
- Models securely serve hote hain — direct access nahi

---

## AR Menu Kis Plan Mein Available Hai?
AR menu `ar_menu` feature wale subscription mein available hai. ZenTable se contact karo AR menu add karne ke liye.

---

## Common Questions

**Q: Kya customer ko koi app download karni padti hai?**
A: Nahi — sirf phone ka browser chahiye. QR scan karo aur AR seedha browser mein khul jaata hai.

**Q: Kaun se phones pe kaam karta hai?**
A: Android aur iOS dono pe modern browsers pe kaam karta hai (Chrome, Safari).

**Q: Agar 3D model add karwana ho naye dish ka?**
A: ZenTable team se contact karo — woh 3D model banake add kar denge.

**Q: AR target customize ho sakta hai?**
A: Haan — table card, physical menu, ya koi bhi printed material AR target ban sakta hai. ZenTable team se discuss karo.
