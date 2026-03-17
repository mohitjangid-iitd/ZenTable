import os

OLD = '''<div style="text-align:center;padding:10px;font-size:0.72rem;color:rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;gap:6px;">
    Powered by
    <img src="/static/assets/zentable/logo_dark_512.png" alt="ZenTable" style="width:13px;height:13px;object-fit:contain;opacity:0.5;vertical-align:middle;" />
    <span>ZenTable</span>
</div>'''

POWERED_DARK = '''<div style="text-align:center;padding:10px;font-size:0.72rem;color:rgba(255,255,255,0.3);display:flex;align-items:center;justify-content:center;gap:6px;">
    Powered by
    <img src="/static/assets/zentable/logo_white_192.png" alt="{{ site.name }}" style="width:13px;height:13px;object-fit:contain;opacity:0.5;vertical-align:middle;" />
    <span>{{ site.name }}</span>
</div>'''

POWERED_LIGHT = '''<div style="text-align:center;padding:10px;font-size:0.72rem;color:rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;gap:6px;">
    Powered by
    <img src="/static/assets/zentable/logo_dark_512.png" alt="{{ site.name }}" style="width:13px;height:13px;object-fit:contain;opacity:0.5;vertical-align:middle;" />
    <span>{{ site.name }}</span>
</div>'''

dark_files = [
    
]

light_files = [
    "templates/staff_waiter.html",
    "templates/staff_kitchen.html",
    "templates/staff_counter.html",
    "templates/staff_owner.html",
    "templates/admin.html",
    "templates/home.html",
    "templates/menu.html",
    "templates/ar_menu.html",
]

for f in dark_files:
    content = open(f, encoding="utf-8").read()
    if OLD in content:
        content = content.replace(OLD, POWERED_DARK)
        open(f, "w", encoding="utf-8").write(content)
        print(f"✅ fixed dark: {f}")
    else:
        print(f"⚠ OLD not found: {f}")

for f in light_files:
    content = open(f, encoding="utf-8").read()
    if OLD in content:
        content = content.replace(OLD, POWERED_LIGHT)
        open(f, "w", encoding="utf-8").write(content)
        print(f"✅ fixed light: {f}")
    else:
        print(f"⚠ OLD not found: {f}")