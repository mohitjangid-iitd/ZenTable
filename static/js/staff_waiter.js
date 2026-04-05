// clientId, menuItems, waiterQtys, pendingBillId — HTML template mein inject hote hain

// ── TABS ──
function switchTab(tab, btn) {
    ['tables', 'orders'].forEach(t => {
        document.getElementById(`tab-${t}`).style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (tab === 'tables') loadTables();
    if (tab === 'orders') loadOrders();
}

// ── TABLES ──
async function loadTables() {
    const res = await fetch(`/api/tables/${clientId}/summary`);
    const tables = await res.json();
    const map = {};
    tables.forEach(t => map[t.table_no] = t);

    const grid = document.getElementById('tables-grid');
    const labels = {
        inactive: 'Inactive', active: 'Active', occupied: 'Pending',
        ready: 'Ready', done: 'Delivered', billed: 'Billed', paid: 'Paid'
    };
    grid.innerHTML = Array.from({ length: numTables }, (_, i) => {
        const n = i + 1;
        const t = map[n];
        const ds = t ? t.display_status : 'inactive';
        return `<div class="table-box ${ds}" onclick="openModal(${n})">
            <div class="table-num">T${n}</div>
            <div class="table-status">${labels[ds] || ds}</div>
        </div>`;
    }).join('');
}

// ── ORDERS ──
let currentFilter = 'active';

function setFilter(filter, btn) {
    currentFilter = filter;
    document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Cancelled pill sirf Paid Today ya Cancelled filter pe dikhao
    const cp = document.getElementById('cancelled-pill');
    if (cp) cp.style.display = (filter === 'paid' || filter === 'cancelled') ? 'inline-flex' : 'none';

    loadOrders();
}

async function loadOrders() {
    // Cancelled pill sirf Paid Today tab mein dikhao
    const cancelledPill = document.getElementById('cancelled-pill');
    if (cancelledPill) {
        cancelledPill.style.display = (currentFilter === 'paid' || currentFilter === 'cancelled') ? 'inline-flex' : 'none';
    }

    const [ordersRes, summaryRes] = await Promise.all([
        fetch(`/api/orders/${clientId}`),
        fetch(`/api/tables/${clientId}/summary`)
    ]);
    const all = await ordersRes.json();
    const summary = await summaryRes.json();

    const tMap = {};
    summary.forEach(t => tMap[String(t.table_no)] = t);

    const list = document.getElementById('orders-list');

    let filtered = all.filter(o => o.status !== 'cancelled');

    if (currentFilter === 'active') {
        filtered = filtered.filter(o => ['pending', 'preparing', 'ready'].includes(o.status));

    } else if (currentFilter === 'ready') {
        filtered = filtered.filter(o => o.status === 'ready');

    } else if (currentFilter === 'done') {
        const unpaidDoneSet = new Set();
        summary.forEach(t => {
            if (t.display_status === 'done' && t.unpaid_done_ids) {
                t.unpaid_done_ids.forEach(id => unpaidDoneSet.add(id));
            }
        });
        filtered = filtered.filter(o => unpaidDoneSet.has(o.id));

    } else if (currentFilter === 'billed') {
        const billedOrderSet = new Set();
        summary.forEach(t => {
            if (t.display_status === 'billed' && t.billed_order_ids) {
                t.billed_order_ids.forEach(id => billedOrderSet.add(id));
            }
        });
        filtered = filtered.filter(o => billedOrderSet.has(o.id));

    } else if (currentFilter === 'paid') {
        const paidTodaySet = new Set();
        summary.forEach(t => {
            if (t.paid_today_order_ids) {
                t.paid_today_order_ids.forEach(id => paidTodaySet.add(id));
            }
        });
        filtered = filtered.filter(o => paidTodaySet.has(o.id));
        // Store cancelled today separately for toggle
        const _n2 = new Date(); const today2 = _n2.getFullYear()+'-'+String(_n2.getMonth()+1).padStart(2,'0')+'-'+String(_n2.getDate()).padStart(2,'0');
        window._cancelledToday = all.filter(o => o.status === 'cancelled' && (o.created_at || '').substring(0, 10) === today2);
        window._showCancelledInPaid = window._showCancelledInPaid || false;
    } else if (currentFilter === 'cancelled') {
        const _now = new Date(); const today = _now.getFullYear()+'-'+String(_now.getMonth()+1).padStart(2,'0')+'-'+String(_now.getDate()).padStart(2,'0');
        filtered = all.filter(o => o.status === 'cancelled' && (o.created_at || '').substring(0, 10) === today);
    }

    // Group by table
    const byTable = {};
    filtered.forEach(o => {
        const key = String(o.table_no);
        if (!byTable[key]) byTable[key] = [];
        byTable[key].push(o);
    });

    if (!Object.keys(byTable).length) {
        const emptyMsg = {
            active: 'Koi active order nahi',
            ready: 'Koi order ready nahi',
            done: 'Koi delivered order nahi',
            billed: 'Koi billed table nahi',
            paid: 'Aaj koi paid table nahi',
            cancelled: 'Koi cancelled order nahi',
        };
        list.innerHTML = `<div class="empty-state"><i class="fas fa-check-circle" style="color:#4caf50"></i><p>${emptyMsg[currentFilter] || 'Koi order nahi'}</p></div>`;
        return;
    }

    let html = '';
    for (const [tableNo, orders] of Object.entries(byTable)) {
        const tInfo = tMap[tableNo] || {};
        const ds = tInfo.display_status || 'occupied';

        let rightEl = '';
        if (currentFilter === 'active') {
            rightEl = `<span style="font-size:0.75rem;color:#888">${orders.length} order${orders.length > 1 ? 's' : ''}</span>`;
        } else if (currentFilter === 'done') {
            const doneTotal = orders.reduce((s, o) => s + o.total, 0);
            rightEl = `<button class="bill-btn" onclick="closeModal && closeModal(); openBillingSheet(${tableNo}, ${doneTotal})">
                Bill ₹${doneTotal}</button>`;
        } else if (currentFilter === 'billed') {
            const tSum = tMap[tableNo] || {};
            const billId = tSum.bill_id;
            const billTotal = tSum.bill_total;
            rightEl = `
                <div style="display:flex;align-items:center;gap:8px">
                    <select id="pay-mode-${tableNo}" style="padding:6px 10px;border:1.5px solid #eee;border-radius:8px;font-size:0.78rem;outline:none;font-family:var(--font-secondary)">
                        <option value="cash">💵 Cash</option>
                        <option value="upi">📱 UPI</option>
                        <option value="card">💳 Card</option>
                    </select>
                    <button class="pay-btn" style="padding:7px 14px;font-size:0.8rem;border-radius:8px;white-space:nowrap"
                        onclick="markPaidFromList(${billId}, ${tableNo})">
                        ✅ Pay ₹${billTotal}
                    </button>
                </div>`;
        } else if (currentFilter === 'paid') {
            rightEl = `<span class="bill-tag-paid">✅ PAID</span>`;
        }

        // Paid Today section ke upar cancelled toggle button inject (sirf ek baar)
        if (currentFilter === 'paid' && !document.getElementById('cancelled-toggle-btn')) {
            const toolbar = document.querySelector('#tab-orders .toolbar');
            if (toolbar && !document.getElementById('cancelled-toggle-btn')) {
                // add after list render — handled below
            }
        }

        html += `<div class="table-group">
            <div class="table-group-head">
                <div class="table-group-title">Table ${tableNo}</div>
                ${rightEl}
            </div>
            <div class="table-group-body">
            ${orders.map(o => {
            const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
            const _rRaw = typeof o.ready_items === 'string'
                ? JSON.parse(o.ready_items || '[]')
                : (o.ready_items || []);
            const _rMap = {};
            _rRaw.forEach(r => typeof r === 'string' ? (_rMap[r] = Infinity) : (_rMap[r.name] = r.qty));
            const canDeliver = o.status === 'ready';

            // Item-wise ready status — active aur ready filter mein dikhao
            let itemsHtml = '';
            if (currentFilter === 'active' || currentFilter === 'ready') {
                itemsHtml = items.map(i => {
                    const isReady = (_rMap[i.name] || 0) > 0;
                    return `<div class="waiter-item-row">
                            <span class="waiter-item-dot ${isReady ? 'dot-ready' : 'dot-pending'}"></span>
                            <span class="waiter-item-name ${isReady ? 'waiter-item-ready' : ''}">${i.name} ×${i.qty}</span>
                            ${isReady ? '<span class="waiter-item-tag">Ready</span>' : ''}
                        </div>`;
                }).join('');
            } else {
                // Baaki filters mein simple text
                itemsHtml = `<div class="order-items-text">${items.map(i => `${i.name} ×${i.qty}`).join(', ')}</div>`;
            }

            // Ready progress badge — qty-aware
            const _readyQtyTotal = items.reduce((s,i) => s + (_rMap[i.name] ? Math.min(_rMap[i.name], i.qty) : 0), 0);
            const _totalQty = items.reduce((s,i) => s + i.qty, 0);
            const progressBadge = (currentFilter === 'active' && _readyQtyTotal > 0)
                ? `<span class="ready-progress ${_readyQtyTotal === _totalQty ? 'rp-full' : 'rp-partial'}">
                        ${_readyQtyTotal}/${_totalQty} ready</span>`
                : '';

            return `<div class="order-row ${o.status}">
                    <div class="order-row-top">
                        <div style="display:flex;gap:5px;align-items:center;flex-wrap:wrap">
                            <span style="background:var(--primary);color:var(--secondary);padding:1px 7px;border-radius:5px;font-weight:700;font-size:0.8rem">#${o.id}</span>
                            <span class="badge ${o.status}">${o.status}</span>
                            <span class="badge staff">${o.source === 'waiter' ? 'staff' : o.source}</span>
                            ${progressBadge}
                        </div>
                        <span style="font-size:0.72rem;color:#bbb">${(o.created_at || '').substring(11, 16)}</span>
                    </div>
                    <div class="waiter-items-list">${itemsHtml}</div>
                    <div class="order-row-foot">
                        <span class="order-total-sm">₹${o.total}</span>
                        <div style="display:flex;gap:6px;">
                        ${canDeliver ? `<button class="deliver-btn" onclick="markDelivered(${o.id})">✓ Delivered</button>` : ''}
                        ${['pending','preparing'].includes(o.status) ? `<button class="edit-order-btn" onclick="openEditOrder(${o.id})">✏️</button>` : ''}
                        </div>
                    </div>
                </div>`;
        }).join('')}
            </div>
        </div>`;
    }
    list.innerHTML = html;

    // Paid Today: cancelled toggle button inject karo
    if (currentFilter === 'paid') {
        const cancelledToday = window._cancelledToday || [];
        const ordersDiv = document.getElementById('orders-list');

        // Button inject at top
        const btnWrap = document.createElement('div');
        btnWrap.style.cssText = 'display:flex;justify-content:flex-end;margin-bottom:10px;';
        btnWrap.innerHTML = `<button id="cancelled-toggle-btn"
            onclick="toggleCancelledSection()"
            style="padding:5px 12px;border-radius:20px;border:1.5px solid #ffcdd2;background:${window._showCancelledInPaid ? '#fff0f0' : 'white'};color:#e53935;font-size:0.78rem;font-weight:600;cursor:pointer;">
            ❌ Cancelled${cancelledToday.length ? ' ('+cancelledToday.length+')' : ''}
        </button>`;
        ordersDiv.insertBefore(btnWrap, ordersDiv.firstChild);

        // Cancelled section
        if (window._showCancelledInPaid && cancelledToday.length) {
            const sec = document.createElement('div');
            sec.id = 'cancelled-section';
            sec.style.cssText = 'margin-bottom:14px;';
            sec.innerHTML = cancelledToday.map(o => {
                const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
                return `<div class="order-row cancelled" style="margin-bottom:8px;opacity:0.7;">
                    <div class="order-row-top">
                        <div style="display:flex;gap:5px;align-items:center">
                            <span style="background:#e53935;color:white;padding:1px 7px;border-radius:5px;font-weight:700;font-size:0.8rem">#${o.id}</span>
                            <span class="badge cancelled">cancelled</span>
                            <span style="font-size:0.75rem;color:#bbb">Table ${o.table_no}</span>
                        </div>
                        <span style="font-size:0.72rem;color:#bbb">${(o.created_at||'').substring(11,16)}</span>
                    </div>
                    <div style="font-size:0.82rem;color:#aaa;margin:6px 0">${items.map(i=>`${i.name} ×${i.qty}`).join(', ')}</div>
                    <div class="order-row-foot"><span class="order-total-sm" style="color:#e53935">₹${o.total}</span></div>
                </div>`;
            }).join('');
            ordersDiv.insertBefore(sec, ordersDiv.children[1] || null);
        }
    }
}

async function markDelivered(orderId) {
    const res = await fetch(`/api/order/${orderId}/status`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'done' })
    });
    if (res.ok) {
        toast('✅ Delivered!');
        await loadOrders();
        loadTables();
    }
}

