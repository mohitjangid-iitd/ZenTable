// clientId, menuItems, waiterQtys, pendingBillId — HTML template mein inject hote hain

// ── TABS ──
function switchTab(tab, btn) {
    ['tables', 'orders', 'place'].forEach(t => {
        document.getElementById(`tab-${t}`).style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (tab === 'tables') loadTables();
    if (tab === 'orders') loadOrders();
    if (tab === 'place') renderMenu();
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
    loadOrders();
}

async function loadOrders() {
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

        html += `<div class="table-group">
            <div class="table-group-head">
                <div class="table-group-title">Table ${tableNo}</div>
                ${rightEl}
            </div>
            <div class="table-group-body">
            ${orders.map(o => {
            const items = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
            const readyItems = typeof o.ready_items === 'string'
                ? JSON.parse(o.ready_items || '[]')
                : (o.ready_items || []);
            const canDeliver = o.status === 'ready';

            // Item-wise ready status — active aur ready filter mein dikhao
            let itemsHtml = '';
            if (currentFilter === 'active' || currentFilter === 'ready') {
                itemsHtml = items.map(i => {
                    const isReady = readyItems.includes(i.name);
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

            // Ready progress badge for active filter
            const progressBadge = (currentFilter === 'active' && readyItems.length > 0)
                ? `<span class="ready-progress ${readyItems.length === items.length ? 'rp-full' : 'rp-partial'}">
                        ${readyItems.length}/${items.length} ready</span>`
                : '';

            return `<div class="order-row ${o.status}">
                    <div class="order-row-top">
                        <div style="display:flex;gap:5px;align-items:center">
                            <span class="badge ${o.status}">${o.status}</span>
                            <span class="badge staff">${o.source === 'waiter' ? 'staff' : o.source}</span>
                            ${progressBadge}
                        </div>
                        <span style="font-size:0.72rem;color:#bbb">${(o.created_at || '').substring(11, 16)}</span>
                    </div>
                    <div class="waiter-items-list">${itemsHtml}</div>
                    <div class="order-row-foot">
                        <span class="order-total-sm">₹${o.total}</span>
                        ${canDeliver
                    ? `<button class="deliver-btn" onclick="markDelivered(${o.id})">✓ Delivered</button>`
                    : ''}
                    </div>
                </div>`;
        }).join('')}
            </div>
        </div>`;
    }
    list.innerHTML = html;
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
            const readyItems = typeof o.ready_items === 'string'
                ? JSON.parse(o.ready_items || '[]')
                : (o.ready_items || []);
            const statusEmoji = { pending: '⏳', preparing: '👨‍🍳', ready: '✅', done: '📦' }[o.status] || '';

            const itemsHtml = items.map(i => {
                const isReady = readyItems.includes(i.name);
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
                        ${readyItems.length > 0 ? `<span class="ready-progress ${readyItems.length === items.length ? 'rp-full' : 'rp-partial'}">${readyItems.length}/${items.length} ready</span>` : ''}
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
        footer.innerHTML = `<button class="cancel-btn" onclick="closeTable(${tableNo})">Close Table</button>`;
    } else if (ds === 'occupied' || ds === 'ready') {
        const readyCount = activeOrders.filter(o => o.status === 'ready').length;
        if (readyCount > 0) {
            footer.innerHTML = `<div style="text-align:center;font-size:0.85rem;color:#2e7d32;font-weight:600">
                ${readyCount} order${readyCount > 1 ? 's' : ''} ready to serve! ✅</div>`;
        } else {
            footer.innerHTML = `<div style="text-align:center;font-size:0.82rem;color:#999">Kitchen mein hai... wait karo</div>`;
        }
    } else if (ds === 'done') {
        const doneTotal = activeOrders.reduce((s, o) => s + o.total, 0);
        footer.innerHTML = `<button class="submit-btn" onclick="closeModal(); openBillingSheet(${tableNo}, ${doneTotal})">
            🧾 Generate Bill — ₹${doneTotal}</button>`;
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
                    ✅ Mark as Paid — ₹${unpaid.total}</button>`;
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
    closeModal(); loadTables();
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

// ── PLACE ORDER ──
// waiterCart: { key: { name, label, price, qty } }
// key = "ItemName" (no size) or "ItemName||SizeLabel" (sized)
const waiterCart = {};
let woActiveCat = 'all';
let woSearchQuery = '';

function renderMenu() {
    const wrap = document.getElementById('menu-items-list');

    // Build categories
    const cats = ['all'];
    menuItems.forEach(item => {
        if (!cats.includes(item.category)) cats.push(item.category);
    });

    wrap.innerHTML = `
        <!-- Table input -->
        <div class="wo-table-row">
            <label>Table No.</label>
            <input type="number" id="wo-table" placeholder="e.g. 2" min="1">
        </div>

        <!-- Search -->
        <div class="wo-search-wrap">
            <i class="fas fa-search wo-search-icon"></i>
            <input type="text" id="wo-search" placeholder="Search dishes..." oninput="woOnSearch(this.value)">
            <button class="wo-search-clear" id="wo-search-clear" onclick="woClearSearch()" style="display:none">✕</button>
        </div>

        <!-- Category tabs -->
        <div class="wo-cat-tabs" id="wo-cat-tabs">
            ${cats.map(c => `
                <button class="wo-cat-tab ${c === woActiveCat ? 'active' : ''}"
                    onclick="woSetCat('${c}')">${c === 'all' ? 'All' : c}</button>
            `).join('')}
        </div>

        <!-- Items list -->
        <div id="wo-items-wrap"></div>

        <!-- Spacer for floating bar -->
        <div style="height:80px"></div>
    `;

    woRenderItems();
    woUpdateBar();
}

function woGetKey(name, label) {
    return label ? name + '||' + label : name;
}

function woOnSearch(val) {
    woSearchQuery = val.trim().toLowerCase();
    document.getElementById('wo-search-clear').style.display = woSearchQuery ? 'block' : 'none';
    woRenderItems();
}

function woClearSearch() {
    document.getElementById('wo-search').value = '';
    woSearchQuery = '';
    document.getElementById('wo-search-clear').style.display = 'none';
    woRenderItems();
}

function woSetCat(cat) {
    woActiveCat = cat;
    document.querySelectorAll('.wo-cat-tab').forEach(b => {
        b.classList.toggle('active', b.textContent === (cat === 'all' ? 'All' : cat));
    });
    woRenderItems();
}

function woRenderItems() {
    const wrap = document.getElementById('wo-items-wrap');
    if (!wrap) return;

    let items = menuItems;

    // Category filter
    if (woActiveCat !== 'all') {
        items = items.filter(i => i.category === woActiveCat);
    }

    // Search filter
    if (woSearchQuery) {
        items = items.filter(i => i.name.toLowerCase().includes(woSearchQuery));
    }

    if (!items.length) {
        wrap.innerHTML = `<div class="wo-empty">No items found</div>`;
        return;
    }

    wrap.innerHTML = items.map(item => {
        const hasSizes = item.sizes && item.sizes.length;
        if (hasSizes) {
            // Sized item — show each size as a row
            const sizeRows = item.sizes.map(s => {
                const key = woGetKey(item.name, s.label);
                const qty = waiterCart[key] ? waiterCart[key].qty : 0;
                return `
                <div class="wo-size-row">
                    <div class="wo-size-info">
                        <span class="wo-size-lbl">${s.label}</span>
                        <span class="wo-size-price">₹${parsePrice(s.price)}</span>
                    </div>
                    <div class="wo-qty-ctrl" id="wqc-${CSS.escape(key)}">
                        ${woCtrlHtml(item.name, s.label, s.price, qty)}
                    </div>
                </div>`;
            }).join('');

            return `
            <div class="wo-item-card">
                <div class="wo-item-head">
                    <div class="wo-veg-dot ${item.veg ? 'veg' : 'nonveg'}"></div>
                    <div class="wo-item-name">${item.name}</div>
                </div>
                <div class="wo-sizes-list">${sizeRows}</div>
            </div>`;
        } else {
            // Single price item
            const key = woGetKey(item.name, '');
            const qty = waiterCart[key] ? waiterCart[key].qty : 0;
            return `
            <div class="wo-item-card">
                <div class="wo-item-row">
                    <div class="wo-item-left">
                        <div class="wo-veg-dot ${item.veg ? 'veg' : 'nonveg'}"></div>
                        <div class="wo-item-name">${item.name}</div>
                    </div>
                    <div class="wo-item-right">
                        <span class="wo-item-price">₹${parsePrice(item.price)}</span>
                        <div class="wo-qty-ctrl" id="wqc-${CSS.escape(key)}">
                            ${woCtrlHtml(item.name, '', item.price, qty)}
                        </div>
                    </div>
                </div>
            </div>`;
        }
    }).join('');
}

function woCtrlHtml(name, label, price, qty) {
    const eName = name.replace(/"/g, '&quot;');
    const eLabel = label.replace(/"/g, '&quot;');
    const ePrice = String(price).replace(/"/g, '&quot;');
    if (qty <= 0) {
        return `<button class="wo-add-btn" onclick="woAdd('${eName}','${eLabel}','${ePrice}')">+</button>`;
    }
    return `
        <button class="qty-btn wo-minus" onclick="woRemove('${eName}','${eLabel}','${ePrice}')">−</button>
        <span class="qty-num">${qty}</span>
        <button class="qty-btn wo-plus" onclick="woAdd('${eName}','${eLabel}','${ePrice}')">+</button>`;
}

function woUpdateCtrl(name, label, price) {
    const key = woGetKey(name, label);
    const qty = waiterCart[key] ? waiterCart[key].qty : 0;
    const el = document.getElementById('wqc-' + CSS.escape(key));
    if (el) el.innerHTML = woCtrlHtml(name, label, price, qty);
}

function woAdd(name, label, price) {
    const key = woGetKey(name, label);
    const displayName = label ? name + ' (' + label + ')' : name;
    if (waiterCart[key]) {
        waiterCart[key].qty++;
    } else {
        waiterCart[key] = { name, label, price, qty: 1, displayName };
    }
    woUpdateCtrl(name, label, price);
    woUpdateBar();
}

function woRemove(name, label, price) {
    const key = woGetKey(name, label);
    if (!waiterCart[key]) return;
    waiterCart[key].qty--;
    if (waiterCart[key].qty <= 0) delete waiterCart[key];
    woUpdateCtrl(name, label, price);
    woUpdateBar();
}

function woUpdateBar() {
    const entries = Object.values(waiterCart);
    const totalQty = entries.reduce((s, e) => s + e.qty, 0);
    const totalPrice = entries.reduce((s, e) => s + parsePrice(e.price) * e.qty, 0);

    let bar = document.getElementById('wo-float-bar');
    if (!bar) return;

    if (totalQty === 0) {
        bar.style.display = 'none';
    } else {
        bar.style.display = 'flex';
        bar.querySelector('.wo-bar-count').textContent = totalQty + ' item' + (totalQty > 1 ? 's' : '');
        bar.querySelector('.wo-bar-total').textContent = '₹' + totalPrice;
    }
}

async function placeOrder() {
    const tableNo = parseInt(document.getElementById('wo-table').value);
    if (!tableNo) { toast('Table number bharo'); return; }

    const entries = Object.values(waiterCart);
    if (!entries.length) { toast('Koi item select karo'); return; }

    const items = entries.map(e => ({
        name: e.displayName,
        qty: e.qty,
        price: parsePrice(e.price)
    }));
    const total = items.reduce((s, i) => s + i.qty * i.price, 0);

    const res = await fetch(`/api/order/${clientId}/${tableNo}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items, total, source: 'Staff' })
    });
    if (res.ok) {
        toast('✅ Order placed!');
        // Cart reset
        Object.keys(waiterCart).forEach(k => delete waiterCart[k]);
        woSearchQuery = '';
        woActiveCat = 'all';
        document.getElementById('wo-table').value = '';
        renderMenu();
        loadTables();
    } else {
        const err = await res.json();
        toast('❌ ' + (err.detail || 'Error'));
    }
}

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
