# Staff Management

## Staff Roles — Overview
ZenTable mein 5 staff roles hain. Har role ko sirf uska relevant dashboard dikhta hai.

| Role | Kya Karta Hai |
|------|---------------|
| **owner** | Poora access — analytics, staff management, orders, billing, multi-branch management |
| **waiter** | Table management, order placement, billing |
| **kitchen** | Live order queue, items ready mark karna |
| **counter** | Table activate/deactivate, payment collect karna |
| **blogger** | Blog posts create aur manage karna |

---

## Har Role Ka Dashboard

### Owner
- Analytics dashboard — sales, revenue, top items
- Staff accounts banana aur manage karna
- Saari tables ka overview aur manage karna
- Full order history
- QR code generator
- Blog posts create aur manage karna
- Restaurent ki menu aur info manage karna
- AI-powered photo-to-menu tool use karna
- AI help bot use karna, analytics aur general help lene ke liye
- Multi-branch management — saari branches ek dashboard se

### Blogger
- Blog posts create, edit, aur publish karna
- Platform aur restaurant ke liye content manage karna

### Waiter
- Table status — kaun si table occupied, billed, paid
- Order place karna customer ki taraf se
- Order status track karna
- Bill generate karna
- Waiter calls receive karna

### Kitchen
- Live order queue — nayi orders turant dikhti hain
- Items ready mark karna (partial bhi — ek item ready, baaki pending)
- Orders ka status update karna

### Counter
- Tables activate/deactivate karna
- Payment collect karna
- Bills mark as paid

---

## Staff Account Banana (Owner ke liye)

1. Owner dashboard mein jaao
2. Staff Management section kholo
3. "Add Staff" button dabao
4. Fill karo:
   - Name
   - Username (login ke liye)
   - Password
   - Role select karo (waiter/kitchen/counter/blogger)
5. Save karo — account ready

---

## Multi-Branch Staff Management

- Agar restaurant ki multiple branches hain, toh har branch ke liye alag staff manage hota hai
- Owner apne dashboard se kisi bhi branch ke staff ko dekh aur manage kar sakta hai
- Staff sirf apni assigned branch ka data dekhta hai
- Owner ko saari branches ka combined view bhi milta hai

---

## Staff Login Kaise Karta Hai?
1. `zentable.in/login` pe jaao
2. Restaurant ID daalo (owner batayega)
3. Username aur password daalo
4. Login ke baad automatically role ka dashboard khulega

---

## Staff Account Manage Karna

### Password Change Karna
Owner dashboard → Staff Management → Staff ke naam pe click → Change Password

### Staff Temporarily Disable Karna
Owner dashboard → Staff Management → Active/Inactive toggle
- Disabled staff login nahi kar sakta
- Account delete nahi hota — baad mein re-enable kar sakte hain

### Staff Delete Karna
Owner dashboard → Staff Management → Delete button
- Permanent deletion — undo nahi hoga

---

## Security
- Har staff ka alag login — shared accounts mat banao
- Password strong rakhna — minimum 8 characters recommended
- JWT-based secure authentication — sessions automatically expire hote hain
- Waiter role analytics nahi dekh sakta
- Kitchen role billing nahi kar sakta
- Roles strict hain — cross-access nahi

---

## Common Questions

**Q: Kitne staff accounts bana sakte hain?**
A: Subscription ke hisaab se — ZenTable se confirm karo apne plan mein.

**Q: Owner ka password bhul gaya?**
A: ZenTable support se contact karo — `zentable.in@gmail.com`

**Q: Ek staff member multiple roles pe kaam kar sakta hai?**
A: Abhi ek account ek role — alag role ke liye alag account banana padega.

**Q: Staff ka username change ho sakta hai?**
A: Abhi directly nahi — old account delete karke naya banana padega. ZenTable support se bhi help le sakte hain (`zentable.in@gmail.com`).
