// clientId — HTML template mein inject hota hai

// Read CSS vars after render
function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

Chart.defaults.font.family = cssVar('--font-secondary') || 'sans-serif';
Chart.defaults.color = '#999';

const charts = {};
let analyticsData = null;

// Date label
const now = new Date();
document.getElementById('today-label').textContent =
    now.toLocaleDateString('en-IN', { weekday:'long', day:'numeric', month:'long', year:'numeric' });

// ── TABS ──
function switchTab(tab, btn) {
    ['overview','analytics','orders','tables','staff'].forEach(t => {
        document.getElementById(`tab-${t}`).style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (tab === 'overview')  { loadAll(); }
    if (tab === 'analytics') { if (!analyticsData) loadAll(); else renderAnalyticsTab(); }
    if (tab === 'orders')    loadOrders();
    if (tab === 'tables')    loadTables();
    if (tab === 'staff')     loadStaff();
}

// ── LOAD ALL ──
async function loadAll() {
    if (!HAS_ANALYTICS) {
        showAnalyticsLocked();
        return;
    }
    try {
        const res = await fetch(`/api/admin/analytics/${clientId}`);
        if (!res.ok) throw new Error();
        analyticsData = await res.json();
        renderOverviewTab();
        renderAnalyticsTab();
    } catch(e) {
        toast('❌ Failed to load data');
    }
}

function showAnalyticsLocked() {
    const msg = `<div style="text-align:center;padding:40px 20px;">
        <div style="font-size:2.5rem;margin-bottom:14px;">📊</div>
        <div style="font-size:1rem;font-weight:700;color:#333;margin-bottom:8px;">Analytics Unavailable</div>
        <div style="font-size:0.85rem;color:#999;line-height:1.6;">Analytics feature is not enabled for this restaurant. Contact support to upgrade.</div>
    </div>`;
    const ov = document.getElementById('tab-overview');
    const an = document.getElementById('tab-analytics');
    if (ov) ov.innerHTML = msg;
    if (an) an.innerHTML = msg;
}

function fmt(n) {
    n = n || 0;
    if (n >= 100000) return '₹' + (n/100000).toFixed(1) + 'L';
    if (n >= 1000)   return '₹' + (n/1000).toFixed(1) + 'K';
    return '₹' + n;
}

function changeHtml(pct) {
    if (pct === null || pct === undefined) return '';
    const arrow = pct > 0 ? '▲' : pct < 0 ? '▼' : '→';
    const cls   = pct > 0 ? 'up' : pct < 0 ? 'down' : 'flat';
    return `<span class="${cls}">${arrow} ${Math.abs(pct)}% vs yesterday</span>`;
}

// ── OVERVIEW TAB ──
function renderOverviewTab() {
    const d = analyticsData;
    const t = d.today;
    const a = d.alltime;

    document.getElementById('s-today-orders').textContent = t.orders;
    document.getElementById('s-today-rev').textContent    = fmt(t.revenue);
    document.getElementById('s-today-avg').textContent    = fmt(t.avg_order_value);
    document.getElementById('s-pending').textContent      = a.pending_now;
    document.getElementById('s-today-orders-chg').innerHTML = changeHtml(t.orders_change_pct);
    document.getElementById('s-today-rev-chg').innerHTML    = changeHtml(t.revenue_change_pct);
    document.getElementById('s-alltime-orders').textContent = a.orders;
    document.getElementById('s-alltime-rev').textContent    = fmt(a.revenue);

    // Source split
    const cust   = t.source_breakdown?.customer || 0;
    const waiter = t.source_breakdown?.waiter   || 0;
    const total  = (cust + waiter) || 1;
    const cpct   = Math.round(cust / total * 100);
    document.getElementById('split-c').style.width = cpct + '%';
    document.getElementById('split-w').style.width = (100 - cpct) + '%';
    document.getElementById('split-c-lbl').textContent = `Customer: ${cust}`;
    document.getElementById('split-w-lbl').textContent = `Waiter: ${waiter}`;

    // Hourly bar chart
    const hours   = d.hourly_today.map(h => h.hour + ':00');
    const hOrders = d.hourly_today.map(h => h.orders);
    renderBarChart('chart-hourly', hours, hOrders, 'Orders', cssVar('--primary'));
}

// ── ANALYTICS TAB ──
function renderAnalyticsTab() {
    if (!analyticsData) return;
    const d = analyticsData;
    const PRIMARY   = cssVar('--primary');
    const SECONDARY = cssVar('--secondary');

    // Daily revenue line
    const days    = d.daily_last7.map(x => x.label);
    const dayRevs = d.daily_last7.map(x => x.revenue);
    const dayOrds = d.daily_last7.map(x => x.orders);
    renderLineChart('chart-daily-rev',    days, dayRevs, 'Revenue (₹)', PRIMARY);
    renderBarChart ('chart-daily-orders', days, dayOrds, 'Orders',       SECONDARY, 150);

    // Top items
    const items  = d.top_items || [];
    const maxQty = items[0]?.qty || 1;
    const rankCls = ['gold','silver','bronze'];
    document.getElementById('top-items-list').innerHTML = items.length
        ? items.map((it, i) => `
            <div class="item-row">
                <div class="item-rank ${rankCls[i]||''}">${i+1}</div>
                <div class="item-name">${it.name}</div>
                <div class="bar-wrap"><div class="bar-fill" style="width:${Math.round(it.qty/maxQty*100)}%"></div></div>
                <div class="item-qty">${it.qty}×</div>
                <div class="item-rev">${fmt(it.revenue)}</div>
            </div>`).join('')
        : '<div class="empty-state"><i class="fas fa-chart-bar"></i><p>No orders yet</p></div>';

    // Payment breakdown
    const payIcons = { cash:'💵', upi:'📱', card:'💳' };
    const payMap = {};
    (d.payment_breakdown||[]).forEach(p => payMap[p.mode] = p);
    document.getElementById('pay-grid').innerHTML = ['cash','upi','card'].map(m => {
        const p = payMap[m] || { count:0, revenue:0 };
        return `<div class="pay-card">
            <div class="pay-icon">${payIcons[m]}</div>
            <div class="pay-val">${fmt(p.revenue)}</div>
            <div class="pay-label">${m}</div>
            <div class="pay-cnt">${p.count} bill${p.count!==1?'s':''}</div>
        </div>`;
    }).join('');
}

// ── CHART HELPERS ──
function renderBarChart(id, labels, data, label, color, height=160) {
    if (charts[id]) charts[id].destroy();
    const ctx = document.getElementById(id);
    if (!ctx) return;
    charts[id] = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label, data, backgroundColor: color + 'bb', borderRadius:6, borderSkipped:false }] },
        options: {
            responsive:true, maintainAspectRatio:false,
            plugins:{ legend:{ display:false } },
            scales: {
                x:{ grid:{ display:false }, ticks:{ font:{ size:10 } } },
                y:{ grid:{ color:'#f0f0f0' }, ticks:{ font:{ size:10 }, precision:0 } }
            }
        }
    });
}

