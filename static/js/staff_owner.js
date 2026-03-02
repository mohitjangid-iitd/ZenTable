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
    ['overview','analytics','orders','tables'].forEach(t => {
        document.getElementById(`tab-${t}`).style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (tab === 'overview')  { loadAll(); }
    if (tab === 'analytics') { if (!analyticsData) loadAll(); else renderAnalyticsTab(); }
    if (tab === 'orders')    loadOrders();
    if (tab === 'tables')    loadTables();
}

// ── LOAD ALL ──
async function loadAll() {
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
    const status  = document.getElementById('f-status').value;
    const source  = document.getElementById('f-source').value;
    const tableNo = document.getElementById('f-table').value;
    let url = `/api/orders/${clientId}/filter?`;
    if (status)  url += `status=${status}&`;
    if (source)  url += `source=${source}&`;
    if (tableNo) url += `table_no=${tableNo}&`;

    const [ordersRes, summaryRes] = await Promise.all([
        fetch(url), fetch(`/api/tables/${clientId}/summary`)
    ]);
    const orders  = await ordersRes.json();
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

    const sel = document.getElementById('f-table');
    if (sel.options.length <= 1 && tables.length) {
        tables.forEach(t => {
            const o = document.createElement('option');
            o.value = t.table_no; o.textContent = `Table ${t.table_no}`;
            sel.appendChild(o);
        });
    }

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
        </div>`;
    }).join('');
}

function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// Init
loadAll();
setInterval(loadAll, 60000);
