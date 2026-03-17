// ════════════════════════════════
// STATE
// ════════════════════════════════
let allRestaurants = [];
let lastCreatedClientId = null;
let currentEditClientId = null;
let currentEditData = null;
let currentEditItemIndex = -1;
let currentPasswordStaffId = null;

// ════════════════════════════════
// INIT
// ════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    loadOverview();
});

// ════════════════════════════════
// TABS
// ════════════════════════════════
function switchTab(name, btn) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    btn.classList.add('active');
    if (name === 'restaurants') renderRestGrid();
    if (name === 'staff') populateStaffRestSelect();
}

function switchEditTab(name, btn) {
    document.querySelectorAll('.json-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.section-editor').forEach(e => e.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('edit-' + name).classList.add('active');
    if (name === 'items') renderItemsList();
}

// ════════════════════════════════
// TOAST
// ════════════════════════════════
function toast(msg, type='') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'show ' + type;
    setTimeout(() => el.className = '', 2800);
}

// ════════════════════════════════
// MODALS
// ════════════════════════════════
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// ════════════════════════════════
// OVERVIEW
// ════════════════════════════════
async function loadOverview(period='alltime') {
    const res = await fetch(`/api/admin/overview?period=${period}`);
    const d = await res.json();
    allRestaurants = d.restaurants;

    // Stats
    const s = d.stats;
    document.getElementById('overall-stats').innerHTML = `
        <div class="stat-card accent-purple">
            <div class="stat-label">Restaurants</div>
            <div class="stat-value">${s.total_restaurants}</div>
            <div class="stat-sub">${s.total_staff} active staff</div>
        </div>
        <div class="stat-card accent-green">
            <div class="stat-label">Today Orders</div>
            <div class="stat-value">${s.today_orders}</div>
            <div class="stat-sub">All restaurants</div>
        </div>
        <div class="stat-card accent-orange">
            <div class="stat-label">Today Revenue</div>
            <div class="stat-value">₹${s.today_revenue.toLocaleString()}</div>
            <div class="stat-sub">Paid bills</div>
        </div>
        <div class="stat-card accent-red">
            <div class="stat-label">All-time Revenue</div>
            <div class="stat-value">₹${s.alltime_revenue.toLocaleString()}</div>
            <div class="stat-sub">${s.alltime_orders} total orders</div>
        </div>
    `;

    // Restaurant summary table — clickable rows
    const tbody = document.getElementById('overview-rest-body');
    if (d.restaurants.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty">Koi restaurant nahi</td></tr>';
    } else {
        tbody.innerHTML = d.restaurants.map(r => `
            <tr class="rest-row" onclick="drillIntoRestaurant('${r.client_id}', '${r.name.replace(/'/g,"\\'")}')">
                <td>
                    <div style="font-weight:500">${r.name}</div>
                    <div class="mono">${r.client_id}</div>
                </td>
                <td>${r.today_orders}</td>
                <td>₹${r.today_revenue.toLocaleString()}</td>
                <td>${r.staff_count}</td>
            </tr>
        `).join('');
    }

    // Top dishes
    const dishEl = document.getElementById('overall-dishes');
    if (d.top_dishes.length === 0) {
        dishEl.innerHTML = '<div class="empty">Abhi koi orders nahi</div>';
    } else {
        const maxQty = d.top_dishes[0].qty;
        dishEl.innerHTML = d.top_dishes.map((item, i) => `
            <div class="dish-row">
                <div class="dish-rank">#${i+1}</div>
                <div class="dish-name">${item.name}</div>
                <div class="dish-bar-wrap"><div class="dish-bar" style="width:${Math.round(item.qty/maxQty*100)}%"></div></div>
                <div class="dish-qty">${item.qty}x</div>
                <div class="dish-rev">₹${item.revenue.toLocaleString()}</div>
            </div>
        `).join('');
    }
}

// ════════════════════════════════
// RESTAURANTS
// ════════════════════════════════
async function loadRestaurants() {
    const res = await fetch('/api/admin/overview');
    const d = await res.json();
    allRestaurants = d.restaurants;
    renderRestGrid();
}