function renderLineChart(id, labels, data, label, color) {
    if (charts[id]) charts[id].destroy();
    const ctx = document.getElementById(id);
    if (!ctx) return;
    charts[id] = new Chart(ctx, {
        type:'line',
        data:{ labels, datasets:[{
            label, data,
            borderColor:color, backgroundColor:color+'25',
            fill:true, tension:0.4, pointBackgroundColor:color,
            pointRadius:4, borderWidth:2
        }]},
        options:{
            responsive:true, maintainAspectRatio:false,
            plugins:{ legend:{ display:false } },
            scales:{
                x:{ grid:{ display:false }, ticks:{ font:{ size:10 } } },
                y:{ grid:{ color:'#f0f0f0' }, ticks:{ font:{ size:10 }, callback: v => '₹'+v } }
            }
        }
    });
}

// ── ORDERS ──
async function loadOrders() {
    const status  = (document.getElementById('f-status')  || {value:''}).value;
    const source  = (document.getElementById('f-source')  || {value:''}).value;
    const time    = (document.getElementById('f-time')    || {value:''}).value;

    let url = `/api/orders/${clientId}/filter?`;

    // "kitchen" = pending + preparing — dono fetch karke merge
    if (status === 'kitchen') {
        url += `status=pending&`;
    } else if (status === 'paid') {
        // paid = done orders jinke table paid hain — all done for now
        url += `status=done&`;
    } else if (status) {
        url += `status=${status}&`;
    }
    if (source === 'waiter') {
        // waiter filter — 'waiter' (purane orders) aur 'Staff' (naye orders) dono
        url += `source=waiter&`;
        window._fetchStaffAlso = true;
    } else if (source) {
        url += `source=${source}&`;
        window._fetchStaffAlso = false;
    } else {
        window._fetchStaffAlso = false;
    }

    // Time filter — local date
    if (time) {
        const now = new Date();
        const pad = n => String(n).padStart(2,'0');
        const todayStr = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}`;
        let fromDate = '';
        if (time === 'today') fromDate = todayStr;
        else if (time === 'week') {
            const d = new Date(now); d.setDate(d.getDate() - d.getDay());
            fromDate = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
        } else if (time === 'month') fromDate = `${now.getFullYear()}-${pad(now.getMonth()+1)}-01`;
        else if (time === 'year')  fromDate = `${now.getFullYear()}-01-01`;
        if (fromDate) url += `from_date=${fromDate}&`;
    }

    let [ordersRes, summaryRes] = await Promise.all([
        fetch(url), fetch(`/api/tables/${clientId}/summary`)
    ]);
    let orders = await ordersRes.json();
    // Staff filter — merge 'waiter' + 'Staff' source orders
    if (window._fetchStaffAlso) {
        const staffUrl = url.replace('source=waiter&', 'source=Staff&');
        const staffRes = await fetch(staffUrl);
        const staffOrders = await staffRes.json();
        orders = [...orders, ...staffOrders].sort((a,b) => b.id - a.id);
    }
    const summary = await summaryRes.json();
    const tMap = {};
    summary.forEach(t => tMap[String(t.table_no)] = t);

    const list = document.getElementById('orders-list');
    if (!orders.length) {
        list.innerHTML = '<div class="empty-state"><i class="fas fa-receipt"></i><p>No orders found</p></div>';
        return;
    }
    list.innerHTML = orders.map(o => {
        const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
        const itemsText = items.map(i => `${i.name} ×${i.qty}`).join(', ');
        const tInfo = tMap[String(o.table_no)] || {};
        const payBadge = tInfo.payment_status === 'paid'
            ? `<span class="badge pay-paid">PAID</span>`
            : tInfo.payment_status === 'unpaid'
            ? `<span class="badge pay-billed">BILLED</span>` : '';
        return `<div class="order-card ${o.status}">
            <div class="order-top">
                <div class="badges">
                    <span class="badge status-${o.status}">${o.status}</span>
                    <span class="badge src-${o.source}">${o.source}</span>
                    ${payBadge}
                </div>
                <div class="order-meta">T${o.table_no} · #${o.id}<br>${(o.created_at||'').substring(0,16)}</div>
            </div>
            <div class="order-items-text">${itemsText}</div>
            <div class="order-foot"><div class="order-total">₹${o.total}</div></div>
        </div>`;
    }).join('');
}

// ── TABLES ──
async function loadTables() {
    const res = await fetch(`/api/tables/${clientId}/summary`);
    const tables = await res.json();
    const map = {};
    tables.forEach(t => map[t.table_no] = t);

    // f-table removed

    const maxTable = tables.length ? Math.max(...tables.map(t => t.table_no)) : 0;
    const count = numTables;
    const labels = { inactive:'Inactive', active:'Active', occupied:'Occupied',
                     ready:'Ready', done:'Done', billed:'Billed', paid:'Paid' };

    document.getElementById('tables-grid').innerHTML = Array.from({length:count}, (_, i) => {
        const n = i + 1;
        const t = map[n];
        const ds = t ? t.display_status : 'inactive';
        return `<div class="table-box ${ds}">
            <div class="table-num">T${n}</div>
            <div class="table-status">${labels[ds]||ds}</div>
            <div class="table-orders">${t ? t.order_count+' orders' : ''}</div>
            <button class="qr-btn" onclick="downloadTableQR(${n})">⬇ QR</button>
        </div>`;
    }).join('');
}

function downloadTableQR(tableNo) {
    const SCALE  = 4;
    const qrSize = 280;
    const pad    = 32;
    const textH  = 60;

    const url = `${window.location.origin}/${clientId}/table/${tableNo}/ar-menu`;

    const wrap = document.createElement('div');
    wrap.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
    document.body.appendChild(wrap);
    new QRCode(wrap, { text: url, width: qrSize, height: qrSize, correctLevel: QRCode.CorrectLevel.H });

    setTimeout(() => {
        const qrEl = wrap.querySelector('canvas') || wrap.querySelector('img');

        const W = qrSize + pad * 2;
        const H = textH + qrSize + pad * 2;

        const canvas = document.createElement('canvas');
        canvas.width  = W * SCALE;
        canvas.height = H * SCALE;
        const ctx = canvas.getContext('2d');
        ctx.scale(SCALE, SCALE);

        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, W, H);

        ctx.fillStyle = '#1a1a1a';
        ctx.font = 'bold 28px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Table ' + tableNo, W / 2, pad + textH / 2);

        const drawQR = (src) => {
            const qrImg = new Image();
            qrImg.onload = () => {
                ctx.drawImage(qrImg, pad, pad + textH, qrSize, qrSize);

                const circleR = qrSize * 0.06;  // circle radius
                const cx = pad + qrSize / 2;
                const cy = pad + textH + qrSize / 2;

                // White circle background
                ctx.fillStyle = '#ffffff';
                ctx.beginPath();
                ctx.arc(cx, cy, circleR + 5, 0, Math.PI * 2);
                ctx.fill();

                // Logo — aspect ratio maintain karte hue circle mein fit karo
                const logoImg = new Image();
                logoImg.onload = () => {
                    const iw = logoImg.naturalWidth;
                    const ih = logoImg.naturalHeight;
                    const aspect = iw / ih;

                    // contain fit — dono dimensions circle diameter se chhoti rahein
                    const diameter = circleR * 2;
                    let dw, dh;
                    if (aspect > 1) {
                        dw = diameter;
                        dh = diameter / aspect;
                    } else {
                        dh = diameter;
                        dw = diameter * aspect;
                    }

                    const dx = cx - dw / 2;
                    const dy = cy - dh / 2 + 3;

                    ctx.drawImage(logoImg, dx, dy, dw, dh);

                    const link = document.createElement('a');
                    link.download = 'table_' + tableNo + '_qr.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                    document.body.removeChild(wrap);
                };
                logoImg.onerror = () => {
                    const link = document.createElement('a');
                    link.download = 'table_' + tableNo + '_qr.png';
                    link.href = canvas.toDataURL('image/png');
                    link.click();
                    document.body.removeChild(wrap);
                };
                logoImg.src = '/static/assets/zentable/logo_golden_192.png';
            };
            qrImg.src = src;
        };

        if (qrEl.tagName === 'CANVAS') drawQR(qrEl.toDataURL());
        else drawQR(qrEl.src);
    }, 100);
}

function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// Init
loadAll();
setInterval(loadAll, 60000);


// ════════════════════════════════
// STAFF MANAGEMENT
// ════════════════════════════════
let editingStaffId = null;
let changingPasswordId = null;

async function loadStaff() {
    const res = await fetch(`/api/staff/${clientId}`);
    const staff = await res.json();
    const el = document.getElementById('staff-list');

    if (!staff.length) {
        el.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><p>Koi staff nahi — Add karo!</p></div>';
        return;
    }

    const filtered = staff.filter(s => s.id !== currentStaffId);
    if (!filtered.length) {
        el.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><p>Koi staff nahi — Add karo!</p></div>';
        return;
    }
    el.innerHTML = filtered.map(s => `
        <div class="staff-card ${s.is_active ? '' : 'staff-inactive'}">
            <div class="staff-card-top">
                <div>
                    <div class="staff-name">
                        <span class="active-dot ${s.is_active ? 'dot-active' : 'dot-inactive'}"></span>
                        ${s.name}
                    </div>
                    <div class="staff-username">@${s.username}</div>
                </div>
                <span class="staff-role-badge staff-role-${s.role}">${s.role}</span>
            </div>
            <div class="staff-actions">
                <button class="staff-btn staff-btn-pass" onclick="openChangePassword(${s.id})">🔑 Password</button>
                <button class="staff-btn ${s.is_active ? 'staff-btn-toggle-on' : 'staff-btn-toggle-off'}" 
                        onclick="toggleStaff(${s.id}, ${s.is_active})">
                    ${s.is_active ? '🔴 Deactivate' : '🟢 Activate'}
                </button>
                <button class="staff-btn staff-btn-delete" onclick="deleteStaff(${s.id}, '${s.name}')">🗑 Delete</button>
            </div>
        </div>
    `).join('');
}

function openAddStaff() {
    editingStaffId = null;
    document.getElementById('staff-modal-title').textContent = 'Staff Add Karo';
    document.getElementById('sm-save-btn').textContent = 'Add Staff';
    document.getElementById('sm-name').value = '';
    document.getElementById('sm-username').value = '';
    document.getElementById('sm-password').value = '';
    document.getElementById('sm-role').value = 'waiter';
    document.getElementById('sm-username').disabled = false;
    document.getElementById('sm-password-group').style.display = 'block';
    document.getElementById('staff-modal').style.display = 'flex';
}

function closeStaffModal() {
    document.getElementById('staff-modal').style.display = 'none';
}

async function saveStaff() {
    const name     = document.getElementById('sm-name').value.trim();
    const username = document.getElementById('sm-username').value.trim().toLowerCase();
    const password = document.getElementById('sm-password').value;
    const role     = document.getElementById('sm-role').value;

    if (!name || !username || !password) { toast('❌ Sab fields required hain'); return; }

    const res = await fetch(`/api/staff/${clientId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, username, password, role })
    });
    const d = await res.json();
    if (res.ok) {
        toast('✅ Staff add ho gaya!');
        closeStaffModal();
        loadStaff();
    } else {
        toast('❌ ' + (d.detail || 'Error'));
    }
}

