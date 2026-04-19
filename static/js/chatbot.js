/* ═══════════════════════════════════════════════════════════
   chatbot.js — ZenTable Owner Dashboard AI Chatbot
   Endpoint: POST /api/chat
   Response: { response: "...", category: "ANALYTICS|PLATFORM_HELP|UNKNOWN" }
   ═══════════════════════════════════════════════════════════ */

(function() {
    function _inject() {
        const fab = document.createElement('button');
        fab.id = 'owner-help-fab';
        fab.title = 'AI Help';
        fab.innerHTML = '🤖';
        fab.setAttribute('onclick', 'toggleOwnerChat()');
        fab.style.cssText = 'position:fixed;bottom:24px;right:20px;z-index:9999;width:54px;height:54px;border-radius:50%;background:var(--primary);border:none;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:center;font-size:1.1rem;color:white;transition:transform 0.2s;';
        document.body.appendChild(fab);

        const panel = document.createElement('div');
        panel.id = 'owner-chat-panel';
        panel.style.cssText = 'display:none;position:fixed;bottom:88px;right:16px;z-index:9998;width:340px;max-height:500px;border-radius:20px;box-shadow:0 8px 40px rgba(0,0,0,0.16);overflow:hidden;flex-direction:column;background:white;';
        panel.innerHTML = `
            <div class="chat-wrap" style="height:500px;">
                <div class="chat-header">
                    <div class="chat-header-avatar">🤖</div>
                    <div class="chat-header-info">
                        <div class="chat-header-name">ZenTable AI</div>
                        <div class="chat-header-status"><span class="status-dot"></span> Online</div>
                    </div>
                    <button onclick="toggleOwnerChat()" style="background:rgba(255,255,255,0.12);border:none;color:white;width:28px;height:28px;border-radius:50%;cursor:pointer;font-size:0.9rem;display:flex;align-items:center;justify-content:center;margin-left:auto;">✕</button>
                </div>
                <div class="chat-messages" id="chat-messages"></div>
                <div class="chat-error-banner" id="chat-error-banner"></div>
                <div class="chat-suggestions" id="chat-suggestions"></div>
                <div class="chat-input-row">
                    <textarea class="chat-input" id="chat-input" placeholder="Kuch bhi poochho..." rows="1"></textarea>
                    <button class="chat-send-btn" id="chat-send-btn" onclick="sendMessage()">➤</button>
                </div>
            </div>
        `;
        document.body.appendChild(panel);

        var _chatOpen = false;
        window.toggleOwnerChat = function() {
            _chatOpen = !_chatOpen;
            panel.style.display = _chatOpen ? 'flex' : 'none';
            fab.style.transform = _chatOpen ? 'scale(0.9)' : 'scale(1)';
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _inject);
    } else {
        _inject();
    }
})();

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
