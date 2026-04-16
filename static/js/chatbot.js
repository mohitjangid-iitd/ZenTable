/* ═══════════════════════════════════════════════════════════
   chatbot.js — ZenTable Owner Dashboard AI Chatbot
   Endpoint: POST /api/chat
   Response: { response: "...", category: "ANALYTICS|PLATFORM_HELP|UNKNOWN" }
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── CONFIG ─────────────────────────────────────────────
    const API_URL     = '/api/chat';
    const MAX_HISTORY = 40; // messages to keep in DOM

    const SUGGESTIONS = [
        'Aaj ki sales?',
        'Top dishes this week?',
        'Last 7 din ka summary?',
        'Staff account kaise banate hain?',
    ];

    const WELCOME_MSG =
        'Namaste! 👋 Main ZenTable AI hoon.\n' +
        'Aap mujhse apne restaurant ki analytics pooch sakte hain ya platform ke baare mein kuch bhi!';

    // ── STATE ──────────────────────────────────────────────
    let _isLoading  = false;
    let _initialized = false;

    // ── DOM REFS (lazily resolved) ─────────────────────────
    const $ = id => document.getElementById(id);

    // ── INIT ───────────────────────────────────────────────
    function initChatbot() {
        if (_initialized) return;
        _initialized = true;

        _renderSuggestions();
        _appendAiMessage(WELCOME_MSG, null);

        // Enter key to send (Shift+Enter = newline)
        const input = $('chat-input');
        if (input) {
            input.addEventListener('keydown', e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });

            // Auto-resize textarea
            input.addEventListener('input', function () {
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 90) + 'px';
            });
        }
    }

    // ── SUGGESTION CHIPS ───────────────────────────────────
    function _renderSuggestions() {
        const container = $('chat-suggestions');
        if (!container) return;

        container.innerHTML = SUGGESTIONS.map(s =>
            `<button class="chip" onclick="chatSendSuggestion('${s}')">${s}</button>`
        ).join('');
    }

    // Called from HTML chip onclick
    window.chatSendSuggestion = function (text) {
        const input = $('chat-input');
        if (input) input.value = text;
        sendMessage();
    };

    // ── SEND ───────────────────────────────────────────────
    window.sendMessage = async function () {
        if (_isLoading) return;

        const input = $('chat-input');
        if (!input) return;

        const text = input.value.trim();
        if (!text) return;

        // Clear input
        input.value = '';
        input.style.height = 'auto';

        // Hide suggestion chips after first user message
        const sugBox = $('chat-suggestions');
        if (sugBox) sugBox.style.display = 'none';

        // Show user bubble
        _appendUserMessage(text);

        // Show typing indicator
        const typingId = _appendTyping();

        // Disable send
        _setLoading(true);
        _hideError();

        try {
            const res = await fetch(API_URL, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin', // send auth_token cookie
                body: JSON.stringify({ message: text }),
            });

            _removeTyping(typingId);

            if (res.status === 429) {
                _showError('Bahut zyada requests! Ek minute baad try karo. ⏳');
                return;
            }

            if (res.status === 403) {
                _showError('Sirf owners is feature ka use kar sakte hain.');
                return;
            }

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                _showError(err.detail || 'Kuch galat ho gaya. Dobara try karo.');
                return;
            }

            const data = await res.json();
            _appendAiMessage(data.response, data.category);

        } catch (e) {
            _removeTyping(typingId);
            _showError('Network error. Internet check karo.');
        } finally {
            _setLoading(false);
        }
    };

    // ── DOM HELPERS ────────────────────────────────────────

    function _appendUserMessage(text) {
        const el = document.createElement('div');
        el.className = 'msg user';
        el.innerHTML = `
            <div class="msg-avatar">👤</div>
            <div class="msg-body">
                <div class="msg-bubble">${_escape(text)}</div>
            </div>`;
        _addToFeed(el);
    }

    function _appendAiMessage(text, category) {
        const el = document.createElement('div');
        el.className = 'msg ai';

        const categoryPill = category
            ? `<span class="msg-category ${category}">${_categoryLabel(category)}</span>`
            : '';

        el.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="msg-body">
                <div class="msg-bubble">${_escape(text)}</div>
                ${categoryPill}
            </div>`;
        _addToFeed(el);
    }

    function _appendTyping() {
        const id = 'typing-' + Date.now();
        const el = document.createElement('div');
        el.className = 'msg ai msg-typing';
        el.id = id;
        el.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="msg-body">
                <div class="msg-bubble">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>`;
        _addToFeed(el);
        return id;
    }

    function _removeTyping(id) {
        const el = $(id);
        if (el) el.remove();
    }

    function _addToFeed(el) {
        const feed = $('chat-messages');
        if (!feed) return;
        feed.appendChild(el);

        // Trim old messages if too many
        const msgs = feed.querySelectorAll('.msg:not(.msg-typing)');
        if (msgs.length > MAX_HISTORY) {
            msgs[0].remove();
        }

        // Scroll to bottom
        feed.scrollTop = feed.scrollHeight;
    }

    function _setLoading(state) {
        _isLoading = state;
        const btn = $('chat-send-btn');
        if (btn) btn.disabled = state;
    }

    function _showError(msg) {
        const el = $('chat-error-banner');
        if (!el) return;
        el.textContent = msg;
        el.classList.add('show');
        setTimeout(() => el.classList.remove('show'), 5000);
    }

    function _hideError() {
        const el = $('chat-error-banner');
        if (el) el.classList.remove('show');
    }

    // ── UTILS ──────────────────────────────────────────────

    function _escape(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function _categoryLabel(cat) {
        const labels = {
            ANALYTICS:     '📊 Analytics',
            PLATFORM_HELP: '📖 Help',
            UNKNOWN:       '🤷 Unknown',
        };
        return labels[cat] || cat;
    }

    // ── TAB HOOK ───────────────────────────────────────────
    // staff_owner.js mein switchTab patch karte hain
    // Jab 'chatbot' tab open ho tab initChatbot() call hota hai

    const _originalSwitchTab = window.switchTab;
    window.switchTab = function (tab, btn) {
        // Show/hide chatbot tab manually (original switchTab handles others)
        const chatTab = $('tab-chatbot');
        if (chatTab) {
            if (tab === 'chatbot') {
                // Hide all other tabs first
                ['overview','analytics','orders','tables','staff','manage'].forEach(t => {
                    const el = $('tab-' + t);
                    if (el) el.style.display = 'none';
                });
                chatTab.classList.add('active-tab');
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                if (btn) btn.classList.add('active');
                initChatbot();
                return; // don't call original
            } else {
                chatTab.classList.remove('active-tab');
            }
        }
        if (_originalSwitchTab) _originalSwitchTab(tab, btn);
    };

})();