// ── TABLE MODAL ──
async function openModal(tableNo) {
    document.getElementById('modal-title').textContent = `Table ${tableNo}`;
    document.getElementById('modal-body').innerHTML = '<div style="text-align:center;padding:20px;color:#bbb"><i class="fas fa-spinner fa-spin"></i></div>';
    document.getElementById('modal-footer').innerHTML = '';
    document.getElementById('modal').classList.add('open');

    const [summaryRes, detailRes] = await Promise.all([
        fetch(`/api/tables/${clientId}/summary`),
        fetch(`/api/table/${clientId}/${tableNo}/detail`)
    ]);
    const summary = await summaryRes.json();
    const detail = await detailRes.json();

    const tInfo = summary.find(t => t.table_no === tableNo) || {};
    const ds = tInfo.display_status || 'inactive';
    const orders = detail.orders || [];
    const bills = detail.bills || [];

    let bodyHtml = '';
    const activeOrders = orders.filter(o => o.status !== 'cancelled');

    if (!activeOrders.length) {
        bodyHtml = '<div class="empty-state" style="padding:20px"><i class="fas fa-utensils"></i><p>Is session mein koi order nahi</p></div>';
    } else {
        const statusOrder = ['pending', 'preparing', 'ready', 'done'];
        const sorted = [...activeOrders].sort((a, b) =>
            statusOrder.indexOf(a.status) - statusOrder.indexOf(b.status)
        );

        bodyHtml = sorted.map(o => {
            const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
            const _rRaw2 = typeof o.ready_items === 'string'
                ? JSON.parse(o.ready_items || '[]')
                : (o.ready_items || []);
            const _rMap2 = {};
            _rRaw2.forEach(r => typeof r === 'string' ? (_rMap2[r] = Infinity) : (_rMap2[r.name] = r.qty));
            const statusEmoji = { pending: '⏳', preparing: '👨‍🍳', ready: '✅', done: '📦' }[o.status] || '';

            const itemsHtml = items.map(i => {
                const isReady = (_rMap2[i.name] || 0) > 0;
                return `<div class="waiter-item-row">
                    <span class="waiter-item-dot ${isReady ? 'dot-ready' : 'dot-pending'}"></span>
                    <span class="waiter-item-name ${isReady ? 'waiter-item-ready' : ''}">${i.name} ×${i.qty}</span>
                    ${isReady ? '<span class="waiter-item-tag">Ready</span>' : ''}
                </div>`;
            }).join('');

            return `<div class="order-row ${o.status}" style="margin-bottom:10px">
                <div class="order-row-top">
                    <div style="display:flex;gap:5px;align-items:center">
                        <span class="badge ${o.status}">${statusEmoji} ${o.status}</span>
                        <span class="badge staff">${o.source === 'waiter' ? 'staff' : o.source}</span>
                        ${Object.keys(_rMap2).length > 0 ? `<span class="ready-progress ${Object.keys(_rMap2).length === items.length ? 'rp-full' : 'rp-partial'}">${Object.keys(_rMap2).length}/${items.length} ready</span>` : ''}
                    </div>
                    <span style="font-size:0.72rem;color:#bbb">${(o.created_at || '').substring(11, 16)}</span>
                </div>
                <div class="waiter-items-list" style="margin:8px 0">${itemsHtml}</div>
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span class="order-total-sm">₹${o.total}</span>
                    ${o.status === 'ready'
                    ? `<button class="deliver-btn" onclick="markDelivered(${o.id});openModal(${tableNo})">✓ Delivered</button>`
                    : ''}
                </div>
            </div>`;
        }).join('');

        if (bills.length) {
            bodyHtml += `<div style="font-size:0.75rem;font-weight:600;color:#999;margin:14px 0 8px;text-transform:uppercase;letter-spacing:0.5px">Bill</div>`;
            bodyHtml += bills.map(b => `
                <div style="background:#fafafa;border-radius:10px;padding:12px;margin-bottom:8px;border:1px solid #eee;display:flex;justify-content:space-between;align-items:center">
                    <div>
                        <div style="font-weight:600;font-size:0.9rem">Bill #${b.id} — ₹${b.total}</div>
                        <div style="font-size:0.72rem;color:#aaa;margin-top:2px">${(b.created_at || '').substring(0, 16)}</div>
                    </div>
                    <span class="${b.payment_status === 'paid' ? 'bill-tag-paid' : 'bill-tag-unpaid'}">
                        ${b.payment_status === 'paid' ? '✅ PAID' : '⏳ UNPAID'}</span>
                </div>`).join('');
        }
    }
    document.getElementById('modal-body').innerHTML = bodyHtml;

    const footer = document.getElementById('modal-footer');

    if (ds === 'inactive') {
        footer.innerHTML = `<button class="submit-btn" onclick="activateTable(${tableNo})">✅ Activate Table</button>`;
    } else if (ds === 'active') {
        footer.innerHTML = `
            <button class="add-items-btn" onclick="openOrderOverlay(${tableNo})">
                <i class="fas fa-plus"></i> Add Items
            </button>
            <button class="cancel-btn" style="margin-top:8px" onclick="closeTable(${tableNo})">Close Table</button>`;
    } else if (ds === 'occupied' || ds === 'ready') {
        footer.innerHTML = `
            <button class="add-items-btn" onclick="openOrderOverlay(${tableNo})">
                <i class="fas fa-plus"></i> Add More Items
            </button>`;
    } else if (ds === 'done') {
        const doneTotal = activeOrders.reduce((s, o) => s + o.total, 0);
        footer.innerHTML = `
            <button class="submit-btn" onclick="closeModal(); openBillingSheet(${tableNo}, ${doneTotal})">
                🧾 Generate Bill — ₹${doneTotal}</button>
            <button class="add-items-btn" style="margin-top:8px" onclick="openOrderOverlay(${tableNo})">
                <i class="fas fa-plus"></i> Add More Items</button>`;
    } else if (ds === 'billed') {
        const unpaid = bills.find(b => b.payment_status === 'unpaid');
                    if (unpaid) {
                footer.innerHTML = `
                    <div class="form-group" style="margin-bottom:10px">
                        <label>Payment Mode</label>
                        <select id="modal-pay-mode" style="width:100%;padding:10px 12px;border:1.5px solid #eee;border-radius:10px;font-size:0.88rem;outline:none">
                            <option value="cash">💵 Cash</option>
                            <option value="upi">📱 UPI</option>
                            <option value="card">💳 Card</option>
                        </select>
                    </div>
                    <button class="pay-btn" onclick="markPaid(${unpaid.id}, ${tableNo})">
                        ✅ Mark as Paid — ₹${unpaid.total}</button>
                    <button class="add-items-btn" style="margin-top:8px" onclick="openOrderOverlay(${tableNo})">
                        <i class="fas fa-plus"></i> Add More Items</button>`;
            }
    } else if (ds === 'paid') {
        footer.innerHTML = `<button class="submit-btn" onclick="clearTable(${tableNo})">🔄 Clear & New Session</button>`;
    }
}