function renderRestGrid() {
    const grid = document.getElementById('rest-grid');
    if (allRestaurants.length === 0) {
        grid.innerHTML = '<div class="empty">Koi restaurant nahi — Add karo!</div>';
        return;
    }
    grid.innerHTML = allRestaurants.map(r => `
        <div class="rest-card">
            <div class="rest-card-top">
                <div>
                    <div class="rest-name">${r.name}</div>
                    <div class="rest-id">${r.client_id}</div>
                </div>
                <div class="rest-actions">
                    <button class="btn btn-ghost btn-icon btn-sm" onclick="openEditRestaurant('${r.client_id}')" title="Edit">✏️</button>
                    <button class="btn btn-danger btn-icon btn-sm" onclick="deleteRestaurant('${r.client_id}', '${r.name}')" title="Delete">🗑️</button>
                </div>
            </div>
            <div class="rest-meta">
                <div class="rest-meta-item">Tables: <span>${r.num_tables}</span></div>
                <div class="rest-meta-item">Staff: <span>${r.staff_count}</span></div>
                <div class="rest-meta-item">Today: <span>${r.today_orders} orders</span></div>
                <div class="rest-meta-item">Revenue: <span>₹${r.today_revenue.toLocaleString()}</span></div>
            </div>
            ${r.cuisine_type ? `<div style="font-size:0.72rem;color:var(--muted);margin-top:8px">${r.cuisine_type}</div>` : ''}
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;">
                ${(r.features || ['basic']).map(f => `<span style="font-size:0.6rem;padding:2px 7px;border-radius:3px;background:rgba(108,99,255,0.12);color:var(--primary);border:1px solid var(--border);font-family:var(--font-m)">${f}</span>`).join('')}
            </div>
            <button class="btn btn-ghost btn-sm" style="width:100%;margin-top:12px;font-size:0.78rem;" onclick="downloadAllQRs('${r.client_id}')">⬇ Download All QR Codes</button>
        </div>
    `).join('');
}