function openChangePassword(staff_id) {
    changingPasswordId = staff_id;
    document.getElementById('pm-password').value = '';
    document.getElementById('pass-modal').style.display = 'flex';
}

function closePassModal() {
    document.getElementById('pass-modal').style.display = 'none';
}

async function changePassword() {
    const password = document.getElementById('pm-password').value;
    if (!password) { toast('❌ Password required'); return; }
    const res = await fetch(`/api/staff/${changingPasswordId}/password`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: password })
    });
    if (res.ok) { toast('✅ Password update ho gaya!'); closePassModal(); }
    else { toast('❌ Failed'); }
}

async function toggleStaff(staff_id, currentlyActive) {
    const res = await fetch(`/api/staff/${staff_id}/toggle`, { method: 'PATCH' });
    const d = await res.json();
    if (res.ok) {
        toast(d.is_active ? '✅ Staff activated' : '🔴 Staff deactivated');
        loadStaff();
    } else { toast('❌ Failed'); }
}

async function deleteStaff(staff_id, name) {
    if (!confirm(`'${name}' ko permanently delete karna hai?`)) return;
    const res = await fetch(`/api/staff/${staff_id}`, { method: 'DELETE' });
    if (res.ok) { toast('🗑 Staff deleted'); loadStaff(); }
    else { toast('❌ Failed'); }
}

function toggleSmPass() {
    const inp = document.getElementById('sm-password');
    const btn = document.getElementById('sm-eye');
    inp.type = inp.type === 'password' ? 'text' : 'password';
    btn.textContent = inp.type === 'password' ? '👁' : '🙈';
}

function togglePmPass() {
    const inp = document.getElementById('pm-password');
    const btn = document.getElementById('pm-eye');
    inp.type = inp.type === 'password' ? 'text' : 'password';
    btn.textContent = inp.type === 'password' ? '👁' : '🙈';
}