function closeModal() {
    document.getElementById('modal').classList.remove('open');
}

async function activateTable(tableNo) {
    await fetch(`/api/table/${clientId}/${tableNo}/activate`, { method: 'POST' });
    toast(`✅ Table ${tableNo} activated`);
    loadTables();
    openModal(tableNo); // Modal refresh ho jayega "Add Items" button ke saath
}

async function closeTable(tableNo) {
    if (!confirm(`Close Table ${tableNo}?`)) return;
    await fetch(`/api/table/${clientId}/${tableNo}/close`, { method: 'POST' });
    toast(`Table ${tableNo} closed`);
    closeModal(); loadTables();
}

async function clearTable(tableNo) {
    if (!confirm(`Clear Table ${tableNo} and mark as Active?`)) return;
    await fetch(`/api/table/${clientId}/${tableNo}/activate`, { method: 'POST' });
    toast(`✅ Table ${tableNo} cleared and active!`);
    closeModal();
    await loadTables();
}

async function markPaid(billId, tableNo) {
    const modeEl = document.getElementById('modal-pay-mode');
    const mode = modeEl ? modeEl.value : 'cash';
    const res = await fetch(`/api/bill/${billId}/pay`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_mode: mode })
    });
    if (res.ok) {
        toast('✅ Payment received!');
        closeModal();
        await loadTables();
        loadOrders();
    } else {
        const err = await res.json().catch(() => ({}));
        const errMsg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
        toast('❌ ' + (errMsg || 'Payment failed'));
    }
}