function openAddRestaurant() {
    ['nr-id','nr-name','nr-tagline','nr-cuisine','nr-phone','nr-email','nr-address','nr-desc','nr-lunch','nr-dinner','nr-closed','nr-instagram','nr-facebook','nr-twitter'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    document.getElementById('nr-tables').value = 6;
    openModal('modal-add-rest');
}

async function createRestaurant() {
    const client_id = document.getElementById('nr-id').value.trim().toLowerCase().replace(/ /g,'_');
    const name = document.getElementById('nr-name').value.trim();
    if (!client_id || !name) { toast('Restaurant ID aur Name required hain', 'error'); return; }
    const body = {
        client_id, name,
        num_tables: parseInt(document.getElementById('nr-tables').value) || 6,
        tagline:    document.getElementById('nr-tagline').value.trim(),
        cuisine_type: document.getElementById('nr-cuisine').value.trim(),
        phone:      document.getElementById('nr-phone').value.trim(),
        email:      document.getElementById('nr-email').value.trim(),
        address:    document.getElementById('nr-address').value.trim(),
        description: document.getElementById('nr-desc').value.trim(),
        lunch:      document.getElementById('nr-lunch').value.trim(),
        dinner:     document.getElementById('nr-dinner').value.trim(),
        closed:     document.getElementById('nr-closed').value.trim(),
        instagram:  document.getElementById('nr-instagram').value.trim(),
        facebook:   document.getElementById('nr-facebook').value.trim(),
        twitter:    document.getElementById('nr-twitter').value.trim(),
    };
    const res = await fetch('/api/admin/restaurant', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    const d = await res.json();
    if (res.ok) {
        lastCreatedClientId = client_id;
        toast(`'${name}' create ho gaya!`, 'success');
        closeModal('modal-add-rest');
        allRestaurants = [];
        await loadOverview();
        renderRestGrid();
        populateStaffRestSelect();
        // Preview button show karo in rest-grid
        const previewBtn = document.getElementById('preview-new-btn');
        const createBtn = document.getElementById('create-rest-btn');
        if (previewBtn) { previewBtn.style.display = 'inline-flex'; }
        if (createBtn) { createBtn.textContent = 'Create Another'; }
    } else {
        toast(d.detail || 'Error', 'error');
    }
}

async function openEditRestaurant(client_id) {
    const res = await fetch(`/api/admin/restaurant/${client_id}/json`);
    if (!res.ok) { toast('Load failed', 'error'); return; }
    currentEditData = await res.json();
    currentEditClientId = client_id;

    document.getElementById('edit-rest-title').textContent = `Edit — ${currentEditData.restaurant.name}`;

    // Fill info
    const r = currentEditData.restaurant;
    document.getElementById('ei-name').value     = r.name || '';
    document.getElementById('ei-tables').value   = r.num_tables || 6;
    document.getElementById('ei-tagline').value  = r.tagline || '';
    document.getElementById('ei-desc').value     = r.description || '';
    document.getElementById('ei-cuisine').value  = r.cuisine_type || '';
    document.getElementById('ei-phone').value    = r.phone || '';
    document.getElementById('ei-email').value    = r.email || '';
    document.getElementById('ei-address').value  = r.address || '';
    document.getElementById('ei-logo').value     = r.logo || '';
    document.getElementById('ei-banner').value   = r.banner || '';
    document.getElementById('ei-lunch').value    = r.timings?.lunch || '';
    document.getElementById('ei-dinner').value   = r.timings?.dinner || '';
    document.getElementById('ei-closed').value   = r.timings?.closed || '';
    document.getElementById('ei-instagram').value = r.social?.instagram || '';
    document.getElementById('ei-facebook').value  = r.social?.facebook || '';
    document.getElementById('ei-twitter').value   = r.social?.twitter || '';

    // Fill features
    const activeFeatures = currentEditData.subscription?.features || ['basic'];
    ['ordering','analytics','ar_menu'].forEach(f => {
        const cb = document.getElementById(`feat-${f}`);
        if (cb) cb.checked = activeFeatures.includes(f);
    });

    // Fill theme
    const t = currentEditData.theme || {};
    const setColor = (id, val) => {
        document.getElementById(id).value = val || '';
        try { document.getElementById(id+'-picker').value = val || '#000000'; } catch(e){}
    };
    setColor('et-primary', t.primary_color);
    setColor('et-secondary', t.secondary_color);
    setColor('et-accent', t.accent_color);
    setColor('et-text', t.text_color);
    setColor('et-bg', t.background);
    document.getElementById('et-font-primary').value = t.font_primary || 'Playfair Display';
    document.getElementById('et-font-secondary').value = t.font_secondary || 'Poppins';

    // Reset to info tab
    document.querySelectorAll('.json-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.section-editor').forEach(e => e.classList.remove('active'));
    document.querySelector('.json-tab').classList.add('active');
    document.getElementById('edit-info').classList.add('active');

    openModal('modal-edit-rest');
}

async function saveRestaurant() {
    if (!currentEditData || !currentEditClientId) return;

    // Collect info
    const r = currentEditData.restaurant;
    r.name         = document.getElementById('ei-name').value.trim();
    r.num_tables   = parseInt(document.getElementById('ei-tables').value) || r.num_tables;
    r.tagline      = document.getElementById('ei-tagline').value.trim();
    r.description  = document.getElementById('ei-desc').value.trim();
    r.cuisine_type = document.getElementById('ei-cuisine').value.trim();
    r.phone        = document.getElementById('ei-phone').value.trim();
    r.email        = document.getElementById('ei-email').value.trim();
    r.address      = document.getElementById('ei-address').value.trim();
    r.logo         = document.getElementById('ei-logo').value.trim();
    r.banner       = document.getElementById('ei-banner').value.trim();
    r.timings = {
        lunch:  document.getElementById('ei-lunch').value.trim(),
        dinner: document.getElementById('ei-dinner').value.trim(),
        closed: document.getElementById('ei-closed').value.trim(),
    };
    r.social = {
        instagram: document.getElementById('ei-instagram').value.trim(),
        facebook:  document.getElementById('ei-facebook').value.trim(),
        twitter:   document.getElementById('ei-twitter').value.trim(),
    };

    // Collect features
    const selectedFeatures = ['basic'];
    ['ordering','analytics','ar_menu'].forEach(f => {
        const cb = document.getElementById(`feat-${f}`);
        if (cb && cb.checked) selectedFeatures.push(f);
    });
    currentEditData.subscription = { features: selectedFeatures };

    // Collect theme
    currentEditData.theme = {
        primary_color:   document.getElementById('et-primary').value.trim(),
        secondary_color: document.getElementById('et-secondary').value.trim(),
        accent_color:    document.getElementById('et-accent').value.trim(),
        text_color:      document.getElementById('et-text').value.trim(),
        background:      document.getElementById('et-bg').value.trim(),
        font_primary:    document.getElementById('et-font-primary').value,
        font_secondary:  document.getElementById('et-font-secondary').value,
    };

    const res = await fetch(`/api/admin/restaurant/${currentEditClientId}/json`, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ data: currentEditData })
    });
    if (res.ok) {
        toast('Saved!', 'success');
        closeModal('modal-edit-rest');
        allRestaurants = [];
        await loadOverview();
        renderRestGrid();
    } else {
        toast('Save failed', 'error');
    }
}

async function deleteRestaurant(client_id, name) {
    if (!confirm(`'${name}' ko permanently delete karna hai? Ye action undo nahi hoga.`)) return;
    const res = await fetch(`/api/admin/restaurant/${client_id}`, { method:'DELETE' });
    if (res.ok) {
        toast(`'${name}' delete ho gaya`, 'success');
        allRestaurants = [];
        await loadOverview();
        renderRestGrid();
        populateStaffRestSelect();
    } else {
        toast('Delete failed', 'error');
    }
}

