// clientId, restaurantLogo — HTML template mein inject hote hain

// ── ORDER STATUS UPDATE ──
async function updateStatus(orderId, status) {
    const res = await fetch(`/api/order/${orderId}/status`, {
        method: 'PATCH',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ status })
    });
    if (res.ok) {
        toast(`Order #${orderId} → ${status}`);
        if (status === 'ready') load();
    }
}

// ── READY ITEMS UPDATE ──
async function updateReadyItems(orderId, totalItems) {
    const checked = [];
    totalItems.forEach((item, i) => {
        const cb = document.getElementById(`item-${orderId}-${i}`);
        if (cb && cb.checked) checked.push(item.name);
    });

    // DB mein ready_items update karo
    await fetch(`/api/order/${orderId}/ready-items`, {
        method: 'PATCH',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ ready_items: checked })
    });

    // Option A logic — auto status
    if (checked.length === 0) {
        // koi item ready nahi — pending rakho
        await updateStatus(orderId, 'pending');
    } else if (checked.length === totalItems.length) {
        // sab ready — order ready mark karo
        await updateStatus(orderId, 'ready');
    } else {
        // kuch ready, kuch nahi — preparing
        await updateStatus(orderId, 'preparing');
    }

    // Master checkbox sync
    const master = document.getElementById(`master-${orderId}`);
    if (master) master.checked = checked.length === totalItems.length;
    if (master) master.indeterminate = checked.length > 0 && checked.length < totalItems.length;

    // Counter update
    const counter = document.getElementById(`counter-${orderId}`);
    if (counter) counter.textContent = `${checked.length}/${totalItems.length} Ready`;
    if (counter) {
        counter.className = 'ready-status ' + (checked.length === totalItems.length ? 'all-ready' : checked.length > 0 ? 'partial-ready' : 'none-ready');
    }
}

// ── MASTER CHECKBOX ──
function toggleMaster(orderId, items, checked) {
    items.forEach((_, i) => {
        const cb = document.getElementById(`item-${orderId}-${i}`);
        if (cb) cb.checked = checked;
    });
    updateReadyItems(orderId, items);
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
            tag: 'kitchen-order',
            requireInteraction: true
        });
        n.onclick = () => { window.focus(); n.close(); };
    }
}

// ── MAIN LOAD ──
async function loadWithNotif() {
    const res = await fetch(`/api/orders/${clientId}`);
    const orders = await res.json();
    const active = orders.filter(o => !['done','cancelled'].includes(o.status));

    if (!firstLoad) {
        const newPending = active.filter(o => o.status === 'pending' && !knownOrderIds.has(o.id));
        if (newPending.length > 0) {
            const tables = [...new Set(newPending.map(o => o.table_no))].join(', ');
            sendNotif(
                `🔥 ${newPending.length} New Order${newPending.length>1?'s':''}!`,
                `Table${newPending.length>1?'s':''} ${tables} — tap to view`
            );
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.frequency.value = 880;
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.4);
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

    list.innerHTML = active.map(o => {
        const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
        const readyItems = typeof o.ready_items === 'string'
            ? JSON.parse(o.ready_items || '[]')
            : (o.ready_items || []);
        const time = (o.created_at || '').substring(11, 16);
        const allReady = readyItems.length === items.length;
        const someReady = readyItems.length > 0 && !allReady;

        // items ko safely encode karo inline use ke liye
        const itemsEncoded = encodeURIComponent(JSON.stringify(items));

        return `<div class="order-card ${o.status}">
            <div class="order-head">
                <div>
                    <div class="order-table">Table ${o.table_no}</div>
                    <div class="order-id">#${o.id} &nbsp;·&nbsp; ${o.source}</div>
                </div>
                <div class="order-time">${time}</div>
            </div>

            <div class="order-items">
                <!-- Master checkbox -->
                <div class="item-check-row master-row">
                    <label class="check-label">
                        <input type="checkbox"
                            id="master-${o.id}"
                            ${allReady ? 'checked' : ''}
                            onchange="toggleMaster(${o.id}, JSON.parse(decodeURIComponent('${itemsEncoded}')), this.checked)">
                        <span class="check-text master-text">All Items Ready</span>
                    </label>
                    <span id="counter-${o.id}" class="ready-status ${allReady ? 'all-ready' : someReady ? 'partial-ready' : 'none-ready'}">
                        ${readyItems.length}/${items.length} Ready
                    </span>
                </div>
                <div class="item-divider"></div>

                <!-- Per item checkboxes -->
                ${items.map((item, i) => {
                    const isReady = readyItems.includes(item.name);
                    return `<div class="item-check-row">
                        <label class="check-label">
                            <input type="checkbox"
                                id="item-${o.id}-${i}"
                                ${isReady ? 'checked' : ''}
                                onchange="updateReadyItems(${o.id}, JSON.parse(decodeURIComponent('${itemsEncoded}')))">
                            <span class="check-text ${isReady ? 'item-done' : ''}">${item.name} ×${item.qty}</span>
                        </label>
                    </div>`;
                }).join('')}
            </div>

            <div class="order-foot">
                <div class="order-total">₹${o.total}</div>
            </div>
        </div>`;
    }).join('');

    // Master checkbox indeterminate state set karo
    active.forEach(o => {
        const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
        const readyItems = typeof o.ready_items === 'string'
            ? JSON.parse(o.ready_items || '[]')
            : (o.ready_items || []);
        const master = document.getElementById(`master-${o.id}`);
        if (master && readyItems.length > 0 && readyItems.length < items.length) {
            master.indeterminate = true;
        }
    });
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
    toast(notifPermission === 'granted' ? '✅ Notifications enabled!' : '❌ Notifications blocked');
};
topbar.insertBefore(notifBtn, topbar.firstChild);
if (notifPermission === 'granted') notifBtn.innerHTML = '🔔 On';

async function load() { await loadWithNotif(); }

requestNotifPermission();
load();
setInterval(load, 20000);