async function markPaidFromList(billId, tableNo) {
    const modeEl = document.getElementById(`pay-mode-${tableNo}`);
    const mode = modeEl ? modeEl.value : 'cash';
    const res = await fetch(`/api/bill/${billId}/pay`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_mode: mode })
    });
    if (res.ok) {
        toast(`✅ Table ${tableNo} — Payment received!`);
        await loadTables();
        loadOrders();
    } else {
        const err = await res.json().catch(() => ({}));
        toast('❌ ' + (err.detail || 'Payment failed'));
    }
}

// ── BILLING SHEET ──
function openBillingSheet(tableNo, estimatedTotal) {
    const sheet = document.createElement('div');
    sheet.id = 'bill-sheet';
    sheet.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:400;display:flex;align-items:flex-end';
    sheet.innerHTML = `
        <div style="background:white;width:100%;border-radius:24px 24px 0 0;padding:24px;max-height:85vh;overflow-y:auto">
            <div style="font-family:var(--font-primary);font-size:1.1rem;color:var(--secondary);margin-bottom:18px">
                Bill — Table ${tableNo}</div>
            <div class="bill-form-row">
                <div class="form-group">
                    <label>Customer Name</label>
                    <input type="text" id="bf-name" placeholder="Optional">
                </div>
                <div class="form-group">
                    <label>Phone</label>
                    <input type="tel" id="bf-phone" placeholder="Optional">
                </div>
            </div>
            <div class="bill-form-row">
                <div class="form-group">
                    <label>Tax %</label>
                    <input type="number" id="bf-tax" value="0" min="0">
                </div>
                <div class="form-group">
                    <label>Discount ₹</label>
                    <input type="number" id="bf-discount" value="0" min="0">
                </div>
            </div>
            <div class="form-group">
                <label>Payment Mode</label>
                <select id="bf-mode">
                    <option value="cash">Cash</option>
                    <option value="upi">UPI</option>
                    <option value="card">Card</option>
                </select>
            </div>
            <div id="bf-preview" style="display:none" class="bill-preview"></div>
            <div style="display:flex;flex-direction:column;gap:10px;margin-top:14px">
                <button id="bf-gen-btn" class="submit-btn" onclick="generateBill(${tableNo})">Generate Bill</button>
                <button id="bf-pay-btn" class="pay-btn" style="display:none" onclick="payBill(${tableNo})">✅ Mark as Paid</button>
                <button class="cancel-btn" onclick="document.getElementById('bill-sheet').remove()">Cancel</button>
            </div>
        </div>`;
    document.body.appendChild(sheet);
}