// ════════════════════════════════
// DISHES
// ════════════════════════════════
function renderItemsList() {
    const el = document.getElementById('items-list');
    const items = currentEditData?.items || [];
    if (items.length === 0) {
        el.innerHTML = '<div class="empty">Koi dish nahi — Add karo!</div>';
        return;
    }
    el.innerHTML = items.map((item, i) => `
        <div class="item-row">
            <img class="item-img" src="${item.image || ''}" onerror="this.style.display='none'" alt="">
            <div class="item-info">
                <div class="item-name">
                    <span class="veg-dot ${item.veg ? 'veg' : 'nonveg'}"></span>
                    ${item.name}
                </div>
                <div class="item-meta">${item.category || ''} &nbsp;·&nbsp; ${item.sizes ? item.sizes.map(s => s.label + ': ' + s.price).join(' / ') : (item.price || '')}</div>
                <div class="item-meta" style="margin-top:3px">${item.description || ''}</div>
            </div>
            <div class="item-actions">
                <button class="btn btn-ghost btn-icon btn-sm" onclick="openEditItem(${i})">✏️</button>
                <button class="btn btn-danger btn-icon btn-sm" onclick="deleteItem(${i})">🗑️</button>
            </div>
        </div>
    `).join('');
}

function openAddItem() {
    currentEditItemIndex = -1;
    document.getElementById('dish-modal-title').textContent = 'Dish Add Karo';
    ['di-name','di-price','di-category','di-desc','di-ingredients','di-image','di-model'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('di-position').value = '0 0 0';
    document.getElementById('di-scale').value = '2 2 2';
    document.getElementById('di-rotation').value = '0 0 0';
    document.getElementById('di-rotatespeed').value = '10000';
    document.getElementById('di-veg').value = 'true';
    document.getElementById('di-autorotate').value = 'true';
    document.getElementById('di-featured').value = 'true';
    // Reset size mode
    document.getElementById('di-multisize').checked = false;
    document.getElementById('di-sizes-list').innerHTML = '';
    document.getElementById('di-price-single').style.display = '';
    document.getElementById('di-price-multi').style.display = 'none';
    openModal('modal-dish');
}

function openEditItem(index) {
    currentEditItemIndex = index;
    const item = currentEditData.items[index];
    document.getElementById('dish-modal-title').textContent = 'Dish Edit Karo';
    document.getElementById('di-name').value        = item.name || '';
    document.getElementById('di-price').value       = item.price || '';
    document.getElementById('di-category').value    = item.category || '';
    document.getElementById('di-desc').value        = item.description || '';
    document.getElementById('di-ingredients').value = item.ingredients || '';
    document.getElementById('di-image').value       = item.image || '';
    document.getElementById('di-model').value       = item.model || '';
    document.getElementById('di-position').value    = item.position || '0 0 0';
    document.getElementById('di-scale').value       = item.scale || '2 2 2';
    document.getElementById('di-rotation').value    = item.rotation || '0 0 0';
    document.getElementById('di-rotatespeed').value = item.rotate_speed || 10000;
    document.getElementById('di-veg').value         = String(item.veg ?? true);
    document.getElementById('di-autorotate').value  = String(item.auto_rotate ?? true);
    document.getElementById('di-featured').value    = String(item.featured ?? true);
    // Sizes
    if (item.sizes && item.sizes.length > 0) {
        document.getElementById('di-multisize').checked = true;
        document.getElementById('di-price-single').style.display = 'none';
        document.getElementById('di-price-multi').style.display = '';
        const list = document.getElementById('di-sizes-list');
        list.innerHTML = '';
        item.sizes.forEach(s => addSizeRow(s.label, s.price));
    } else {
        document.getElementById('di-multisize').checked = false;
        document.getElementById('di-price-single').style.display = '';
        document.getElementById('di-price-multi').style.display = 'none';
        document.getElementById('di-sizes-list').innerHTML = '';
    }
    openModal('modal-dish');
}


// ── Size helpers ──
function toggleSizeMode() {
    const on = document.getElementById('di-multisize').checked;
    document.getElementById('di-price-single').style.display = on ? 'none' : '';
    document.getElementById('di-price-multi').style.display  = on ? '' : 'none';
    if (on && document.getElementById('di-sizes-list').children.length === 0) {
        addSizeRow(); addSizeRow();
    }
}

function addSizeRow(label = '', price = '') {
    const list = document.getElementById('di-sizes-list');
    const row = document.createElement('div');
    row.className = 'size-row';
    row.style.cssText = 'display:flex;gap:8px;align-items:center;';
    row.innerHTML = `
        <input class="size-label" type="text" placeholder="e.g. Half" value="${label}"
            style="flex:1;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--input-bg, rgba(255,255,255,0.06));color:white;font-size:0.84rem;outline:none;">
        <input class="size-price" type="text" placeholder="INR 180" value="${price}"
            style="flex:1;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--input-bg, rgba(255,255,255,0.06));color:white;font-size:0.84rem;outline:none;">
        <button type="button" onclick="this.parentElement.remove()"
            style="background:transparent;border:none;color:var(--muted);cursor:pointer;font-size:1rem;padding:4px;">✕</button>
    `;
    list.appendChild(row);
}

function saveDish() {
    const isMultiSize = document.getElementById('di-multisize').checked;
    let priceField = {};
    if (isMultiSize) {
        const rows = document.getElementById('di-sizes-list').querySelectorAll('.size-row');
        const sizes = [];
        rows.forEach(row => {
            const label = row.querySelector('.size-label').value.trim();
            const price = row.querySelector('.size-price').value.trim();
            if (label && price) sizes.push({ label, price });
        });
        if (sizes.length === 0) { toast('At least one size required', 'error'); return; }
        priceField = { sizes };
    } else {
        priceField = { price: document.getElementById('di-price').value.trim() };
    }
    const item = {
        name:        document.getElementById('di-name').value.trim(),
        ...priceField,
        category:    document.getElementById('di-category').value.trim(),
        description: document.getElementById('di-desc').value.trim(),
        ingredients: document.getElementById('di-ingredients').value.trim(),
        image:       document.getElementById('di-image').value.trim(),
        model:       document.getElementById('di-model').value.trim(),
        position:    document.getElementById('di-position').value.trim(),
        scale:       document.getElementById('di-scale').value.trim(),
        rotation:    document.getElementById('di-rotation').value.trim(),
        rotate_speed: parseInt(document.getElementById('di-rotatespeed').value) || 10000,
        veg:         document.getElementById('di-veg').value === 'true',
        auto_rotate: document.getElementById('di-autorotate').value === 'true',
        featured:    document.getElementById('di-featured').value === 'true',
    };
    if (!item.name) { toast('Dish name required', 'error'); return; }
    if (!currentEditData.items) currentEditData.items = [];
    if (currentEditItemIndex === -1) {
        currentEditData.items.push(item);
    } else {
        currentEditData.items[currentEditItemIndex] = item;
    }
    renderItemsList();
    closeModal('modal-dish');
    toast('Dish saved (Save Changes dabao to commit)', 'success');
}

function deleteItem(index) {
    if (!confirm('Ye dish delete karna hai?')) return;
    currentEditData.items.splice(index, 1);
    renderItemsList();
    toast('Dish removed (Save Changes dabao to commit)');
}

// ════════════════════════════════
// STAFF
// ════════════════════════════════
async function populateStaffRestSelect() {
    if (allRestaurants.length === 0) {
        const res = await fetch('/api/admin/overview');
        const d = await res.json();
        allRestaurants = d.restaurants;
    }
    const sel = document.getElementById('staff-rest-select');
    const current = sel.value;
    sel.innerHTML = '<option value="">-- Restaurant Select Karo --</option>';
    allRestaurants.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.client_id;
        opt.textContent = `${r.name} (${r.client_id})`;
        sel.appendChild(opt);
    });
    if (current) sel.value = current;
}

