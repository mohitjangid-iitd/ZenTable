# ZenTable — Features

## ZenTable Kya Hai?
ZenTable ek modern restaurant management platform hai jo digital menu, AR (Augmented Reality) menu, real-time order management, aur analytics ek jagah deta hai. Restaurant owners apne staff ko manage kar sakte hain, orders track kar sakte hain, aur business analytics dekh sakte hain — sab kuch ek dashboard se.

Live platform: https://zentable.in

---

## Core Features

### 1. Digital Menu
- QR code scan karo, menu khul jaata hai — koi app download nahi
- Mobile-friendly, fast loading
- Categories, images, descriptions, prices sab dikhta hai
- Veg/non-veg indicators
- Table-specific QR — customer seedha apni table se order kar sakta hai

### 2. AR Menu (Augmented Reality)
- QR code camera ke saamne rakho — 3D food models screen pe aa jaate hain
- Customer dish ko 360° rotate karke dekh sakta hai before ordering
- ZenTable ki team actual food ki 3D scanning karti hai aur models banati hai
- AR targets customize kiye ja sakte hain — table pe rakha card, physical menu, ya koi bhi specific cheez
- Technology: MindAR + Three.js (web-based, koi app nahi chahiye)

### 3. Real-Time Order Management
- Customer table se order karta hai → kitchen ko turant milta hai
- Kitchen staff items ready mark karta hai
- Waiter ko notification — item ready hai, serve karo
- Order status tracking: pending → ready → done
- Staff apni screen se live orders dekh sakte hain

### 4. Table Management
- Tables activate/deactivate karo
- Table ka current status dikhe — inactive, active, occupied, billed, paid
- Saari tables ek saath activate/close karne ka option
- Waiter call feature — customer button dabaye, waiter ko alert

### 5. Billing & Payments
- Automatic bill generation — done orders se
- Tax aur discount add karne ka option
- Multiple payment modes — cash, UPI, card
- Bill print/share option
- Payment status tracking

### 6. Staff Management
- Multiple roles: owner, waiter, kitchen, counter, blogger
- Har role ko sirf uska relevant dashboard dikhta hai
- Staff accounts owner khud bana sakta hai
- Active/inactive toggle — temporary disable without deleting

### 7. Analytics Dashboard (Owner)
- Aaj ki sales, revenue, order count
- Last 7 din ka daily breakdown
- Top selling items
- Payment mode breakdown (cash vs UPI vs card)
- Hourly order pattern

### 8. Multi-Restaurant Support
- Ek platform pe multiple restaurants
- Har restaurant ka alag data, alag staff, alag menu
- Admin panel se sab manage hota hai

### 9. Multi-Branch Support
- Ek brand ki multiple branches manage karo — ek hi dashboard se
- Har branch ka apna menu, staff, orders, aur analytics alag
- Owner apni saari branches ek jagah se dekh sakta hai
- Branch-level aur brand-level dono analytics available

### 10. Owner Self-Signup
- Restaurant owner khud signup kar sakta hai ZenTable pe
- Admin ko request jaati hai — approve ya reject ka option
- Approve hone ke baad owner apna restaurant setup kar sakta hai
- Koi manual onboarding ki zaroorat nahi

### 11. Blogging Platform
- ZenTable ka apna built-in blogging system hai
- Platform aur connected restaurants ke liye blog posts likho
- SEO-friendly — organic traffic aur audience engagement badhta hai
- Blogger role wale staff members blog posts create aur manage kar sakte hain

### 12. AI-Powered Tools
- **Photo to Menu** — menu ki photo upload karo, AI automatically items extract karke menu bana deta hai
- **AI Chatbot** — customers apne sawaal puch sakte hain menu, timings, restaurant info ke baare mein
- **Help Bot** — owners ko platform use karne mein madad karta hai

---

## Subscription Features
- **basic** — Digital menu, QR code
- **ordering** — Table ordering, kitchen queue, billing
- **analytics** — Owner analytics dashboard
- **ar_menu** — AR menu with 3D models

---

## Technology
- Web-based — koi app download nahi, browser se kaam karta hai
- Mobile aur desktop dono pe kaam karta hai
- Fast, lightweight frontend
- Secure JWT-based authentication
