// clientId, numTables — HTML se inject hote hain

let currentTab = 'billing';

function switchTab(tab, btn) {
    ['billing', 'tables'].forEach(t => {
        document.getElementById(`tab-${t}`).style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentTab = tab;
    if (tab === 'billing') loadBilling();
    if (tab === 'tables')  loadTables();
}

function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// ── BILLING ──
async function loadBilling() {
    const list = document.getElementById('billing-list');
    try {
        const summary = await fetch(`/api/tables/${clientId}/summary?branch_id=${branchId}`).then(r => r.json());
        const billed = summary.filter(t => t.display_status === 'billed' && t.bill_id);

        if (!billed.length) {
            list.innerHTML = `<div class="empty-state">
                <i class="fas fa-check-circle" style="color:#4caf50"></i>
                <p>Koi pending bill nahi!</p>
            </div>`;
            return;
        }

        const billDetails = await Promise.all(
            billed.map(t => fetch(`/api/bill/${t.bill_id}`).then(r => r.json()))
        );

        list.innerHTML = billed.map((t, i) => {
            const bill = billDetails[i];
            const orderCount = Array.isArray(bill.order_ids) ? bill.order_ids.length : 1;
            const time = (bill.created_at || '').substring(0, 16);
            const hasTaxDiscount = bill.subtotal !== bill.total;

            return `<div class="bill-card">
                <div class="bill-top">
                    <div>
                        <div class="bill-table">Table ${t.table_no}</div>
                        <div class="bill-time">Bill generated: ${time}</div>
                    </div>
                    <div class="bill-time">${orderCount} order${orderCount !== 1 ? 's' : ''}</div>
                </div>
                ${hasTaxDiscount ? `<div class="bill-items">Subtotal: Rs.${bill.subtotal} &nbsp;·&nbsp; Tax: Rs.${bill.tax} &nbsp;·&nbsp; Discount: Rs.${bill.discount}</div>` : ''}
                <div class="bill-footer">
                    <div class="bill-total">Rs.${bill.total}</div>
                    <select class="pay-select" id="pay-mode-${t.table_no}">
                        <option value="cash">Cash</option>
                        <option value="upi">UPI</option>
                        <option value="card">Card</option>
                    </select>
                    <button class="pay-btn" id="pay-btn-${bill.id}"
                        onclick="markPaid(${bill.id}, ${t.table_no})">
                        Mark Paid
                    </button>
                </div>
            </div>`;
        }).join('');

    } catch(e) {
        list.innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-circle"></i><p>Load failed</p></div>`;
    }
}

async function markPaid(billId, tableNo) {
    const btn = document.getElementById(`pay-btn-${billId}`);
    const mode = document.getElementById(`pay-mode-${tableNo}`)?.value || 'cash';
    if (btn) btn.disabled = true;

    const res = await fetch(`/api/bill/${billId}/pay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_mode: mode })
    });

    if (res.ok) {
        toast('Payment received! Table ' + tableNo + ' (' + mode + ')');
        loadBilling();
    } else {
        const err = await res.json().catch(() => ({}));
        toast('Failed: ' + (err.detail || 'Payment failed'));
        if (btn) btn.disabled = false;
    }
}

// ── TABLES ──
async function loadTables() {
    const grid = document.getElementById('tables-grid');
    try {
        const summary = await fetch(`/api/tables/${clientId}/summary?branch_id=${branchId}`).then(r => r.json());
        const map = {};
        summary.forEach(t => map[t.table_no] = t);

        const labels = {
            inactive: 'Inactive', active: 'Active', occupied: 'Occupied',
            ready: 'Ready', done: 'Done', billed: 'Billed', paid: 'Paid'
        };

        grid.innerHTML = Array.from({ length: numTables }, (_, i) => {
            const n = i + 1;
            const t = map[n];
            const ds = t ? t.display_status : 'inactive';
            const canActivate = ds === 'inactive';
            const canClose = ['active', 'paid'].includes(ds);
            const actionBtns = (canActivate || canClose) ? `
                <div class="table-actions">
                    ${canActivate ? `<button class="tbl-btn activate" onclick="activateTable(${n})">Activate</button>` : ''}
                    ${canClose    ? `<button class="tbl-btn close"    onclick="closeTable(${n})">Close</button>` : ''}
                </div>` : '';

            return `<div class="table-box ${ds}">
                <div class="table-num">T${n}</div>
                <div class="table-status">${labels[ds] || ds}</div>
                ${t && t.order_count ? `<div style="font-size:0.72rem;color:#999">${t.order_count} orders</div>` : ''}
                ${actionBtns}
            </div>`;
        }).join('');

    } catch(e) {
        grid.innerHTML = `<div style="grid-column:span 3;text-align:center;padding:30px;color:#bbb">Load failed</div>`;
    }
}

async function activateTable(tableNo) {
    const res = await fetch(`/api/table/${clientId}/${tableNo}/activate?branch_id=${branchId}`, { method: 'POST' });
    if (res.ok) { toast('Table ' + tableNo + ' activated'); loadTables(); }
    else toast('Failed');
}

async function closeTable(tableNo) {
    const res = await fetch(`/api/table/${clientId}/${tableNo}/close?branch_id=${branchId}`, { method: 'POST' });
    if (res.ok) { toast('Table ' + tableNo + ' closed'); loadTables(); }
    else toast('Failed');
}

async function activateAll() {
    const res = await fetch(`/api/table/${clientId}/activate-all?branch_id=${branchId}`, { method: 'POST' });
    if (res.ok) { toast('Saari tables activate ho gayi!'); loadTables(); }
    else toast('Failed');
}

async function closeAll() {
    if (!confirm('Saari tables close karna chahte ho?')) return;
    const res = await fetch(`/api/table/${clientId}/close-all?branch_id=${branchId}`, { method: 'POST' });
    if (res.ok) { toast('Saari tables band ho gayi'); loadTables(); }
    else toast('Failed');
}

loadBilling();
setInterval(() => {
    if (currentTab === 'billing') loadBilling();
    else loadTables();
}, 20000);