async function loadStaff() {
    const client_id = document.getElementById('staff-rest-select').value;
    const tbody = document.getElementById('staff-table-body');
    if (!client_id) { tbody.innerHTML = '<tr><td colspan="6" class="empty">Restaurant select karo</td></tr>'; return; }
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading...</td></tr>';
    const res = await fetch(`/api/admin/staff/${client_id}`);
    const staff = await res.json();
    if (staff.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">Koi staff nahi</td></tr>';
        return;
    }
    tbody.innerHTML = staff.map(s => `
        <tr>
            <td class="mono">${s.id}</td>
            <td>${s.name}</td>
            <td class="mono">${s.username}</td>
            <td><span class="badge badge-${s.role}">${s.role}</span></td>
            <td><span class="badge ${s.is_active ? 'badge-active' : 'badge-inactive'}">${s.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <div style="display:flex;gap:6px;">
                    <button class="btn btn-ghost btn-sm" onclick="openChangePassword(${s.id})">🔑</button>
                    <button class="btn btn-ghost btn-sm" onclick="toggleStaff(${s.id})">${s.is_active ? '🔴' : '🟢'}</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteStaff(${s.id}, '${s.name}')">Delete</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function openAddStaff() {
    const client_id = document.getElementById('staff-rest-select').value;
    if (!client_id) { toast('Pehle restaurant select karo', 'error'); return; }
    ['ns-name','ns-username','ns-password'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('ns-role').value = 'waiter';
    openModal('modal-add-staff');
}

async function createStaff() {
    const client_id = document.getElementById('staff-rest-select').value;
    const body = {
        name:     document.getElementById('ns-name').value.trim(),
        username: document.getElementById('ns-username').value.trim().toLowerCase(),
        password: document.getElementById('ns-password').value,
        role:     document.getElementById('ns-role').value,
    };
    if (!body.name || !body.username || !body.password) { toast('Sab fields required', 'error'); return; }
    const res = await fetch(`/api/admin/staff/${client_id}`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    const d = await res.json();
    if (res.ok) { toast(`'${body.name}' added!`, 'success'); closeModal('modal-add-staff'); loadStaff(); }
    else { toast(d.detail || 'Error', 'error'); }
}

function openChangePassword(staff_id) {
    currentPasswordStaffId = staff_id;
    document.getElementById('cp-password').value = '';
    openModal('modal-change-pass');
}

async function changePassword() {
    const password = document.getElementById('cp-password').value;
    if (!password) { toast('Password required', 'error'); return; }
    const res = await fetch(`/api/admin/staff/${currentPasswordStaffId}/password`, {
        method:'PATCH', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ new_password: password })
    });
    if (res.ok) { toast('Password updated!', 'success'); closeModal('modal-change-pass'); }
    else { toast('Failed', 'error'); }
}

async function toggleStaff(staff_id) {
    const res = await fetch(`/api/admin/staff/${staff_id}/toggle`, { method:'PATCH' });
    const d = await res.json();
    if (res.ok) { toast(d.is_active ? 'Staff activated' : 'Staff deactivated'); loadStaff(); }
    else { toast('Failed', 'error'); }
}

async function deleteStaff(staff_id, name) {
    if (!confirm(`'${name}' ko delete karna hai?`)) return;
    const res = await fetch(`/api/admin/staff/${staff_id}`, { method:'DELETE' });
    if (res.ok) { toast(`'${name}' deleted`); loadStaff(); }
    else { toast('Delete failed', 'error'); }
}

// ════════════════════════════════
// ADMIN MANAGEMENT
// ════════════════════════════════
function openAddAdmin() {
    ['na-name','na-username','na-password'].forEach(id => document.getElementById(id).value = '');
    openModal('modal-add-admin');
}

async function createAdmin() {
    const body = {
        name:     document.getElementById('na-name').value.trim(),
        username: document.getElementById('na-username').value.trim().toLowerCase(),
        password: document.getElementById('na-password').value,
    };
    if (!body.name || !body.username || !body.password) { toast('Sab fields required', 'error'); return; }
    const res = await fetch('/api/admin/create', {
        method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    const d = await res.json();
    if (res.ok) { toast(`Admin '${body.name}' add ho gaya!`, 'success'); closeModal('modal-add-admin'); }
    else { toast(d.detail || 'Error', 'error'); }
}

function openAdminPassword() {
    document.getElementById('ap-password').value = '';
    openModal('modal-admin-pass');
}

async function changeAdminPassword() {
    const password = document.getElementById('ap-password').value;
    if (!password) { toast('Password required', 'error'); return; }
    const res = await fetch('/api/admin/password', {
        method:'PATCH', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ new_password: password })
    });
    if (res.ok) { toast('Password update ho gaya!', 'success'); closeModal('modal-admin-pass'); }
    else { toast('Failed', 'error'); }
}

// ════════════════════════════════
// LOGOUT
// ════════════════════════════════
async function doLogout() {
    await fetch('/api/auth/logout', { method:'POST' });
    window.location.replace('/admin/login');
}

// ════════════════════════════════
// TOP DISHES FILTER
// ════════════════════════════════
let currentDishPeriod = 'alltime';
let currentDrillClientId = null;

function setDishPeriod(period, btn) {
    currentDishPeriod = period;
    document.querySelectorAll('#dish-period-pills .filter-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (currentDrillClientId) {
        loadRestaurantDishes(currentDrillClientId);
    } else {
        loadTopDishes(period);
    }
}

async function loadTopDishes(period='alltime') {
    const dishEl = document.getElementById('overall-dishes');
    dishEl.innerHTML = '<div class="loading">Loading...</div>';
    const res = await fetch(`/api/admin/overview?period=${period}`);
    const d = await res.json();
    renderTopDishes(d.top_dishes);
}

function renderTopDishes(dishes) {
    const dishEl = document.getElementById('overall-dishes');
    if (!dishes || dishes.length === 0) {
        dishEl.innerHTML = '<div class="empty">Abhi koi orders nahi</div>';
        return;
    }
    const maxQty = dishes[0].qty;
    dishEl.innerHTML = dishes.map((item, i) => `
        <div class="dish-row">
            <div class="dish-rank">#${i+1}</div>
            <div class="dish-name">${item.name}</div>
            <div class="dish-bar-wrap"><div class="dish-bar" style="width:${Math.round(item.qty/maxQty*100)}%"></div></div>
            <div class="dish-qty">${item.qty}x</div>
            <div class="dish-rev">₹${item.revenue.toLocaleString()}</div>
        </div>
    `).join('');
}

// ════════════════════════════════
// RESTAURANT DRILL-DOWN
// ════════════════════════════════
async function drillIntoRestaurant(clientId, name) {
    currentDrillClientId = clientId;

    // Row highlight
    document.querySelectorAll('.rest-row').forEach(r => r.classList.remove('row-selected'));
    const selectedRow = [...document.querySelectorAll('.rest-row')]
        .find(r => r.querySelector('.mono')?.textContent === clientId);
    if (selectedRow) selectedRow.classList.add('row-selected');

    // Top dishes panel title + back button
    document.getElementById('dishes-panel-title').textContent = `Top Dishes — ${name}`;
    document.getElementById('dishes-back-btn').style.display = 'block';
    loadRestaurantDishes(clientId);

    // Show detail section
    const detailSection = document.getElementById('rest-detail-section');
    const detailBody = document.getElementById('rest-detail-body');
    document.getElementById('rest-detail-title').textContent = `${name} — Details`;
    detailSection.style.display = 'block';
    detailBody.innerHTML = '<div class="loading">Loading...</div>';

    const res = await fetch(`/api/admin/restaurant/${clientId}/analytics`);
    const d = await res.json();
    const t = d.today;
    const a = d.alltime;

    const payHtml = (d.payment_breakdown || []).map(p =>
        `<span style="font-size:0.78rem;padding:3px 10px;border-radius:5px;background:rgba(255,255,255,0.05);border:1px solid var(--border)">${p.mode}: <b>₹${p.revenue.toLocaleString()}</b> (${p.count})</span>`
    ).join('') || '<span style="color:var(--muted);font-size:0.8rem">No data</span>';

    const src = t.source_breakdown || {};
    const srcHtml = Object.entries(src).map(([k, v]) =>
        `<span style="font-size:0.78rem;padding:3px 10px;border-radius:5px;background:rgba(255,255,255,0.05);border:1px solid var(--border)">${k}: <b>${v}</b></span>`
    ).join('') || '<span style="color:var(--muted);font-size:0.8rem">No data</span>';

    detailBody.innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px;">
            <div class="mini-stat">
                <div class="mini-stat-label">Today Orders</div>
                <div class="mini-stat-val">${t.orders}</div>
                ${t.orders_change_pct !== null ? `<div class="mini-stat-sub ${t.orders_change_pct >= 0 ? 'up' : 'down'}">${t.orders_change_pct >= 0 ? '▲' : '▼'} ${Math.abs(t.orders_change_pct)}% vs yesterday</div>` : ''}
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">Today Revenue</div>
                <div class="mini-stat-val">₹${t.revenue.toLocaleString()}</div>
                ${t.revenue_change_pct !== null ? `<div class="mini-stat-sub ${t.revenue_change_pct >= 0 ? 'up' : 'down'}">${t.revenue_change_pct >= 0 ? '▲' : '▼'} ${Math.abs(t.revenue_change_pct)}% vs yesterday</div>` : ''}
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">All-time Orders</div>
                <div class="mini-stat-val">${a.orders}</div>
                <div class="mini-stat-sub">${a.pending_now} pending now</div>
            </div>
            <div class="mini-stat">
                <div class="mini-stat-label">All-time Revenue</div>
                <div class="mini-stat-val">₹${a.revenue.toLocaleString()}</div>
                <div class="mini-stat-sub">${a.active_tables} active tables</div>
            </div>
        </div>
        <div style="display:flex;gap:18px;flex-wrap:wrap;">
            <div style="flex:1;min-width:180px;">
                <div style="font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">Payment Modes</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;">${payHtml}</div>
            </div>
            <div style="flex:1;min-width:180px;">
                <div style="font-size:0.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">Order Sources (Today)</div>
                <div style="display:flex;flex-wrap:wrap;gap:6px;">${srcHtml}</div>
            </div>
        </div>
    `;
}

async function loadRestaurantDishes(clientId) {
    const dishEl = document.getElementById('overall-dishes');
    dishEl.innerHTML = '<div class="loading">Loading...</div>';
    const res = await fetch(`/api/admin/restaurant/${clientId}/analytics`);
    const d = await res.json();
    renderTopDishes(d.top_items || []);
}

function clearRestaurantDrill() {
    currentDrillClientId = null;
    document.getElementById('dishes-panel-title').textContent = 'Top Dishes (Overall)';
    document.getElementById('dishes-back-btn').style.display = 'none';
    document.querySelectorAll('#dish-period-pills .filter-pill').forEach((b, i) => {
        b.classList.toggle('active', i === 0);
    });
    currentDishPeriod = 'alltime';
    document.getElementById('rest-detail-section').style.display = 'none';
    document.querySelectorAll('.rest-row').forEach(r => r.classList.remove('row-selected'));
    loadTopDishes('alltime');
}
// ── QR Generator (Admin — Branded) ──
async function downloadAllQRs(clientId) {
    const SCALE = 4; // high quality for print

    const res = await fetch(`/api/menu/${clientId}`);
    const data = await res.json();
    const rest = data.restaurant;
    const theme = data.theme;
    const numTables = rest.num_tables || 6;
    const primary   = theme.primary_color   || '#6C63FF';
    const secondary = theme.secondary_color || '#1a1a1a';

    // Logo load
    let logoImg = null;
    if (rest.logo) {
        logoImg = await new Promise(res => {
            const img = new Image();
            img.onload  = () => res(img);
            img.onerror = () => res(null);
            // Same-origin hai toh crossOrigin nahi chahiye
            img.src = rest.logo + '?v=' + Date.now();
        });
    }

    const zip = new JSZip();

    for (let n = 1; n <= numTables; n++) {
        const url = `${window.location.origin}/${clientId}/table/${n}/ar-menu`;

        const blob = await new Promise(resolve => {
            const wrap = document.createElement('div');
            wrap.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
            document.body.appendChild(wrap);

            const qrSize = 300;
            new QRCode(wrap, { text: url, width: qrSize, height: qrSize, correctLevel: QRCode.CorrectLevel.H });

            setTimeout(() => {
                const qrEl = wrap.querySelector('canvas') || wrap.querySelector('img');

                // Layout constants (pre-scale)
                const pad      = 28;
                const barH     = 8;
                const logoSize = logoImg ? 70 : 0;
                const logoGap  = logoImg ? logoSize + 14 : 0;
                const nameH    = 28;
                const tableH   = 36;
                const gap      = 10;
                const totalH   = barH + pad + logoGap + nameH + gap + tableH + gap + qrSize + pad + barH;
                const totalW   = qrSize + pad * 2;

                const canvas = document.createElement('canvas');
                canvas.width  = totalW * SCALE;
                canvas.height = totalH * SCALE;
                const ctx = canvas.getContext('2d');
                ctx.scale(SCALE, SCALE);

                // White bg
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, totalW, totalH);

                // Top bar
                ctx.fillStyle = primary;
                ctx.fillRect(0, 0, totalW, barH);

                let y = barH + pad;

                // Logo — circular clip
                if (logoImg) {
                    const lx = (totalW - logoSize) / 2;
                    const ly = y;
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(lx + logoSize/2, ly + logoSize/2, logoSize/2, 0, Math.PI*2);
                    ctx.closePath();
                    ctx.clip();
                    ctx.drawImage(logoImg, lx, ly, logoSize, logoSize);
                    ctx.restore();
                    y += logoSize + 14;
                }

                // Restaurant name
                ctx.fillStyle = secondary;
                ctx.font = `600 15px Arial`;
                ctx.textAlign = 'center';
                ctx.fillText(rest.name, totalW / 2, y + 20);
                y += nameH + gap;

                // Table number
                ctx.fillStyle = primary;
                ctx.font = `bold 24px Arial`;
                ctx.fillText(`Table ${n}`, totalW / 2, y + 28);
                y += tableH + gap;

                // QR
                const drawQR = (src) => {
                    const img = new Image();
                    img.onload = () => {
                        ctx.drawImage(img, pad, y, qrSize, qrSize);

                        // ZenTable logo QR center mein
                        const ztR      = qrSize * 0.07;
                        const ztCx     = pad + qrSize / 2;
                        const ztCy     = y + qrSize / 2;

                        // White circle bg
                        ctx.fillStyle = '#F5F0E8';
                        ctx.beginPath();
                        ctx.arc(ztCx, ztCy, ztR + 5, 0, Math.PI * 2);
                        ctx.fill();

                        const finalize = () => {
                            y += qrSize + pad;
                            // Bottom bar
                            ctx.fillStyle = primary;
                            ctx.fillRect(0, totalH - barH, totalW, barH);
                            canvas.toBlob(blob => {
                                document.body.removeChild(wrap);
                                resolve(blob);
                            }, 'image/png');
                        };

                        const ztLogo = new Image();
                        ztLogo.onload = () => {
                            const iw = ztLogo.naturalWidth;
                            const ih = ztLogo.naturalHeight;
                            const aspect = iw / ih;
                            const diam = ztR * 2;
                            let dw = aspect > 1 ? diam : diam * aspect;
                            let dh = aspect > 1 ? diam / aspect : diam;
                            ctx.drawImage(ztLogo, ztCx - dw/2, ztCy - dh/2 + 3, dw, dh);
                            finalize();
                        };
                        ztLogo.onerror = finalize;
                        ztLogo.src = '/static/assets/zentable/logo_golden_192.png';
                    };
                    img.src = src;
                };

                if (qrEl.tagName === 'CANVAS') drawQR(qrEl.toDataURL());
                else drawQR(qrEl.src);
            }, 150);
        });

        zip.file(`${clientId}_table_${n}.png`, blob);
        await new Promise(r => setTimeout(r, 100));
    }

    // Generate zip aur download
    const zipBlob = await zip.generateAsync({ type: 'blob' });
    const link = document.createElement('a');
    link.download = `${clientId}_qr_codes.zip`;
    link.href = URL.createObjectURL(zipBlob);
    link.click();
    URL.revokeObjectURL(link.href);
}