async function generateBill(tableNo) {
    const body = {
        customer_name: document.getElementById('bf-name').value || null,
        customer_phone: document.getElementById('bf-phone').value || null,
        tax_percent: parseFloat(document.getElementById('bf-tax').value) || 0,
        discount: parseInt(document.getElementById('bf-discount').value) || 0,
        payment_mode: document.getElementById('bf-mode').value
    };
    const res = await fetch(`/api/bill/${clientId}/${tableNo}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    if (!res.ok) {
        const err = await res.json();
        toast('❌ ' + (err.detail || 'Error')); return;
    }
    const bill = await res.json();
    pendingBillId = bill.bill_id;

    const orders = bill.orders || [];
    const itemLines = orders.flatMap(o => {
        const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
        return items.map(i => `<div class="bill-row"><span>${i.name} ×${i.qty}</span><span>₹${i.price * i.qty}</span></div>`);
    }).join('');

    const preview = document.getElementById('bf-preview');
    preview.style.display = 'block';
    preview.innerHTML = `
        ${bill.customer_name ? `<div class="bill-row"><span>Customer</span><span>${bill.customer_name}</span></div>` : ''}
        <div style="border-top:1px dashed #ddd;margin:8px 0"></div>
        ${itemLines}
        <div class="bill-row"><span>Subtotal</span><span>₹${bill.subtotal}</span></div>
        ${bill.tax ? `<div class="bill-row"><span>Tax</span><span>₹${bill.tax}</span></div>` : ''}
        ${bill.discount ? `<div class="bill-row"><span>Discount</span><span>−₹${bill.discount}</span></div>` : ''}
        <div class="bill-row total"><span>Total</span><span>₹${bill.total}</span></div>`;

    document.getElementById('bf-gen-btn').style.display = 'none';
    document.getElementById('bf-pay-btn').style.display = 'block';
    toast('✅ Bill generated!');
    loadTables();
}

async function payBill(tableNo) {
    if (!pendingBillId) return;
    const mode = document.getElementById('bf-mode').value;
    const res = await fetch(`/api/bill/${pendingBillId}/pay`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_mode: mode })
    });
    if (res.ok) {
        toast('✅ Payment received!');
        pendingBillId = null;
        document.getElementById('bill-sheet').remove();
        await loadTables();
        loadOrders();
    }
}

// ── ORDER OVERLAY ──
let overlayTableNo = null;
let ooActiveCat = 'all';
let ooSearchQuery = '';
const overlayCart = {}; // key: {name, label, price, qty, displayName}

function openOrderOverlay(tableNo) {
    overlayTableNo = tableNo;
    // Reset cart for new overlay open
    Object.keys(overlayCart).forEach(k => delete overlayCart[k]);
    ooActiveCat = 'all';
    ooSearchQuery = '';

    document.getElementById('order-overlay-title').textContent = `Table ${tableNo} — Add Items`;
    ooRenderCats();
    ooRenderItems();
    ooUpdateBar();

    // Close modal first, then open overlay
    closeModal();
    setTimeout(() => {
        document.getElementById('order-overlay').classList.add('open');
    }, 50);
}

function closeOrderOverlay() {
    document.getElementById('order-overlay').classList.remove('open');
    overlayTableNo = null;
    Object.keys(overlayCart).forEach(k => delete overlayCart[k]);
    // Reload tables after closing
    loadTables();
}

function ooRenderCats() {
    const cats = ['all'];
    menuItems.forEach(item => {
        if (!cats.includes(item.category)) cats.push(item.category);
    });
    document.getElementById('oo-cat-tabs').innerHTML = cats.map(c =>
        `<button class="wo-cat-tab ${c === ooActiveCat ? 'active' : ''}"
            onclick="ooSetCat('${c}')">${c === 'all' ? 'All' : c}</button>`
    ).join('');
}

function ooSetCat(cat) {
    ooActiveCat = cat;
    document.querySelectorAll('#oo-cat-tabs .wo-cat-tab').forEach(b => {
        b.classList.toggle('active', b.textContent === (cat === 'all' ? 'All' : cat));
    });
    ooRenderItems();
}

function ooOnSearch(val) {
    ooSearchQuery = val.trim().toLowerCase();
    document.getElementById('oo-search-clear').style.display = ooSearchQuery ? 'block' : 'none';
    ooRenderItems();
}

function ooClearSearch() {
    document.getElementById('oo-search').value = '';
    ooSearchQuery = '';
    document.getElementById('oo-search-clear').style.display = 'none';
    ooRenderItems();
}

function ooGetKey(name, label) {
    return label ? name + '||' + label : name;
}

function ooRenderItems() {
    const wrap = document.getElementById('oo-items-wrap');
    if (!wrap) return;

    let items = menuItems;
    if (ooActiveCat !== 'all') items = items.filter(i => i.category === ooActiveCat);
    if (ooSearchQuery) items = items.filter(i => i.name.toLowerCase().includes(ooSearchQuery));

    if (!items.length) {
        wrap.innerHTML = `<div class="wo-empty">No items found</div>`;
        return;
    }

    wrap.innerHTML = items.map(item => {
        const hasSizes = item.sizes && item.sizes.length;
        if (hasSizes) {
            const sizeRows = item.sizes.map(s => {
                const key = ooGetKey(item.name, s.label);
                const qty = overlayCart[key] ? overlayCart[key].qty : 0;
                return `<div class="wo-size-row">
                    <div class="wo-size-info">
                        <span class="wo-size-lbl">${s.label}</span>
                        <span class="wo-size-price">₹${parsePrice(s.price)}</span>
                    </div>
                    <div class="wo-qty-ctrl" id="oqc-${CSS.escape(key)}">
                        ${ooCtrlHtml(item.name, s.label, s.price, qty)}
                    </div>
                </div>`;
            }).join('');
            return `<div class="wo-item-card">
                <div class="wo-item-head">
                    <div class="wo-veg-dot ${item.veg ? 'veg' : 'nonveg'}"></div>
                    <div class="wo-item-name">${item.name}</div>
                </div>
                <div class="wo-sizes-list">${sizeRows}</div>
            </div>`;
        } else {
            const key = ooGetKey(item.name, '');
            const qty = overlayCart[key] ? overlayCart[key].qty : 0;
            return `<div class="wo-item-card">
                <div class="wo-item-row">
                    <div class="wo-item-left">
                        <div class="wo-veg-dot ${item.veg ? 'veg' : 'nonveg'}"></div>
                        <div class="wo-item-name">${item.name}</div>
                    </div>
                    <div class="wo-item-right">
                        <span class="wo-item-price">₹${parsePrice(item.price)}</span>
                        <div class="wo-qty-ctrl" id="oqc-${CSS.escape(key)}">
                            ${ooCtrlHtml(item.name, '', item.price, qty)}
                        </div>
                    </div>
                </div>
            </div>`;
        }
    }).join('');
}

function ooCtrlHtml(name, label, price, qty) {
    const eName = name.replace(/"/g, '&quot;');
    const eLabel = label.replace(/"/g, '&quot;');
    const ePrice = String(price).replace(/"/g, '&quot;');
    if (qty <= 0) {
        return `<button class="wo-add-btn" onclick="ooAdd('${eName}','${eLabel}','${ePrice}')">+</button>`;
    }
    return `
        <button class="qty-btn wo-minus" onclick="ooRemove('${eName}','${eLabel}','${ePrice}')">−</button>
        <span class="qty-num">${qty}</span>
        <button class="qty-btn wo-plus" onclick="ooAdd('${eName}','${eLabel}','${ePrice}')">+</button>`;
}

function ooUpdateCtrl(name, label, price) {
    const key = ooGetKey(name, label);
    const qty = overlayCart[key] ? overlayCart[key].qty : 0;
    const el = document.getElementById('oqc-' + CSS.escape(key));
    if (el) el.innerHTML = ooCtrlHtml(name, label, price, qty);
}

function ooAdd(name, label, price) {
    const key = ooGetKey(name, label);
    const displayName = label ? name + ' (' + label + ')' : name;
    if (overlayCart[key]) overlayCart[key].qty++;
    else overlayCart[key] = { name, label, price, qty: 1, displayName };
    ooUpdateCtrl(name, label, price);
    ooUpdateBar();
}

function ooRemove(name, label, price) {
    const key = ooGetKey(name, label);
    if (!overlayCart[key]) return;
    overlayCart[key].qty--;
    if (overlayCart[key].qty <= 0) delete overlayCart[key];
    ooUpdateCtrl(name, label, price);
    ooUpdateBar();
}

function ooUpdateBar() {
    const entries = Object.values(overlayCart);
    const totalQty = entries.reduce((s, e) => s + e.qty, 0);
    const totalPrice = entries.reduce((s, e) => s + parsePrice(e.price) * e.qty, 0);
    const bar = document.getElementById('oo-float-bar');
    const badge = document.getElementById('oo-cart-badge');
    if (!bar) return;

    if (totalQty === 0) {
        bar.style.display = 'none';
        if (badge) badge.style.display = 'none';
    } else {
        bar.style.display = 'flex';
        document.getElementById('oo-bar-count').textContent = totalQty + ' item' + (totalQty > 1 ? 's' : '');
        document.getElementById('oo-bar-total').textContent = '₹' + totalPrice;
        if (badge) { badge.style.display = 'block'; badge.textContent = totalQty + ' items — ₹' + totalPrice; }
    }
}

async function placeOrderFromOverlay() {
    if (!overlayTableNo) { toast('Table number missing'); return; }
    const entries = Object.values(overlayCart);
    if (!entries.length) { toast('Koi item select karo'); return; }

    const items = entries.map(e => ({
        name: e.displayName,
        qty: e.qty,
        price: parsePrice(e.price)
    }));
    const total = items.reduce((s, i) => s + i.qty * i.price, 0);

    const res = await fetch(`/api/order/${clientId}/${overlayTableNo}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items, total, source: 'Staff' })
    });
    if (res.ok) {
        toast('✅ Order placed!');
        document.getElementById('order-overlay').classList.remove('open');
        overlayTableNo = null;
        Object.keys(overlayCart).forEach(k => delete overlayCart[k]);
        loadTables();
    } else {
        const err = await res.json();
        toast('❌ ' + (err.detail || 'Error'));
    }
}

