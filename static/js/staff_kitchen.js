// clientId, restaurantLogo — HTML template mein inject hote hain

// ── ORDER STATUS UPDATE ──
async function updateStatus(orderId, status) {
    await fetch(`/api/order/${orderId}/status`, {
        method: 'PATCH',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ status })
    });
}

// ── READY ITEMS UPDATE ──
async function updateReadyItems(orderId, pendingItems, readyItemsMap) {
    const checked = [];
    pendingItems.forEach((item, i) => {
        const cb = document.getElementById(`item-${orderId}-${i}`);
        if (cb && cb.checked) checked.push(item.name);
    });

    // Pehle se ready + abhi check kiye — {name,qty} format
    const newReadyMap = {};
    (readyItemsMap || []).forEach(r => { newReadyMap[r.name] = r.qty; });
    pendingItems.forEach(item => {
        if (checked.includes(item.name)) newReadyMap[item.name] = (newReadyMap[item.name] || 0) + item.qty;
    });
    const allReadyNow = Object.entries(newReadyMap).map(([name, qty]) => ({ name, qty }));

    const checkedQty      = pendingItems.filter(i => checked.includes(i.name)).reduce((s,i) => s+i.qty, 0);
    const totalPendingQty = pendingItems.reduce((s,i) => s+i.qty, 0);
    const newStatus       = checkedQty === 0 ? 'pending' : checkedQty === totalPendingQty ? 'ready' : 'preparing';

    // Ek saath dono update karo — parallel
    await Promise.all([
        fetch(`/api/order/${orderId}/ready-items`, {
            method: 'PATCH',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ ready_items: allReadyNow })
        }),
        fetch(`/api/order/${orderId}/status`, {
            method: 'PATCH',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ status: newStatus })
        })
    ]);

    if (newStatus === 'ready') {
        toast(`Order #${orderId} fully ready!`);
        load();
        return;
    }

    // Counter update — reload nahi, sirf counter
    const counter = document.getElementById(`counter-${orderId}`);
    if (counter) {
        counter.textContent = `${checkedQty}/${totalPendingQty} Ready`;
        counter.className = 'ready-status ' + (checkedQty > 0 ? 'partial-ready' : 'none-ready');
    }
    const master = document.getElementById(`master-${orderId}`);
    if (master) {
        master.checked = false;
        master.indeterminate = checkedQty > 0 && checkedQty < totalPendingQty;
    }
}

// ── MASTER CHECKBOX ──
function toggleMaster(orderId, pendingItems, readyItemsMap, checked) {
    pendingItems.forEach((_, i) => {
        const cb = document.getElementById(`item-${orderId}-${i}`);
        if (cb) cb.checked = checked;
    });
    updateReadyItems(orderId, pendingItems, readyItemsMap);
}

// ── TOAST ──
function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// ── NOTIFICATIONS ──
let notifPermission = Notification.permission;
let knownOrderIds = new Set();
let firstLoad = true;

async function requestNotifPermission() {
    if (notifPermission === 'default') {
        notifPermission = await Notification.requestPermission();
    }
}

function sendNotif(title, body) {
    if (notifPermission === 'granted') {
        const n = new Notification(title, {
            body,
            icon: restaurantLogo,
            badge: restaurantLogo,
            tag: 'kitchen-order-' + Date.now(),
            requireInteraction: true
        });
        n.onclick = () => { window.focus(); n.close(); };
    }
}

