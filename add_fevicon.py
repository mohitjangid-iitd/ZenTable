import os

OLD_FAVICON = '<link rel="icon" href="data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'%236C63FF\' stroke-width=\'2.2\' stroke-linecap=\'round\' stroke-linejoin=\'round\'><path d=\'M3 11l19-9-9 19-2-8-8-2z\'/></svg>" />'

NEW_FAVICON = '''  <link rel="icon" type="image/x-icon" href="/static/assets/zentable/favicon.ico" />
  <link rel="icon" type="image/png" sizes="32x32" href="/static/assets/zentable/favicon_32.png" />
  <link rel="icon" type="image/png" sizes="16x16" href="/static/assets/zentable/favicon_16.png" />'''

files = [
    "templates/landing.html",
    "templates/login.html",
    "templates/admin_login.html",
    "templates/admin.html",
    "templates/home.html",
    "templates/menu.html",
    "templates/ar_menu.html",
    "templates/staff_waiter.html",
    "templates/staff_kitchen.html",
    "templates/staff_counter.html",
    "templates/staff_owner.html",
]

for f in files:
    content = open(f, encoding="utf-8").read()
    if OLD_FAVICON in content:
        content = content.replace(OLD_FAVICON, NEW_FAVICON)
        open(f, "w", encoding="utf-8").write(content)
        print(f"✅ Updated: {f}")
    else:
        print(f"⏭ Skipped (old favicon not found): {f}")