// ── PLACE ORDER (old tab functions — kept as stubs, no longer used directly) ──
const waiterCart = {};
let woActiveCat = 'all';
let woSearchQuery = '';

function renderMenu() {}
function placeOrder() {}

// ── HELPERS ──
function parsePrice(p) { return parseInt(String(p).replace(/[^0-9]/g, '')) || 0; }

function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// Init + auto-refresh
loadTables();
setInterval(loadTables, 15000);
setInterval(() => {
    if (document.getElementById('tab-orders').style.display !== 'none') loadOrders();
}, 15000);

// ── ORDER EDIT ──
let editOrderId = null;
let editOrderData = null;

async function openEditOrder(orderId) {
    const allRes = await fetch(`/api/orders/${clientId}`);
    const all = await allRes.json();
    const order = all.find(o => o.id === orderId);
    if (!order) return;

    editOrderId = orderId;
    const items = typeof order.items === 'string' ? JSON.parse(order.items) : order.items;
    const readyList = typeof order.ready_items === 'string'
        ? JSON.parse(order.ready_items || '[]')
        : (order.ready_items || []);

    // readyList: [{name,qty}] ya legacy List[str]
    const readyQtyMap = {};
    readyList.forEach(r => {
        if (typeof r === 'string') readyQtyMap[r] = (items.find(i => i.name === r) || {}).qty || 1;
        else readyQtyMap[r.name] = r.qty;
    });

    editOrderData = items.map(i => ({
        ...i,
        _readyQty: readyQtyMap[i.name] || 0,
        _originalQty: i.qty
    }));

    document.getElementById('edit-modal-title').textContent = `Edit Order #${orderId} — Table ${order.table_no}`;
    renderEditItems();
    document.getElementById('edit-modal').style.display = 'block';
}