// ── MAIN LOAD ──
async function loadWithNotif() {
    const res = await fetch(`/api/orders/${clientId}`);
    const orders = await res.json();
    // pending, preparing, ready — sirf done hide hoga
    const active = orders.filter(o => ['pending','preparing','ready'].includes(o.status));

    if (!firstLoad) {
        const newPending = active.filter(o => o.status === 'pending' && !knownOrderIds.has(o.id));
        if (newPending.length > 0) {
            const tables = [...new Set(newPending.map(o => o.table_no))].join(', ');
            sendNotif(
                `New Order${newPending.length>1?'s':''}!`,
                `Table${newPending.length>1?'s':''} ${tables} — tap to view`
            );
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.frequency.value = 880; osc.type = 'sine';
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
                osc.start(ctx.currentTime); osc.stop(ctx.currentTime + 0.4);
            } catch(e) {}
        }
    }

    active.forEach(o => knownOrderIds.add(o.id));
    firstLoad = false;

    const list = document.getElementById('orders-list');
    if (!active.length) {
        list.innerHTML = `<div class="empty-state">
            <i class="fas fa-check-circle" style="color:#4caf50"></i>
            <p>No pending orders!</p>
        </div>`;
        return;
    }

    // Sort: pending first, phir preparing, phir ready; same status mein newest first
    const statusOrder = { pending: 0, preparing: 1, ready: 2 };
    active.sort((a, b) => {
        const sd = (statusOrder[a.status] ?? 9) - (statusOrder[b.status] ?? 9);
        if (sd !== 0) return sd;
        return b.id - a.id;  // newer orders first
    });

    list.innerHTML = active.map(o => {
        const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
        const readyRaw = typeof o.ready_items === 'string'
            ? JSON.parse(o.ready_items || '[]')
            : (o.ready_items || []);

        // Normalize to [{name, qty}] — legacy List[str] support
        const readyQtyMap = {};
        readyRaw.forEach(r => {
            if (typeof r === 'string') {
                // legacy: naam ready hai — kitni qty ready? jo items mein hai utni
                const it = items.find(i => i.name === r);
                readyQtyMap[r] = it ? it.qty : 0;
            } else {
                readyQtyMap[r.name] = r.qty;
            }
        });

        // Build readyItemsMap for passing to functions
        const readyItemsMap = Object.entries(readyQtyMap).map(([name, qty]) => ({ name, qty }));

        // Split into ready rows and pending rows (partial qty support)
        const readyRows   = [];
        const pendingRows = [];
        items.forEach(item => {
            const rQty = readyQtyMap[item.name] || 0;
            if (rQty >= item.qty) {
                readyRows.push({ name: item.name, qty: item.qty });
            } else if (rQty > 0) {
                readyRows.push({ name: item.name, qty: rQty });
                pendingRows.push({ name: item.name, qty: item.qty - rQty, price: item.price });
            } else {
                pendingRows.push({ name: item.name, qty: item.qty, price: item.price });
            }
        });

        const time            = (o.created_at || '').substring(11, 16);
        const totalPendingQty = pendingRows.reduce((s, i) => s + i.qty, 0);
        const pendingEncoded  = encodeURIComponent(JSON.stringify(pendingRows));
        const readyMapEncoded = encodeURIComponent(JSON.stringify(readyItemsMap));

        const readySection = readyRows.length > 0 ? `
                <div style="padding:4px 0 2px;border-bottom:1px dashed #e0e0e0;margin-bottom:4px;">
                    <span style="font-size:0.7rem;font-weight:700;color:#4caf50;text-transform:uppercase;letter-spacing:0.5px;">✅ Done</span>
                </div>
                ${readyRows.map(item => `
                <div class="item-check-row">
                    <label class="check-label">
                        <input type="checkbox" checked disabled style="opacity:0.4;">
                        <span class="check-text item-done">${item.name} ×${item.qty}</span>
                    </label>
                </div>`).join('')}
                ${pendingRows.length > 0 ? '<div class="item-divider"></div>' : ''}` : '';

        const pendingSection = pendingRows.length > 0 ? `
                <div class="item-check-row master-row">
                    <label class="check-label">
                        <input type="checkbox"
                            id="master-${o.id}"
                            onchange="toggleMaster(${o.id}, JSON.parse(decodeURIComponent('${pendingEncoded}')), JSON.parse(decodeURIComponent('${readyMapEncoded}')), this.checked)">
                        <span class="check-text master-text">All Items Ready</span>
                    </label>
                    <span id="counter-${o.id}" class="ready-status none-ready">
                        0/${totalPendingQty} Ready
                    </span>
                </div>
                <div class="item-divider"></div>
                ${pendingRows.map((item, i) => `
                <div class="item-check-row">
                    <label class="check-label">
                        <input type="checkbox"
                            id="item-${o.id}-${i}"
                            onchange="updateReadyItems(${o.id}, JSON.parse(decodeURIComponent('${pendingEncoded}')), JSON.parse(decodeURIComponent('${readyMapEncoded}')))">
                        <span class="check-text">${item.name} ×${item.qty}</span>
                    </label>
                </div>`).join('')}` : '';

        return `<div class="order-card ${o.status}">
            <div class="order-head">
                <div>
                    <div class="order-table">Table ${o.table_no}</div>
                    <div class="order-id"><span style="background:var(--primary);color:var(--secondary);padding:1px 7px;border-radius:5px;font-weight:700;">#${o.id}</span> &nbsp;·&nbsp; ${o.source}</div>
                </div>
                <div class="order-time">${time}</div>
            </div>
            <div class="order-items">
                ${readySection}
                ${pendingSection}
            </div>
            <div class="order-foot">
                <div class="order-total">₹${o.total}</div>
            </div>
        </div>`;
    }).join('');
}

// ── NOTIF BUTTON ──
const topbar = document.querySelector('.topbar > div:last-child');
const notifBtn = document.createElement('button');
notifBtn.className = 'logout-btn';
notifBtn.id = 'notif-btn';
notifBtn.innerHTML = '🔔 Alerts';
notifBtn.onclick = async () => {
    await requestNotifPermission();
    notifBtn.innerHTML = notifPermission === 'granted' ? '🔔 On' : '🔕 Off';
    toast(notifPermission === 'granted' ? 'Notifications enabled!' : 'Notifications blocked');
};
topbar.insertBefore(notifBtn, topbar.firstChild);
if (notifPermission === 'granted') notifBtn.innerHTML = '🔔 On';

async function load() { await loadWithNotif(); }

requestNotifPermission();
load();
setInterval(load, 20000);
