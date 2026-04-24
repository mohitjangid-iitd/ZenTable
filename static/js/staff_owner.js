// clientId — HTML template mein inject hota hai

// Read CSS vars after render
function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

Chart.defaults.font.family = cssVar('--font-secondary') || 'sans-serif';
Chart.defaults.color = '#999';

const charts = {};
let analyticsData = null;

// ── BRANCHES STATE ──
let allBranches = [];         // [{id, name}] — loaded on init
let isMultiBranch = false;    // true if >1 branch exists
let staffCache = [];          // full staff list for client-side filtering

// Date label
const now = new Date();
document.getElementById('today-label').textContent =
    now.toLocaleDateString('en-IN', { weekday:'long', day:'numeric', month:'long', year:'numeric' });

// ── TABS ──
function switchTab(tab, btn) {
    ['analytics','orders','tables','staff','manage'].forEach(t => {
        document.getElementById(`tab-${t}`).style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (tab === 'overview')  { loadAll(); }
    if (tab === 'analytics') { if (!analyticsData) loadAll(); else renderAnalyticsTab(); }
    if (tab === 'orders')    loadOrders();
    if (tab === 'tables')    { loadTables(); if (!ownerRestData) loadOwnerRestData(); }
    if (tab === 'staff')     loadStaff();
    if (tab === 'manage')    initManageTab();
}

// ── LOAD ALL ──
async function loadAll() {
    if (!HAS_ANALYTICS) {
        showAnalyticsLocked();
        return;
    }
    try {
        const branch = getTabBranch('analytics');
        const bParam = branch ? `?branch_id=${branch}` : '';
        const res = await fetch(`/api/admin/analytics/${clientId}${bParam}`);
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

    const selectedBranch = getTabBranch('orders');
    let url = selectedBranch
        ? `/api/orders/${clientId}/filter?branch_id=${selectedBranch}&`
        : `/api/orders/${clientId}/filter?`;

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

    const summaryBranch = selectedBranch || branchId;
    let [ordersRes, summaryRes] = await Promise.all([
        fetch(url), fetch(`/api/tables/${clientId}/summary?branch_id=${summaryBranch}`)
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
        const branchBadge = (isMultiBranch && !selectedBranch && o.branch_id)
            ? `<span class="badge" style="background:#f0f4ff;color:#3b5bdb;font-size:0.6rem;">${branchLabel(o.branch_id)}</span>`
            : '';
        return `<div class="order-card ${o.status}">
            <div class="order-top">
                <div class="badges">
                    <span class="badge status-${o.status}">${o.status}</span>
                    <span class="badge src-${o.source}">${o.source}</span>
                    ${payBadge}
                    ${branchBadge}
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
    // Tables mein always ek specific branch — "All" nahi hota
    const selectedBranch = getTabBranch('tables')
        || (allBranches[0] && (allBranches[0].branch_id || allBranches[0].id))
        || branchId;
    const res = await fetch(`/api/tables/${clientId}/summary?branch_id=${selectedBranch}`);
    const tables = await res.json();
    const map = {};
    tables.forEach(t => map[t.table_no] = t);

    // Selected branch ka num_tables — BRANCHES config se nikalo
    const branchObj = allBranches.find(b => (b.branch_id || b.id) === selectedBranch);
    const branchCfg = branchObj ? getBranchConfig(branchObj) : null;
    const configCount = branchCfg?.restaurant?.num_tables || branchCfg?.num_tables;
    // Fallback: API ne kitni tables return ki unka max table_no
    const apiMaxTable = tables.length ? Math.max(...tables.map(t => t.table_no)) : 0;
    const count = configCount || apiMaxTable || parseInt(document.getElementById('oi-num-tables')?.value) || numTables;

    // oi-num-tables input bhi update karo — branch change reflect ho
    const numInput = document.getElementById('oi-num-tables');
    if (numInput) numInput.value = count;

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
    _renderTableQRBlob(tableNo).then(blob => {
        const link = document.createElement('a');
        link.download = 'table_' + tableNo + '_qr.png';
        link.href = URL.createObjectURL(blob);
        link.click();
        URL.revokeObjectURL(link.href);
    });
}

// ── Activate / Close All ──
async function activateAll() {
    const effectiveBranch = getTabBranch('tables')
        || (allBranches[0] && (allBranches[0].branch_id || allBranches[0].id))
        || branchId;
    const res = await fetch(`/api/table/${clientId}/activate-all?branch_id=${effectiveBranch}`, { method: 'POST' });
    if (res.ok) { toast('✅ Saari tables activate ho gayi!'); loadTables(); }
    else toast('❌ Failed');
}

async function closeAll() {
    if (!confirm('Saari tables close karna chahte ho?')) return;
    const effectiveBranch = getTabBranch('tables')
        || (allBranches[0] && (allBranches[0].branch_id || allBranches[0].id))
        || branchId;
    const res = await fetch(`/api/table/${clientId}/close-all?branch_id=${effectiveBranch}`, { method: 'POST' });
    if (res.ok) { toast('✅ Saari tables band ho gayi'); loadTables(); }
    else toast('❌ Failed');
}

// ── Download All QR (ZIP) ──
async function downloadAllQRs() {
    const count = parseInt(document.getElementById('oi-num-tables')?.value) || numTables;
    const btn = document.getElementById('dl-all-qr-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...'; }

    try {
        const zip = new JSZip();
        for (let n = 1; n <= count; n++) {
            const blob = await _renderTableQRBlob(n);
            zip.file(`table_${n}_qr.png`, blob);
            await new Promise(r => setTimeout(r, 100));
        }
        const zipBlob = await zip.generateAsync({ type: 'blob' });
        const link = document.createElement('a');
        link.download = `${clientId}_qr_codes.zip`;
        link.href = URL.createObjectURL(zipBlob);
        link.click();
        URL.revokeObjectURL(link.href);
        toast('✅ All QR downloaded!');
    } catch(e) {
        toast('❌ Download failed');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-download"></i> All QR (ZIP)'; }
    }
}

// ── Single QR → Blob (shared by single + bulk download) ──
function _renderTableQRBlob(tableNo) {
    return new Promise(resolve => {
        const SCALE  = 4;
        const qrSize = 280;
        const pad    = 32;
        const textH  = 60;
        const W = qrSize + pad * 2;
        const H = textH + qrSize + pad * 2;

        const url = `${window.location.origin}/${clientId}/table/${tableNo}/ar-menu`;

        const wrap = document.createElement('div');
        wrap.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
        document.body.appendChild(wrap);
        new QRCode(wrap, { text: url, width: qrSize, height: qrSize, correctLevel: QRCode.CorrectLevel.H });

        setTimeout(() => {
            const qrEl = wrap.querySelector('canvas') || wrap.querySelector('img');

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

                    const circleR = qrSize * 0.06;
                    const cx = pad + qrSize / 2;
                    const cy = pad + textH + qrSize / 2;

                    ctx.fillStyle = '#ffffff';
                    ctx.beginPath();
                    ctx.arc(cx, cy, circleR + 5, 0, Math.PI * 2);
                    ctx.fill();

                    const logoImg = new Image();
                    const finish = () => {
                        canvas.toBlob(blob => {
                            document.body.removeChild(wrap);
                            resolve(blob);
                        }, 'image/png');
                    };
                    logoImg.onload = () => {
                        const iw = logoImg.naturalWidth, ih = logoImg.naturalHeight;
                        const aspect = iw / ih;
                        const diameter = circleR * 2;
                        const dw = aspect > 1 ? diameter : diameter * aspect;
                        const dh = aspect > 1 ? diameter / aspect : diameter;
                        ctx.drawImage(logoImg, cx - dw/2, cy - dh/2 + 3, dw, dh);
                        finish();
                    };
                    logoImg.onerror = finish;
                    logoImg.src = '/static/assets/zentable/logo_golden_192.png';
                };
                qrImg.src = src;
            };

            if (qrEl.tagName === 'CANVAS') drawQR(qrEl.toDataURL());
            else drawQR(qrEl.src);
        }, 100);
    });
}

function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// ════════════════════════════════
// BRANCH MANAGEMENT (multi-branch)
// ════════════════════════════════

function loadBranchesInit() {
    allBranches = (typeof BRANCHES !== 'undefined') ? BRANCHES : [];
    isMultiBranch = allBranches.length > 1;
    if (isMultiBranch) {
        populateAllBranchDropdowns();
        showBranchUI();
    }
}
// config already parsed object hai ya string — dono handle karo
function getBranchConfig(b) {
    if (!b.config) return {};
    if (typeof b.config === 'object') return b.config;
    try { return JSON.parse(b.config); } catch(e) { return {}; }
}

function getBranchName(b) {
    const bid = b.branch_id || b.id || '';
    if (bid === '__default__') return 'Main';
    const cfg = getBranchConfig(b);
    return cfg?.restaurant?.name || bid.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase());
}

function populateAllBranchDropdowns() {
    // Tables + Manage — NO "All Branches", first branch auto-selected
    // FIX: getElementById sirf 1 arg leta hai — dono ko alag handle karo
    ['f-tables-branch', 'f-manage-branch'].forEach(selId => {
        const sel = document.getElementById(selId);
        if (!sel) return;
        sel.innerHTML = '';
        allBranches.forEach((b, i) => {
            const opt = document.createElement('option');
            opt.value = b.branch_id || b.id || '';
            opt.textContent = getBranchName(b);
            if (i === 0) opt.selected = true;
            sel.appendChild(opt);
        });
    });

    // Baaki — "All Branches" option ke saath
    const otherIds = ['f-analytics-branch','f-orders-branch','f-staff-branch','sm-branch'];
    otherIds.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const firstOpt = el.options[0];
        el.innerHTML = '';
        el.appendChild(firstOpt);
        allBranches.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.branch_id || b.id || '';
            opt.textContent = getBranchName(b);
            el.appendChild(opt);
        });
    });
}

function showBranchUI() {
    ['analytics-branch-bar','tables-branch-bar','manage-branch-bar'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = '';
    });
    const fOB = document.getElementById('f-orders-branch');
    if (fOB) fOB.style.display = '';
    const fSB = document.getElementById('f-staff-branch');
    if (fSB) fSB.style.display = '';
    const smBG = document.getElementById('sm-branch-group');
    if (smBG) smBG.style.display = '';
}

// Active branch per tab (helper)
function getTabBranch(tabName) {
    const el = document.getElementById(`f-${tabName}-branch`);
    return (el && el.value) ? el.value : null;
}

// Init
loadBranchesInit();
loadAll();
setInterval(loadAll, 60000);


// ── BRANCH LABEL HELPER ──
function branchLabel(bid) {
    if (!bid || bid === '__default__') return 'Main';
    const b = allBranches.find(x => (x.branch_id || x.id) === bid);
    if (!b) return bid.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase());
    const cfg = getBranchConfig(b);
    return cfg?.restaurant?.name || bid.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ════════════════════════════════
// STAFF MANAGEMENT
// ════════════════════════════════
let editingStaffId = null;
let changingPasswordId = null;

async function loadStaff() {
    const res = await fetch(`/api/staff/${clientId}`);
    staffCache = await res.json();
    renderStaffFiltered();
}

function renderStaffFiltered() {
    const branchFilter = (document.getElementById('f-staff-branch') || {value:''}).value;
    const roleFilter   = (document.getElementById('f-staff-role')   || {value:''}).value;
    const el = document.getElementById('staff-list');

    let filtered = staffCache.filter(s => s.id !== currentStaffId);
    if (branchFilter) filtered = filtered.filter(s => s.branch_id === branchFilter);
    if (roleFilter)   filtered = filtered.filter(s => s.role === roleFilter);

    if (!filtered.length) {
        el.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i><p>Koi staff nahi — Add karo!</p></div>';
        return;
    }
    el.innerHTML = filtered.map(s => {
        const branchBadge = isMultiBranch
            ? `<span class="staff-role-badge" style="background:#f0f4ff;color:#3b5bdb;font-size:0.6rem;margin-left:5px;">${branchLabel(s.branch_id)}</span>`
            : '';
        return `
        <div class="staff-card ${s.is_active ? '' : 'staff-inactive'}">
            <div class="staff-card-top">
                <div>
                    <div class="staff-name">
                        <span class="active-dot ${s.is_active ? 'dot-active' : 'dot-inactive'}"></span>
                        ${s.name}
                        ${branchBadge}
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
        </div>`;
    }).join('');
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
    // Pre-select current branch filter if any
    const smBranch = document.getElementById('sm-branch');
    if (smBranch) {
        const curFilter = (document.getElementById('f-staff-branch') || {value:''}).value;
        smBranch.value = curFilter || '__default__';
    }
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
    const smBranch = document.getElementById('sm-branch');
    const branch_id = (isMultiBranch && smBranch) ? (smBranch.value || '__default__') : (branchId || '__default__');

    if (!name || !username || !password) { toast('❌ Sab fields required hain'); return; }

    const res = await fetch(`/api/staff/${clientId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, username, password, role, branch_id })
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
    const res = await fetch(`/api/staff/${clientId}/${changingPasswordId}/password`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: password })
    });
    if (res.ok) { toast('✅ Password update ho gaya!'); closePassModal(); }
    else { toast('❌ Failed'); }
}

async function toggleStaff(staff_id, currentlyActive) {
    const res = await fetch(`/api/staff/${clientId}/${staff_id}/toggle`, { method: 'PATCH' });
    const d = await res.json();
    if (res.ok) {
        toast(d.is_active ? '✅ Staff activated' : '🔴 Staff deactivated');
        loadStaff();
    } else { toast('❌ Failed'); }
}

async function deleteStaff(staff_id, name) {
    if (!confirm(`'${name}' ko permanently delete karna hai?`)) return;
    const res = await fetch(`/api/staff/${clientId}/${staff_id}`, { method: 'DELETE' });
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


// ════════════════════════════════
// MANAGE TAB
// ════════════════════════════════
let ownerRestData    = null;   // full restaurant JSON
let ownerEditIndex   = -1;     // dish index being edited
let manageInitDone   = false;

function switchManageSub(sub, btn) {
    ['dishes','info'].forEach(s => {
        document.getElementById(`msub-${s}`).style.display = s === sub ? 'block' : 'none';
    });
    document.querySelectorAll('.manage-sub-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

// ── Manage branch change ──
function onManageBranchChange() {
    ownerRestData = null;
    manageInitDone = false;
    initManageTab();
}

async function initManageTab() {
    if (!ownerRestData) await loadOwnerRestData();
    renderOwnerDishes();
}

async function loadOwnerRestData() {
    try {
        const selectedBranch = getTabBranch('manage') || branchId;
        // BRANCHES already available hai page load se — extra API call nahi
        const branchObj = allBranches.find(b => (b.branch_id || b.id) === selectedBranch)
                       || allBranches[0];
        if (branchObj) {
            ownerRestData = getBranchConfig(branchObj);
            populateInfoFields();
            populateTableCount();
            return;
        }
        // Fallback — API call
        const res = await fetch(`/api/owner/${clientId}/json?branch_id=${selectedBranch}`);
        if (!res.ok) throw new Error();
        ownerRestData = await res.json();
        populateInfoFields();
        populateTableCount();
    } catch(e) {
        toast('❌ Restaurant data load nahi hua');
    }
}

// ── Dishes ──
function renderOwnerDishes() {
    const items = ownerRestData?.items || [];
    const el = document.getElementById('owner-items-list');
    if (!items.length) {
        el.innerHTML = '<div class="empty-state"><i class="fas fa-utensils"></i><p>Koi dish nahi — Add karo!</p></div>';
        return;
    }
    el.innerHTML = items.map((item, i) => {
        const priceText = item.sizes
            ? item.sizes.map(s => s.label + ': ₹' + s.price).join(' / ')
            : (item.price ? '₹' + item.price : '');
        const vegColor = item.veg ? '#4caf50' : '#ef5350';
        const imgHtml = item.image
            ? `<img class="owner-dish-img" src="${item.image}" alt="" onerror="this.style.display='none'">`
            : `<div class="owner-dish-img" style="display:flex;align-items:center;justify-content:center;font-size:1.4rem;">🍽️</div>`;
        return `<div class="owner-dish-row">
            ${imgHtml}
            <div class="owner-dish-info">
                <div class="owner-dish-name">
                    <span class="owner-dish-veg" style="background:${vegColor};display:inline-block;margin-right:5px;"></span>
                    ${item.name}
                </div>
                <div class="owner-dish-meta">${item.category || ''} ${priceText ? '· ' + priceText : ''}</div>
            </div>
            <div class="owner-dish-actions">
                <button class="owner-dish-btn owner-dish-edit" onclick="openOwnerEditDish(${i})">✏️</button>
                <button class="owner-dish-btn owner-dish-delete" onclick="deleteOwnerDish(${i})">🗑</button>
            </div>
        </div>`;
    }).join('');
}

function openOwnerAddDish() {
    ownerEditIndex = -1;
    document.getElementById('odm-title').textContent = 'Dish Add Karo';
    ['odm-name','odm-price','odm-category','odm-desc','odm-ingredients','odm-image'].forEach(id => {
        document.getElementById(id).value = '';
    });
    document.getElementById('odm-model').value = '';
    document.getElementById('odm-model-display').textContent = 'No 3D model';
    document.getElementById('odm-veg').value = 'true';
    document.getElementById('odm-featured').value = 'true';
    document.getElementById('odm-position').value = '';
    document.getElementById('odm-scale').value = '';
    document.getElementById('odm-rotation').value = '';
    document.getElementById('odm-rotate-speed').value = '';
    document.getElementById('odm-auto-rotate').value = '';
    document.getElementById('odm-multisize').checked = false;
    document.getElementById('odm-sizes-list').innerHTML = '';
    document.getElementById('odm-price-single').style.display = '';
    document.getElementById('odm-price-multi').style.display = 'none';
    // Reset image box
    resetOwnerUploadBox('odm-image-box','odm-image-preview','odm-image-hint','odm-image-icon');
    document.getElementById('owner-dish-modal').style.display = 'flex';
}

function openOwnerEditDish(index) {
    ownerEditIndex = index;
    const item = ownerRestData.items[index];
    document.getElementById('odm-title').textContent = 'Dish Edit Karo';
    document.getElementById('odm-name').value         = item.name || '';
    document.getElementById('odm-category').value     = item.category || '';
    document.getElementById('odm-desc').value         = item.description || '';
    document.getElementById('odm-ingredients').value  = item.ingredients || '';
    document.getElementById('odm-image').value        = item.image || '';
    document.getElementById('odm-model').value        = item.model || '';
    document.getElementById('odm-model-display').textContent = item.model
        ? item.model.split('/').pop() + ' (contact ZenTable to change)'
        : 'No 3D model — contact ZenTable to add';
    document.getElementById('odm-veg').value          = String(item.veg ?? true);
    document.getElementById('odm-featured').value     = String(item.featured ?? true);
    document.getElementById('odm-position').value     = item.position || '';
    document.getElementById('odm-scale').value        = item.scale || '';
    document.getElementById('odm-rotation').value     = item.rotation || '';
    document.getElementById('odm-rotate-speed').value = item.rotate_speed || '';
    document.getElementById('odm-auto-rotate').value  = String(item.auto_rotate ?? true);

    // Image
    resetOwnerUploadBox('odm-image-box','odm-image-preview','odm-image-hint','odm-image-icon');
    if (item.image) {
        const prev = document.getElementById('odm-image-preview');
        prev.src = item.image; prev.style.display = '';
        document.getElementById('odm-image-icon').style.display = 'none';
        document.getElementById('odm-image-hint').textContent = '✓ ' + item.image.split('/').pop();
        document.getElementById('odm-image-box').classList.add('upload-success');
    }

    // Sizes
    if (item.sizes && item.sizes.length > 0) {
        document.getElementById('odm-multisize').checked = true;
        document.getElementById('odm-price-single').style.display = 'none';
        document.getElementById('odm-price-multi').style.display = '';
        document.getElementById('odm-sizes-list').innerHTML = '';
        item.sizes.forEach(s => addOwnerSizeRow(s.label, s.price));
        document.getElementById('odm-price').value = '';
    } else {
        document.getElementById('odm-multisize').checked = false;
        document.getElementById('odm-price-single').style.display = '';
        document.getElementById('odm-price-multi').style.display = 'none';
        document.getElementById('odm-sizes-list').innerHTML = '';
        document.getElementById('odm-price').value = item.price || '';
    }

    document.getElementById('owner-dish-modal').style.display = 'flex';
}

function closeOwnerDishModal() {
    document.getElementById('owner-dish-modal').style.display = 'none';
}

function toggleOwnerSizeMode() {
    const on = document.getElementById('odm-multisize').checked;
    document.getElementById('odm-price-single').style.display = on ? 'none' : '';
    document.getElementById('odm-price-multi').style.display  = on ? '' : 'none';
    if (on && document.getElementById('odm-sizes-list').children.length === 0) {
        addOwnerSizeRow(); addOwnerSizeRow();
    }
}

function addOwnerSizeRow(label = '', price = '') {
    const list = document.getElementById('odm-sizes-list');
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;align-items:center;';
    row.innerHTML = `
        <input type="text" placeholder="e.g. Half" value="${label}"
            style="flex:1;padding:8px 10px;border-radius:8px;border:1.5px solid #eee;font-size:0.84rem;outline:none;font-family:var(--font-secondary);">
        <input type="text" placeholder="₹ 180" value="${price}"
            style="flex:1;padding:8px 10px;border-radius:8px;border:1.5px solid #eee;font-size:0.84rem;outline:none;font-family:var(--font-secondary);">
        <button type="button" onclick="this.parentElement.remove()"
            style="background:none;border:none;cursor:pointer;color:#aaa;font-size:1rem;padding:4px;">✕</button>
    `;
    list.appendChild(row);
}

async function saveOwnerDish() {
    const isMulti = document.getElementById('odm-multisize').checked;
    let priceField = {};
    if (isMulti) {
        const rows = document.getElementById('odm-sizes-list').querySelectorAll('div');
        const sizes = [];
        rows.forEach(row => {
            const inputs = row.querySelectorAll('input[type=text]');
            if (inputs.length >= 2) {
                const lbl = inputs[0].value.trim(), prc = inputs[1].value.trim();
                if (lbl && prc) sizes.push({ label: lbl, price: prc });
            }
        });
        if (sizes.length === 0) { toast('❌ At least one size required'); return; }
        priceField = { sizes };
    } else {
        const p = document.getElementById('odm-price').value.trim();
        if (!p) { toast('❌ Price required'); return; }
        priceField = { price: p };
    }

    const name = document.getElementById('odm-name').value.trim();
    if (!name) { toast('❌ Dish name required'); return; }

    const item = {
        name,
        ...priceField,
        category:     document.getElementById('odm-category').value.trim(),
        description:  document.getElementById('odm-desc').value.trim(),
        ingredients:  document.getElementById('odm-ingredients').value.trim(),
        image:        document.getElementById('odm-image').value.trim(),
        model:        document.getElementById('odm-model').value.trim(),
        position:     document.getElementById('odm-position').value.trim(),
        scale:        document.getElementById('odm-scale').value.trim(),
        rotation:     document.getElementById('odm-rotation').value.trim(),
        rotate_speed: parseInt(document.getElementById('odm-rotate-speed').value) || 10000,
        auto_rotate:  document.getElementById('odm-auto-rotate').value !== 'false',
        veg:          document.getElementById('odm-veg').value === 'true',
        featured:     document.getElementById('odm-featured').value === 'true',
    };

    if (!ownerRestData.items) ownerRestData.items = [];
    if (ownerEditIndex === -1) ownerRestData.items.push(item);
    else ownerRestData.items[ownerEditIndex] = item;

    const ok = await pushOwnerRestData();
    if (ok) {
        toast('✅ Dish saved!');
        closeOwnerDishModal();
        renderOwnerDishes();
    }
}

async function deleteOwnerDish(index) {
    if (!confirm(`"${ownerRestData.items[index]?.name}" delete karna hai?`)) return;
    ownerRestData.items.splice(index, 1);
    const ok = await pushOwnerRestData();
    if (ok) { toast('🗑 Dish deleted'); renderOwnerDishes(); }
}

// ── Restaurant Info ──
function populateInfoFields() {
    const r = ownerRestData?.restaurant || {};
    document.getElementById('oi-name').value      = r.name || '';
    document.getElementById('oi-tagline').value   = r.tagline || '';
    document.getElementById('oi-desc').value      = r.description || '';
    document.getElementById('oi-phone').value     = r.phone || '';
    document.getElementById('oi-email').value     = r.email || '';
    document.getElementById('oi-address').value   = r.address || '';
    document.getElementById('oi-lunch').value     = r.timings?.lunch || '';
    document.getElementById('oi-dinner').value    = r.timings?.dinner || '';
    document.getElementById('oi-closed').value    = r.timings?.closed || '';
    document.getElementById('oi-instagram').value = r.social?.instagram || '';
    document.getElementById('oi-facebook').value  = r.social?.facebook || '';
    document.getElementById('oi-twitter').value   = r.social?.twitter || '';
    document.getElementById('oi-logo').value      = r.logo || '';
    document.getElementById('oi-banner').value    = r.banner || '';

    resetOwnerUploadBox('oi-logo-box','oi-logo-preview','oi-logo-hint','oi-logo-icon');
    if (r.logo) {
        const prev = document.getElementById('oi-logo-preview');
        prev.src = r.logo; prev.style.display = '';
        document.getElementById('oi-logo-icon').style.display = 'none';
        document.getElementById('oi-logo-hint').textContent = '✓ ' + r.logo.split('/').pop();
        document.getElementById('oi-logo-box').classList.add('upload-success');
    }
    resetOwnerUploadBox('oi-banner-box','oi-banner-preview','oi-banner-hint','oi-banner-icon');
    if (r.banner) {
        const prev = document.getElementById('oi-banner-preview');
        prev.src = r.banner; prev.style.display = '';
        document.getElementById('oi-banner-icon').style.display = 'none';
        document.getElementById('oi-banner-hint').textContent = '✓ ' + r.banner.split('/').pop();
        document.getElementById('oi-banner-box').classList.add('upload-success');
    }
}

async function saveRestaurantInfo() {
    const r = ownerRestData.restaurant;
    r.name        = document.getElementById('oi-name').value.trim();
    r.tagline     = document.getElementById('oi-tagline').value.trim();
    r.description = document.getElementById('oi-desc').value.trim();
    r.phone       = document.getElementById('oi-phone').value.trim();
    r.email       = document.getElementById('oi-email').value.trim();
    r.address     = document.getElementById('oi-address').value.trim();
    r.timings     = {
        lunch:  document.getElementById('oi-lunch').value.trim(),
        dinner: document.getElementById('oi-dinner').value.trim(),
        closed: document.getElementById('oi-closed').value.trim(),
    };
    r.social = {
        instagram: document.getElementById('oi-instagram').value.trim(),
        facebook:  document.getElementById('oi-facebook').value.trim(),
        twitter:   document.getElementById('oi-twitter').value.trim(),
    };
    const logoVal   = document.getElementById('oi-logo').value.trim();
    const bannerVal = document.getElementById('oi-banner').value.trim();
    if (logoVal)   r.logo   = logoVal;
    if (bannerVal) r.banner = bannerVal;

    const ok = await pushOwnerRestData();
    if (ok) toast('✅ Info saved!');
}

// ── Table Count ──
function populateTableCount() {
    document.getElementById('oi-num-tables').value = ownerRestData?.restaurant?.num_tables || 6;
}

async function saveTableCount() {
    const val = parseInt(document.getElementById('oi-num-tables').value);
    if (!val || val < 1 || val > 500) { toast('❌ 1–500 ke beech hona chahiye'); return; }
    // Tables tab ki selected branch use karo — manage tab ki nahi
    const tablesBranch = getTabBranch('tables')
        || (allBranches[0] && (allBranches[0].branch_id || allBranches[0].id))
        || branchId;
    // Us branch ka fresh data API se fetch karo — ownerRestData overwrite nahi karna
    let branchData = null;
    try {
        const r = await fetch(`/api/owner/${clientId}/json?branch_id=${tablesBranch}`);
        if (r.ok) branchData = await r.json();
    } catch(e) {}
    if (!branchData) { toast('❌ Data load nahi hua, dobara try karo'); return; }
    if (!branchData.restaurant) branchData.restaurant = {};
    branchData.restaurant.num_tables = val;
    try {
        const res = await fetch(`/api/owner/${clientId}/json?branch_id=${tablesBranch}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: branchData }),
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Error');
        toast('✅ Table count saved!');
        // allBranches cache bhi update karo — warna loadTables stale count dikhayega
        const updatedBranch = allBranches.find(b => (b.branch_id || b.id) === tablesBranch);
        if (updatedBranch) {
            const cfg = getBranchConfig(updatedBranch);
            if (cfg.restaurant) cfg.restaurant.num_tables = val;
            updatedBranch.config = cfg;
        }
        loadTables();
    } catch(e) {
        toast('❌ Save failed: ' + e.message);
    }
}

// ── Push data to server ──
async function pushOwnerRestData(branchOverride) {
    try {
        const selectedBranch = branchOverride || getTabBranch('manage') || branchId;
        const res = await fetch(`/api/owner/${clientId}/json?branch_id=${selectedBranch}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: ownerRestData }),
        });
        if (!res.ok) throw new Error((await res.json()).detail || 'Error');
        return true;
    } catch(e) {
        toast('❌ Save failed: ' + e.message);
        return false;
    }
}

// ── Upload helper for owner panel ──
async function handleOwnerUpload(input, hiddenId, boxId, previewId, hintId, iconId, progressId, barId, type) {
    const file = input.files[0];
    if (!file) return;
    const box = document.getElementById(boxId);
    box.classList.remove('upload-success','upload-error');
    const progressEl = document.getElementById(progressId);
    const barEl      = document.getElementById(barId);
    progressEl.style.display = '';
    barEl.style.width = '10%';

    const fd = new FormData();
    fd.append('file', file);
    fd.append('type', type);

    try {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = e => {
            if (e.lengthComputable) barEl.style.width = Math.round(e.loaded/e.total*90) + '%';
        };
        await new Promise((resolve, reject) => {
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
                else reject(new Error(xhr.responseText));
            };
            xhr.onerror = reject;
            xhr.open('POST', `/api/owner/upload/${clientId}`);
            xhr.send(fd);
        }).then(data => {
            barEl.style.width = '100%';
            setTimeout(() => progressEl.style.display = 'none', 500);
            document.getElementById(hiddenId).value = data.path;
            if (previewId) {
                const prev = document.getElementById(previewId);
                if (prev) { prev.src = data.path; prev.style.display = ''; }
            }
            if (iconId) document.getElementById(iconId).style.display = 'none';
            document.getElementById(hintId).textContent = '✓ ' + file.name;
            box.classList.add('upload-success');
            toast('✅ ' + file.name + ' uploaded!');
        });
    } catch(e) {
        barEl.style.width = '100%';
        progressEl.style.display = 'none';
        box.classList.add('upload-error');
        toast('❌ Upload failed');
    }
    input.value = '';
}

function resetOwnerUploadBox(boxId, previewId, hintId, iconId) {
    const box = document.getElementById(boxId);
    if (box) box.classList.remove('upload-success','upload-error');
    if (previewId) { const p = document.getElementById(previewId); if (p) { p.src=''; p.style.display='none'; } }
    if (hintId)  { const h = document.getElementById(hintId); if (h) h.textContent = 'Click to upload'; }
    if (iconId)  { const ic = document.getElementById(iconId); if (ic) ic.style.display = ''; }
}