function renderEditItems() {
    const wrap = document.getElementById('edit-modal-items');
    wrap.innerHTML = editOrderData.map((item, idx) => {
        const canDecrease = item.qty > item._readyQty;
        const delta = item.qty - item._originalQty;
        const deltaHtml = delta > 0
            ? `<span style="color:#4caf50;font-size:0.72rem;margin-left:4px">+${delta} added</span>`
            : delta < 0
            ? `<span style="color:#e53935;font-size:0.72rem;margin-left:4px">${delta} removed</span>`
            : '';

        return `<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f5f5f5;">
            <div>
                <div style="display:flex;align-items:center;gap:4px;">
                    <span style="font-size:0.9rem;font-weight:600;color:var(--secondary)">${item.name}</span>
                    ${deltaHtml}
                </div>
                <div style="font-size:0.75rem;color:#aaa;margin-top:2px">
                    ₹${item.price} each
                    ${item._readyQty > 0 ? `<span style="color:#4caf50;margin-left:6px">✓ ${item._readyQty} ready</span>` : ''}
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;">
                <button onclick="editQty(${idx},-1)" ${!canDecrease ? 'disabled' : ''}
                    style="width:28px;height:28px;border-radius:50%;
                    border:1.5px solid ${canDecrease ? 'var(--primary)' : '#ddd'};
                    background:${canDecrease ? 'transparent' : '#f5f5f5'};
                    color:${canDecrease ? 'var(--primary)' : '#ccc'};
                    cursor:${canDecrease ? 'pointer' : 'not-allowed'};
                    font-size:1rem;opacity:${canDecrease ? '1' : '0.4'}">−</button>
                <span style="font-weight:700;min-width:20px;text-align:center">${item.qty}</span>
                <button onclick="editQty(${idx},1)"
                    style="width:28px;height:28px;border-radius:50%;border:none;
                    background:var(--primary);color:var(--secondary);cursor:pointer;font-size:1rem;">+</button>
            </div>
        </div>`;
    }).join('');
}

