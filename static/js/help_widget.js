/* ═══════════════════════════════════════════════════════════
   help_widget.js — ZenTable Landing Page Help Widget
   Endpoint : POST /api/help-chat
   Response : { response: "..." }
   No auth required. IP rate limited server-side.
   Self-contained — no external deps. Styles from chatbot.css.
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── CONFIG ─────────────────────────────────────────────
    const API_URL = '/api/help-chat';

    const SUGGESTIONS = [
        'AR menu kya hai? 🍽️',
        'Pricing kya hai?',
        'Staff kaise manage karein?',
        'ZenTable kaise setup karein?',
    ];

    const WELCOME_MSG =
        'Namaste! 👋 Main ZenTable ka AI assistant hoon.\n' +
        'Platform ke baare mein kuch bhi poochho — features, pricing, setup — sab bata sakta hoon!';

    // ── STATE ──────────────────────────────────────────────
    let _open       = false;
    let _isLoading  = false;
    let _initialized = false;
    let _msgCount   = 0;

    // ── MOUNT ──────────────────────────────────────────────
    // DOM ready pe inject karo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _mount);
    } else {
        _mount();
    }

    function _mount() {
        // FAB button
        const fab = document.createElement('button');
        fab.className  = 'help-widget-fab';
        fab.id         = 'hw-fab';
        fab.setAttribute('aria-label', 'Help chat kholo');
        fab.innerHTML  = `<span id="hw-fab-icon">💬</span><span class="fab-badge" id="hw-badge">1</span>`;
        fab.onclick    = toggleWidget;

        // Widget panel
        const panel = document.createElement('div');
        panel.className = 'help-widget-panel';
        panel.id        = 'hw-panel';
        panel.innerHTML = `
            <div class="hw-header">
                <div class="hw-header-avatar">🤖</div>
                <div class="hw-header-info">
                    <div class="hw-header-name">ZenTable AI</div>
                    <div class="hw-header-sub">Platform ke baare mein poochho</div>
                </div>
                <button class="hw-close-btn" onclick="window._hwClose()" aria-label="Band karo">✕</button>
            </div>

            <div class="hw-messages" id="hw-messages"></div>

            <div class="hw-suggestions" id="hw-suggestions"></div>

            <div class="hw-input-row">
                <input
                    class="hw-input"
                    id="hw-input"
                    type="text"
                    placeholder="Kuch poochho..."
                    maxlength="400"
                    autocomplete="off"
                />
                <button class="hw-send-btn" id="hw-send-btn" onclick="window._hwSend()" aria-label="Bhejo">➤</button>
            </div>`;

        document.body.appendChild(fab);
        document.body.appendChild(panel);

        // Show badge after 3s to draw attention
        setTimeout(() => {
            const badge = document.getElementById('hw-badge');
            if (badge && !_open) badge.classList.add('show');
        }, 3000);
    }

    // ── TOGGLE ─────────────────────────────────────────────
    window.toggleWidget = function () {
        _open ? _closeWidget() : _openWidget();
    };

    window._hwClose = function () { _closeWidget(); };

    function _openWidget() {
        _open = true;
        const panel = document.getElementById('hw-panel');
        const fab   = document.getElementById('hw-fab');
        const badge = document.getElementById('hw-badge');

        if (panel) panel.classList.add('open');
        if (badge) badge.classList.remove('show');
        if (fab)   document.getElementById('hw-fab-icon').textContent = '✕';

        if (!_initialized) _initWidget();

        // Focus input
        setTimeout(() => {
            const input = document.getElementById('hw-input');
            if (input) input.focus();
        }, 260);
    }

    function _closeWidget() {
        _open = false;
        const panel = document.getElementById('hw-panel');
        const fabIcon = document.getElementById('hw-fab-icon');
        if (panel)   panel.classList.remove('open');
        if (fabIcon) fabIcon.textContent = '💬';
    }

    // ── INIT (first open) ──────────────────────────────────
    function _initWidget() {
        _initialized = true;

        _renderSuggestions();
        _appendAiMsg(WELCOME_MSG);

        // Enter to send
        const input = document.getElementById('hw-input');
        if (input) {
            input.addEventListener('keydown', e => {
                if (e.key === 'Enter') { e.preventDefault(); _hwSend(); }
            });
        }
    }

    // ── SUGGESTIONS ────────────────────────────────────────
    function _renderSuggestions() {
        const box = document.getElementById('hw-suggestions');
        if (!box) return;
        box.innerHTML = SUGGESTIONS.map(s =>
            `<button class="hw-chip" onclick="window._hwChip('${s.replace(/'/g,"\\'")}')">
                ${_escHtml(s)}
             </button>`
        ).join('');
    }

    window._hwChip = function (text) {
        const input = document.getElementById('hw-input');
        if (input) input.value = text;
        _hwSend();
    };

    // ── SEND ───────────────────────────────────────────────
    window._hwSend = async function () {
        if (_isLoading) return;

        const input = document.getElementById('hw-input');
        if (!input) return;

        const text = input.value.trim();
        if (!text) return;

        input.value = '';

        // Hide suggestions after first message
        const sugBox = document.getElementById('hw-suggestions');
        if (sugBox) sugBox.style.display = 'none';

        _appendUserMsg(text);
        const typingId = _appendTyping();
        _setLoading(true);

        try {
            const res = await fetch(API_URL, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ message: text }),
            });

            _removeTyping(typingId);

            if (res.status === 429) {
                _appendAiMsg('Bahut zyada messages! Thodi der baad try karo. ⏳');
                return;
            }

            if (!res.ok) {
                _appendAiMsg('Kuch galat ho gaya. Dobara try karo ya humse contact karo. 🙏');
                return;
            }

            const data = await res.json();
            _appendAiMsg(data.response);

        } catch (_e) {
            _removeTyping(typingId);
            _appendAiMsg('Network error. Internet check karo. 📡');
        } finally {
            _setLoading(false);
        }
    };

    // ── DOM HELPERS ────────────────────────────────────────
    function _appendUserMsg(text) {
        const el = document.createElement('div');
        el.className = 'hw-msg hw-user';
        el.innerHTML = `
            <div class="hw-avatar">👤</div>
            <div class="hw-bubble">${_escHtml(text)}</div>`;
        _addToFeed(el);
        _msgCount++;
    }

    function _appendAiMsg(text) {
        const el = document.createElement('div');
        el.className = 'hw-msg hw-ai';
        el.innerHTML = `
            <div class="hw-avatar">🤖</div>
            <div class="hw-bubble">${_escHtml(text)}</div>`;
        _addToFeed(el);
        _msgCount++;
    }

    function _appendTyping() {
        const id = 'hw-typing-' + Date.now();
        const el = document.createElement('div');
        el.className = 'hw-msg hw-ai';
        el.id = id;
        el.innerHTML = `
            <div class="hw-avatar">🤖</div>
            <div class="hw-bubble" style="display:flex;align-items:center;gap:5px;padding:10px 14px;">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>`;
        _addToFeed(el);
        return id;
    }

    function _removeTyping(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function _addToFeed(el) {
        const feed = document.getElementById('hw-messages');
        if (!feed) return;
        feed.appendChild(el);
        feed.scrollTop = feed.scrollHeight;
    }

    function _setLoading(state) {
        _isLoading = state;
        const btn = document.getElementById('hw-send-btn');
        if (btn) btn.disabled = state;
    }

    function _escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/\n/g, '<br>');
    }

})();