function editQty(idx, delta) {
    const item = editOrderData[idx];
    const newQty = item.qty + delta;
    if (newQty < item._readyQty) return;
    if (newQty < 0) return;
    item.qty = newQty;
    renderEditItems();
}

async function cancelOrderDirect() {
    if (!editOrderId) return;
    if (!confirm('Poora order cancel kar dein?')) return;

    const res = await fetch(`/api/order/${editOrderId}/items`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [] })  // saari items 0 — backend cancel karega
    });

    if (res.ok) {
        closeEditModal();
        toast('🚫 Order cancelled');
        loadOrders();
        loadTables();
    } else {
        const err = await res.json();
        toast('❌ ' + (err.detail || 'Error'));
    }
}

async function saveOrderEdit() {
    if (!editOrderId) return;

    const items = editOrderData.map(i => ({
        name: i.name, qty: i.qty, price: i.price
    }));

    const res = await fetch(`/api/order/${editOrderId}/items`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
    });

    if (res.ok) {
        const data = await res.json();
        closeEditModal();
        toast(data.message.includes('cancelled') ? '🚫 Order cancelled' : '✅ Order updated');
        loadOrders();
        loadTables();
    } else {
        const err = await res.json();
        toast('❌ ' + (err.detail || 'Error'));
    }
}

function closeEditModal() {
    document.getElementById('edit-modal').style.display = 'none';
    editOrderId   = null;
    editOrderData = null;
}

// Cancelled toggle in Paid Today section
function toggleCancelledSection() {
    window._showCancelledInPaid = !window._showCancelledInPaid;
    loadOrders();
}
