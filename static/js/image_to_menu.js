/**
 * image_to_menu.js — Add from Photo (Image to Menu)
 * ===================================================
 * Admin panel mein "+ Add from Photo" button ke liye
 *
 * Flow:
 *   1. File picker open
 *   2. Image preview + scanning animation
 *   3. POST /api/admin/image-to-menu → dishes JSON
 *   4. Review panel — cards with inline edit, veg toggle, delete
 *   5. "Add X dishes to menu" → existing addDish() function call
 */

(function () {
  "use strict";

  // ─── Config ────────────────────────────────────────────────────
  // Endpoint dynamically banta hai — admin ya owner role ke hisaab se
  // Admin:  /api/admin/image-to-menu/{client_id}
  // Owner:  /api/owner/{client_id}/image-to-menu
  function _buildEndpoint(clientId) {
    const ownerPanel = _isOwnerPanel();
    if (ownerPanel) {
      return `/api/owner/${clientId}/image-to-menu`;
    } else {
      return `/api/admin/image-to-menu/${clientId}`;
    }
  }

  // ─── State ─────────────────────────────────────────────────────
  let _extractedDishes = []; // dishes from Gemini
  let _currentClientId = null;

  // ─── Init ──────────────────────────────────────────────────────
  function init() {
    _injectStyles();
    _injectHTML();
    _bindTriggerButton();
  }

  // ─── Inject CSS ────────────────────────────────────────────────
  function _injectStyles() {
    if (document.getElementById("itm-styles")) return;
    const style = document.createElement("style");
    style.id = "itm-styles";
    style.textContent = `
      /* ── Overlay ── */
      #itm-overlay {
        display: none;
        position: fixed;
        inset: 0;
        background: rgba(10, 10, 20, 0.75);
        backdrop-filter: blur(4px);
        z-index: 9000;
        align-items: center;
        justify-content: center;
      }
      #itm-overlay.active { display: flex; }

      /* ── Modal ── */
      #itm-modal {
        background: #1a1a2e;
        border: 1px solid rgba(108, 99, 255, 0.3);
        border-radius: 16px;
        width: min(680px, 95vw);
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        box-shadow: 0 24px 64px rgba(0,0,0,0.5), 0 0 0 1px rgba(108,99,255,0.1);
      }

      /* ── Header ── */
      #itm-header {
        padding: 20px 24px 16px;
        border-bottom: 1px solid rgba(255,255,255,0.07);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-shrink: 0;
      }
      #itm-header h3 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 600;
        color: #e8e6ff;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      #itm-close-btn {
        background: none;
        border: none;
        color: #888;
        cursor: pointer;
        font-size: 1.4rem;
        line-height: 1;
        padding: 4px 8px;
        border-radius: 6px;
        transition: color 0.2s, background 0.2s;
      }
      #itm-close-btn:hover { color: #fff; background: rgba(255,255,255,0.08); }

      /* ── Body ── */
      #itm-body { overflow-y: auto; padding: 24px; flex: 1; }

      /* ── Upload zone ── */
      #itm-upload-zone {
        border: 2px dashed rgba(108, 99, 255, 0.4);
        border-radius: 12px;
        padding: 40px 20px;
        text-align: center;
        cursor: pointer;
        transition: border-color 0.2s, background 0.2s;
        background: rgba(108, 99, 255, 0.04);
      }
      #itm-upload-zone:hover {
        border-color: rgba(108, 99, 255, 0.7);
        background: rgba(108, 99, 255, 0.08);
      }
      #itm-upload-zone.drag-over {
        border-color: #6C63FF;
        background: rgba(108, 99, 255, 0.12);
      }
      #itm-upload-icon { font-size: 2.5rem; margin-bottom: 12px; }
      #itm-upload-zone p { color: #aaa; margin: 6px 0 0; font-size: 0.9rem; }
      #itm-upload-zone strong { color: #c8c5ff; }

      /* ── Hidden file input ── */
      #itm-file-input { display: none; }

      /* ── Image preview ── */
      #itm-preview-section { display: none; }
      #itm-preview-img {
        width: 100%;
        max-height: 220px;
        object-fit: contain;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.08);
        background: #111;
      }

      /* ── Scanning animation ── */
      #itm-scanning {
        display: none;
        margin-top: 16px;
        padding: 16px;
        background: rgba(108, 99, 255, 0.08);
        border-radius: 10px;
        border: 1px solid rgba(108, 99, 255, 0.2);
        text-align: center;
      }
      #itm-scanning.active { display: block; }
      .itm-scan-bar {
        height: 3px;
        background: linear-gradient(90deg, transparent, #6C63FF, #a78bfa, transparent);
        border-radius: 2px;
        margin: 10px 0;
        animation: itm-scan-move 1.6s ease-in-out infinite;
        background-size: 60% 100%;
        background-repeat: no-repeat;
      }
      @keyframes itm-scan-move {
        0%   { background-position: -60% 0; }
        100% { background-position: 160% 0; }
      }
      .itm-scan-text {
        color: #a78bfa;
        font-size: 0.85rem;
        font-weight: 500;
        letter-spacing: 0.03em;
      }

      /* ── Skeleton cards ── */
      #itm-skeleton { display: none; margin-top: 16px; }
      #itm-skeleton.active { display: block; }
      .itm-skeleton-card {
        background: rgba(255,255,255,0.04);
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
        display: flex;
        gap: 12px;
        align-items: center;
      }
      .itm-skel-block {
        background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%);
        background-size: 200% 100%;
        border-radius: 6px;
        animation: itm-shimmer 1.5s infinite;
      }
      @keyframes itm-shimmer {
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }

      /* ── Error / Empty state ── */
      #itm-error {
        display: none;
        margin-top: 16px;
        padding: 14px 16px;
        background: rgba(255, 71, 87, 0.1);
        border: 1px solid rgba(255, 71, 87, 0.3);
        border-radius: 10px;
        color: #ff6b7a;
        font-size: 0.9rem;
        text-align: center;
      }
      #itm-error.active { display: block; }

      /* ── Review section ── */
      #itm-review { display: none; margin-top: 4px; }
      #itm-review.active { display: block; }
      .itm-review-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 14px;
      }
      .itm-review-header span {
        color: #aaa;
        font-size: 0.85rem;
      }
      .itm-review-header strong { color: #c8c5ff; }

      /* ── Dish card ── */
      .itm-dish-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 10px;
        transition: border-color 0.2s;
        position: relative;
      }
      .itm-dish-card:hover { border-color: rgba(108, 99, 255, 0.3); }
      .itm-dish-card.removed {
        opacity: 0.35;
        border-style: dashed;
        pointer-events: none;
      }

      .itm-card-top {
        display: flex;
        align-items: flex-start;
        gap: 10px;
      }

      /* Veg/Non-veg toggle dot */
      .itm-veg-toggle {
        flex-shrink: 0;
        width: 22px;
        height: 22px;
        border-radius: 4px;
        border: 2px solid;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        margin-top: 2px;
      }
      .itm-veg-toggle.veg {
        border-color: #43E97B;
        background: rgba(67, 233, 123, 0.1);
      }
      .itm-veg-toggle.veg::after {
        content: '';
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #43E97B;
      }
      .itm-veg-toggle.non-veg {
        border-color: #FF4757;
        background: rgba(255, 71, 87, 0.1);
      }
      .itm-veg-toggle.non-veg::after {
        content: '';
        width: 0; height: 0;
        border-left: 6px solid transparent;
        border-right: 6px solid transparent;
        border-bottom: 10px solid #FF4757;
      }

      .itm-card-info { flex: 1; min-width: 0; }
      .itm-card-actions {
        flex-shrink: 0;
        display: flex;
        gap: 6px;
        align-items: center;
      }

      /* Editable fields */
      .itm-field {
        width: 100%;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 6px;
        color: #e8e6ff;
        padding: 5px 8px;
        font-size: 0.85rem;
        font-family: inherit;
        transition: border-color 0.2s;
        box-sizing: border-box;
      }
      .itm-field:focus {
        outline: none;
        border-color: rgba(108, 99, 255, 0.5);
      }
      .itm-field-name {
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 6px;
        color: #e8e6ff;
      }
      .itm-field-row {
        display: flex;
        gap: 8px;
        margin-top: 6px;
      }
      .itm-field-row .itm-field { flex: 1; }
      .itm-cat-badge {
        display: inline-block;
        background: rgba(108, 99, 255, 0.15);
        color: #a78bfa;
        border-radius: 4px;
        padding: 2px 7px;
        font-size: 0.75rem;
        margin-bottom: 6px;
      }

      /* Action buttons */
      .itm-btn-icon {
        width: 30px; height: 30px;
        border-radius: 6px;
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.9rem;
        transition: background 0.2s, transform 0.1s;
      }
      .itm-btn-icon:active { transform: scale(0.9); }
      .itm-btn-remove {
        background: rgba(255, 71, 87, 0.1);
        color: #FF4757;
      }
      .itm-btn-remove:hover { background: rgba(255, 71, 87, 0.2); }

      /* ── Footer ── */
      #itm-footer {
        padding: 16px 24px;
        border-top: 1px solid rgba(255,255,255,0.07);
        display: flex;
        gap: 10px;
        justify-content: flex-end;
        flex-shrink: 0;
      }
      .itm-btn {
        padding: 9px 20px;
        border-radius: 8px;
        border: none;
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        font-family: inherit;
      }
      .itm-btn:active { transform: scale(0.97); }
      .itm-btn-secondary {
        background: rgba(255,255,255,0.07);
        color: #aaa;
      }
      .itm-btn-secondary:hover { background: rgba(255,255,255,0.12); color: #e8e6ff; }
      .itm-btn-primary {
        background: linear-gradient(135deg, #6C63FF, #8b5cf6);
        color: #fff;
        box-shadow: 0 4px 14px rgba(108, 99, 255, 0.35);
      }
      .itm-btn-primary:hover { filter: brightness(1.1); }
      .itm-btn-primary:disabled {
        opacity: 0.4;
        cursor: not-allowed;
        filter: none;
      }

      /* Scrollbar */
      #itm-body::-webkit-scrollbar { width: 5px; }
      #itm-body::-webkit-scrollbar-track { background: transparent; }
      #itm-body::-webkit-scrollbar-thumb { background: rgba(108,99,255,0.3); border-radius: 10px; }
    `;
    document.head.appendChild(style);
  }

  // ─── Inject HTML ───────────────────────────────────────────────
  function _injectHTML() {
    if (document.getElementById("itm-overlay")) return;

    const overlay = document.createElement("div");
    overlay.id = "itm-overlay";
    overlay.innerHTML = `
      <div id="itm-modal">
        <div id="itm-header">
          <h3>📷 Add from Photo</h3>
          <button id="itm-close-btn" title="Close">✕</button>
        </div>

        <div id="itm-body">
          <!-- Upload Zone -->
          <div id="itm-upload-zone">
            <div id="itm-upload-icon">🍽️</div>
            <strong>Menu photo yahan drop karo</strong>
            <p>ya click karke select karo</p>
            <p style="margin-top:8px; font-size:0.78rem; color:#666;">JPG, PNG, WebP · Max 10MB</p>
          </div>
          <input type="file" id="itm-file-input" accept="image/jpeg,image/jpg,image/png,image/webp">

          <!-- Preview + Scan -->
          <div id="itm-preview-section">
            <img id="itm-preview-img" alt="Menu preview">
            <div id="itm-scanning">
              <div class="itm-scan-text">🔍 Dishes scan kar raha hoon...</div>
              <div class="itm-scan-bar"></div>
              <div class="itm-scan-text" style="font-size:0.78rem; color:#7c6fcf; margin-top:4px;">AI menu analyze kar raha hai</div>
            </div>
          </div>

          <!-- Skeleton loader -->
          <div id="itm-skeleton">
            ${[1,2,3].map(() => `
              <div class="itm-skeleton-card">
                <div class="itm-skel-block" style="width:22px;height:22px;border-radius:4px;flex-shrink:0"></div>
                <div style="flex:1">
                  <div class="itm-skel-block" style="height:14px;width:60%;margin-bottom:8px"></div>
                  <div class="itm-skel-block" style="height:11px;width:35%"></div>
                </div>
                <div class="itm-skel-block" style="width:55px;height:26px;border-radius:6px"></div>
              </div>
            `).join('')}
          </div>

          <!-- Error state -->
          <div id="itm-error"></div>

          <!-- Review Panel -->
          <div id="itm-review">
            <div class="itm-review-header">
              <span><strong id="itm-count">0</strong> dishes mili hain — review karo</span>
              <span style="font-size:0.78rem;color:#666;">Veg dot click karke toggle kar sakte ho</span>
            </div>
            <div id="itm-cards-container"></div>
          </div>
        </div>

        <div id="itm-footer">
          <button class="itm-btn itm-btn-secondary" id="itm-cancel-btn">Cancel</button>
          <button class="itm-btn itm-btn-primary" id="itm-confirm-btn" disabled>Add 0 Dishes</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    _bindModalEvents();
  }

  // ─── Detect panel theme ────────────────────────────────────────
  // owner panel = var(--primary) / var(--secondary) CSS vars use karta hai
  // admin panel = dark purple fixed colors use karta hai
  function _isOwnerPanel() {
    return !!(
      document.getElementById("owner-dish-modal") ||    // owner dish modal
      document.getElementById("tab-manage") ||           // owner manage tab
      typeof openOwnerAddDish === "function"              // owner JS function
    );
  }

  // ─── Bind trigger button ───────────────────────────────────────
  function _bindTriggerButton() {
    const ownerPanel = _isOwnerPanel();

    // ── Find the "Add Dish" anchor button ──
    // Owner panel: button[onclick="openOwnerAddDish()"] inside #msub-dishes
    // Admin panel: #add-dish-btn, .add-dish-btn, [data-action="add-dish"]
    const selectors = ownerPanel
      ? [
          'button[onclick="openOwnerAddDish()"]',   // exact owner button
          '#msub-dishes .refresh-btn',               // fallback by class inside dishes section
        ]
      : [
          '[data-action="add-dish"]',
          '#add-dish-btn',
          '.add-dish-btn',
        ];

    let addDishBtn = null;
    for (const sel of selectors) {
      addDishBtn = document.querySelector(sel);
      if (addDishBtn) break;
    }

    const triggerBtn = document.createElement("button");
    triggerBtn.id = "itm-trigger-btn";
    triggerBtn.innerHTML = "📷 Add from Photo";

    if (ownerPanel) {
      // ── Owner theme — match karo refresh-btn style ──
      triggerBtn.className = "refresh-btn";  // owner ka existing class
      triggerBtn.style.cssText = `
        margin-left: 8px;
        white-space: nowrap;
      `;
    } else {
      // ── Admin dark theme ──
      triggerBtn.style.cssText = `
        margin-left: 10px;
        padding: 8px 16px;
        background: linear-gradient(135deg, rgba(108,99,255,0.15), rgba(139,92,246,0.15));
        border: 1px solid rgba(108,99,255,0.4);
        border-radius: 8px;
        color: #a78bfa;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        font-family: inherit;
        white-space: nowrap;
      `;
      triggerBtn.addEventListener("mouseenter", () => {
        triggerBtn.style.background = "linear-gradient(135deg, rgba(108,99,255,0.25), rgba(139,92,246,0.25))";
        triggerBtn.style.borderColor = "rgba(108,99,255,0.7)";
      });
      triggerBtn.addEventListener("mouseleave", () => {
        triggerBtn.style.background = "linear-gradient(135deg, rgba(108,99,255,0.15), rgba(139,92,246,0.15))";
        triggerBtn.style.borderColor = "rgba(108,99,255,0.4)";
      });
    }

    triggerBtn.addEventListener("click", openModal);

    if (addDishBtn && addDishBtn.parentElement) {
      if (ownerPanel) {
        // Owner: Add Dish button ko wrapper div mein wrap karo
        // taaki space-between layout dono ko alag na kare
        const wrapper = document.createElement("div");
        wrapper.style.cssText = "display:flex; gap:8px; align-items:center;";
        addDishBtn.parentElement.replaceChild(wrapper, addDishBtn);
        wrapper.appendChild(addDishBtn);
        wrapper.appendChild(triggerBtn);
      } else {
        addDishBtn.parentElement.insertBefore(triggerBtn, addDishBtn.nextSibling);
      }
    } else {
      // Fallback: dish form ke paas koi container dhundho
      const fallback = document.querySelector(
        "#msub-dishes, .dish-actions, #dish-form-container, #menu-editor-header, .menu-section-header"
      );
      if (fallback) {
        const hd = fallback.querySelector("div");
        if (hd) hd.appendChild(triggerBtn);
        else fallback.appendChild(triggerBtn);
      } else {
        // Last resort — body mein fixed position (chatbot ke upar)
        triggerBtn.style.position = "fixed";
        triggerBtn.style.bottom = "90px";   // chatbot FAB ke upar
        triggerBtn.style.right = "20px";
        triggerBtn.style.zIndex = "8000";
        if (!ownerPanel) triggerBtn.style.boxShadow = "0 4px 20px rgba(108,99,255,0.4)";
        document.body.appendChild(triggerBtn);
      }
    }
  }

  // ─── Modal events ──────────────────────────────────────────────
  function _bindModalEvents() {
    // Close
    document.getElementById("itm-close-btn").addEventListener("click", closeModal);
    document.getElementById("itm-cancel-btn").addEventListener("click", closeModal);
    document.getElementById("itm-overlay").addEventListener("click", (e) => {
      if (e.target === document.getElementById("itm-overlay")) closeModal();
    });

    // Upload zone click
    const zone = document.getElementById("itm-upload-zone");
    zone.addEventListener("click", () => document.getElementById("itm-file-input").click());

    // Drag & drop
    zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      const file = e.dataTransfer.files[0];
      if (file) _handleFile(file);
    });

    // File input change
    document.getElementById("itm-file-input").addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) _handleFile(file);
    });

    // Confirm button
    document.getElementById("itm-confirm-btn").addEventListener("click", _confirmAddDishes);
  }

  // ─── Open / close modal ────────────────────────────────────────
  function openModal(clientId) {
    if (typeof clientId === "string") _currentClientId = clientId;
    else {
      // Try to get from global or URL
      _currentClientId = window._currentClientId ||
        (typeof currentClientId !== "undefined" ? currentClientId : null) ||
        document.querySelector("[data-client-id]")?.dataset?.clientId ||
        new URLSearchParams(window.location.search).get("client_id") ||
        location.pathname.split("/").filter(Boolean)[0];
    }
    _resetModal();
    document.getElementById("itm-overlay").classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    document.getElementById("itm-overlay").classList.remove("active");
    document.body.style.overflow = "";
    // Reset file input so same file can be re-selected
    document.getElementById("itm-file-input").value = "";
  }

  // ─── Reset state ───────────────────────────────────────────────
  function _resetModal() {
    _extractedDishes = [];
    _show("upload-zone", true);
    _show("preview-section", false);
    _show("scanning", false);
    _show("skeleton", false);
    _show("error", false);
    _show("review", false);
    document.getElementById("itm-cards-container").innerHTML = "";
    document.getElementById("itm-confirm-btn").disabled = true;
    document.getElementById("itm-confirm-btn").textContent = "Add 0 Dishes";
  }

  // ─── File handling ─────────────────────────────────────────────
  function _handleFile(file) {
    // Validate type
    const allowed = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
    if (!allowed.includes(file.type.toLowerCase())) {
      _showError("Invalid file type. JPG, PNG, ya WebP upload karo.");
      return;
    }
    // Validate size
    if (file.size > 10 * 1024 * 1024) {
      _showError("Image bahut badi hai (max 10MB).");
      return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
      document.getElementById("itm-preview-img").src = e.target.result;
    };
    reader.readAsDataURL(file);

    _show("upload-zone", false);
    _show("preview-section", true);
    _show("error", false);
    _show("review", false);

    // Start scan animation + upload
    setTimeout(() => _uploadImage(file), 300);
  }

  // ─── Upload to backend ─────────────────────────────────────────
  async function _uploadImage(file) {
    _show("scanning", true);
    _show("skeleton", true);

    const formData = new FormData();
    formData.append("image", file);

    // client_id resolve karo — openModal se set hota hai
    const clientId = _currentClientId;
    if (!clientId) {
      _showError("Restaurant ID nahi mila. Page reload karo.");
      _show("scanning", false);
      _show("skeleton", false);
      return;
    }

    const endpoint = _buildEndpoint(clientId);

    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      const data = await resp.json();

      _show("scanning", false);
      _show("skeleton", false);

      if (!resp.ok) {
        _showError(data.detail || "Server error aaya. Dobara try karo.");
        return;
      }

      if (!data.success || !data.dishes || data.dishes.length === 0) {
        _showError(data.message || "Koi dish nahi mili. Clearer photo try karo.");
        return;
      }

      _extractedDishes = data.dishes;
      _renderReviewPanel();

    } catch (err) {
      _show("scanning", false);
      _show("skeleton", false);
      _showError("Network error. Internet connection check karo aur dobara try karo.");
      console.error("[itm] Upload error:", err);
    }
  }

  // ─── Render review cards ───────────────────────────────────────
  function _renderReviewPanel() {
    const container = document.getElementById("itm-cards-container");
    container.innerHTML = "";

    _extractedDishes.forEach((dish, idx) => {
      const card = _createDishCard(dish, idx);
      container.appendChild(card);
    });

    _show("review", true);
    _updateConfirmButton();
  }

  function _createDishCard(dish, idx) {
    const card = document.createElement("div");
    card.className = "itm-dish-card";
    card.dataset.idx = idx;

    const isVeg   = dish.veg === true;
    const isOwner = _isOwnerPanel();
    const hasSizes = Array.isArray(dish.sizes) && dish.sizes.length > 0;

    card.innerHTML = `
      <div class="itm-card-top">
        <div class="itm-veg-toggle ${isVeg ? "veg" : "non-veg"}"
             title="${isVeg ? "Veg (click to toggle)" : "Non-veg (click to toggle)"}"
             data-veg="${isVeg}"></div>
        <div class="itm-card-info">

          <!-- Row 1: Category badge (editable) + Name -->
          <input type="text" class="itm-field" value="${_esc(dish.category || "")}"
                 placeholder="Category" data-field="category"
                 style="display:inline-block;width:auto;min-width:80px;max-width:160px;
                        background:rgba(108,99,255,0.15);border-color:transparent;
                        color:#a78bfa;font-size:0.75rem;padding:2px 8px;margin-bottom:5px;border-radius:4px;">
          <input type="text" class="itm-field itm-field-name" value="${_esc(dish.name || "")}"
                 placeholder="Dish name" data-field="name"
                 style="width:100%;box-sizing:border-box;margin-bottom:0;">

          <!-- Row 2: Price / Sizes toggle -->
          <div class="itm-price-section" style="margin-top:6px;">
            <!-- Size mode toggle -->
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <span style="font-size:0.75rem;color:#888;">Price type:</span>
              <button class="itm-size-toggle-btn itm-size-single ${!hasSizes ? "active" : ""}"
                      data-mode="single" style="font-size:0.72rem;padding:2px 8px;border-radius:4px;border:1px solid;cursor:pointer;
                      background:${!hasSizes ? "rgba(108,99,255,0.25)" : "rgba(255,255,255,0.05)"};
                      color:${!hasSizes ? "#a78bfa" : "#666"};
                      border-color:${!hasSizes ? "rgba(108,99,255,0.5)" : "rgba(255,255,255,0.1)"};">
                Single
              </button>
              <button class="itm-size-toggle-btn itm-size-multi ${hasSizes ? "active" : ""}"
                      data-mode="multi" style="font-size:0.72rem;padding:2px 8px;border-radius:4px;border:1px solid;cursor:pointer;
                      background:${hasSizes ? "rgba(108,99,255,0.25)" : "rgba(255,255,255,0.05)"};
                      color:${hasSizes ? "#a78bfa" : "#666"};
                      border-color:${hasSizes ? "rgba(108,99,255,0.5)" : "rgba(255,255,255,0.1)"};">
                Multi-size
              </button>
            </div>

            <!-- Single price input -->
            <div class="itm-single-price" style="display:${!hasSizes ? "block" : "none"};">
              <input type="text" class="itm-field" value="${_esc(dish.price || "")}"
                     placeholder="Price (INR 0)" data-field="price" style="max-width:140px;">
            </div>

            <!-- Multi-size inputs -->
            <div class="itm-multi-sizes" style="display:${hasSizes ? "block" : "none"};">
              <div class="itm-sizes-list" style="display:flex;flex-direction:column;gap:5px;">
                ${(dish.sizes || []).map((s, si) => `
                  <div class="itm-size-row" style="display:flex;gap:6px;align-items:center;" data-si="${si}">
                    <input type="text" class="itm-field itm-size-label" value="${_esc(s.label || "")}"
                           placeholder="Label (e.g. Small)" style="flex:1;font-size:0.8rem;">
                    <input type="text" class="itm-field itm-size-price" value="${_esc(String(s.price || ""))}"
                           placeholder="Price" style="max-width:90px;font-size:0.8rem;">
                    <button class="itm-btn-icon itm-size-del-btn" title="Hatao"
                            style="width:24px;height:24px;font-size:0.75rem;background:rgba(255,71,87,0.1);color:#FF4757;border:none;border-radius:4px;cursor:pointer;flex-shrink:0;">✕</button>
                  </div>
                `).join("")}
              </div>
              <button class="itm-add-size-btn" style="margin-top:6px;font-size:0.75rem;padding:3px 10px;
                      background:rgba(108,99,255,0.1);border:1px dashed rgba(108,99,255,0.4);
                      color:#a78bfa;border-radius:5px;cursor:pointer;">+ Add size</button>
            </div>
          </div>

          <!-- Row 3: Description -->
          <input type="text" class="itm-field" value="${_esc(dish.description || "")}"
                 placeholder="Description (optional)" data-field="description"
                 style="margin-top:6px;width:100%;box-sizing:border-box;">

          <!-- Row 4: Photo upload -->
          <div style="margin-top:6px;display:flex;align-items:center;gap:8px;">
            <label style="font-size:0.75rem;color:#888;flex-shrink:0;">📷 Photo:</label>
            <input type="file" class="itm-dish-photo-input" accept="image/jpeg,image/jpg,image/png,image/webp"
                   style="display:none;">
            <button class="itm-dish-photo-btn" style="font-size:0.75rem;padding:3px 10px;
                    background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.12);
                    color:#aaa;border-radius:5px;cursor:pointer;">Choose photo</button>
            <span class="itm-dish-photo-name" style="font-size:0.73rem;color:#666;"></span>
          </div>

          <!-- Row 5: GLB -->
          <div style="margin-top:5px;display:flex;align-items:center;gap:8px;">
            <label style="font-size:0.75rem;color:#888;flex-shrink:0;">🧊 3D Model:</label>
            ${isOwner
              ? `<span style="font-size:0.73rem;color:#555;font-style:italic;">3D model ke liye ZenTable se contact karo</span>`
              : `<input type="text" class="itm-field" placeholder=".glb filename (e.g. dish.glb)"
                        data-field="glb" value="${_esc(dish.glb || "")}"
                        style="flex:1;font-size:0.8rem;">`
            }
          </div>

        </div>
        <div class="itm-card-actions">
          <button class="itm-btn-icon itm-btn-remove" title="Is dish ko skip karo">✕</button>
        </div>
      </div>
    `;

    // ── Veg toggle ──
    card.querySelector(".itm-veg-toggle").addEventListener("click", function () {
      const cur = this.dataset.veg === "true";
      this.dataset.veg = String(!cur);
      this.className = `itm-veg-toggle ${!cur ? "veg" : "non-veg"}`;
      this.title = !cur ? "Veg (click to toggle)" : "Non-veg (click to toggle)";
      _extractedDishes[idx].veg = !cur;
    });

    // ── Text field changes ──
    card.querySelectorAll("[data-field]").forEach((input) => {
      input.addEventListener("input", () => {
        _extractedDishes[idx][input.dataset.field] = input.value;
      });
    });

    // ── Single / Multi-size toggle buttons ──
    card.querySelectorAll(".itm-size-toggle-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const mode = btn.dataset.mode;
        const single = card.querySelector(".itm-single-price");
        const multi  = card.querySelector(".itm-multi-sizes");
        const btnSingle = card.querySelector(".itm-size-single");
        const btnMulti  = card.querySelector(".itm-size-multi");

        if (mode === "single") {
          single.style.display = "block";
          multi.style.display  = "none";
          btnSingle.style.background    = "rgba(108,99,255,0.25)";
          btnSingle.style.color         = "#a78bfa";
          btnSingle.style.borderColor   = "rgba(108,99,255,0.5)";
          btnMulti.style.background     = "rgba(255,255,255,0.05)";
          btnMulti.style.color          = "#666";
          btnMulti.style.borderColor    = "rgba(255,255,255,0.1)";
          // Clear sizes from dish
          delete _extractedDishes[idx].sizes;
          const priceInput = card.querySelector(".itm-single-price .itm-field");
          _extractedDishes[idx].price = priceInput ? priceInput.value : "";
        } else {
          single.style.display = "none";
          multi.style.display  = "block";
          btnMulti.style.background     = "rgba(108,99,255,0.25)";
          btnMulti.style.color          = "#a78bfa";
          btnMulti.style.borderColor    = "rgba(108,99,255,0.5)";
          btnSingle.style.background    = "rgba(255,255,255,0.05)";
          btnSingle.style.color         = "#666";
          btnSingle.style.borderColor   = "rgba(255,255,255,0.1)";
          // Init sizes if empty
          if (!_extractedDishes[idx].sizes) {
            _extractedDishes[idx].sizes = [{ label: "", price: "" }];
            delete _extractedDishes[idx].price;
            // Render one empty row
            _refreshSizeRows(card, idx);
          }
        }
      });
    });

    // ── Size row events (label / price / delete) ──
    _bindSizeEvents(card, idx);

    // ── Add size button ──
    card.querySelector(".itm-add-size-btn").addEventListener("click", () => {
      if (!_extractedDishes[idx].sizes) _extractedDishes[idx].sizes = [];
      _extractedDishes[idx].sizes.push({ label: "", price: "" });
      _refreshSizeRows(card, idx);
    });

    // ── Photo upload ──
    const photoBtn   = card.querySelector(".itm-dish-photo-btn");
    const photoInput = card.querySelector(".itm-dish-photo-input");
    const photoName  = card.querySelector(".itm-dish-photo-name");
    photoBtn.addEventListener("click", () => photoInput.click());
    photoInput.addEventListener("change", () => {
      const file = photoInput.files[0];
      if (!file) return;
      photoName.textContent = file.name;
      _extractedDishes[idx]._photoFile = file;
      // Preview thumbnail
      const reader = new FileReader();
      reader.onload = e => {
        photoBtn.style.backgroundImage = `url(${e.target.result})`;
        photoBtn.style.backgroundSize  = "cover";
        photoBtn.style.backgroundPosition = "center";
        photoBtn.style.width  = "40px";
        photoBtn.style.height = "40px";
        photoBtn.style.borderRadius = "6px";
        photoBtn.textContent = "";
      };
      reader.readAsDataURL(file);
    });

    // ── Remove button ──
    card.querySelector(".itm-btn-remove").addEventListener("click", () => {
      card.classList.add("removed");
      card.dataset.removed = "true";
      _updateConfirmButton();
    });

    return card;
  }

  // ── Bind size row events (label, price, delete) ──
  function _bindSizeEvents(card, idx) {
    card.querySelectorAll(".itm-size-row").forEach((row) => {
      const si = parseInt(row.dataset.si);
      row.querySelector(".itm-size-label").addEventListener("input", (e) => {
        if (_extractedDishes[idx].sizes && _extractedDishes[idx].sizes[si]) {
          _extractedDishes[idx].sizes[si].label = e.target.value;
        }
      });
      row.querySelector(".itm-size-price").addEventListener("input", (e) => {
        if (_extractedDishes[idx].sizes && _extractedDishes[idx].sizes[si]) {
          _extractedDishes[idx].sizes[si].price = e.target.value;
        }
      });
      row.querySelector(".itm-size-del-btn").addEventListener("click", () => {
        if (_extractedDishes[idx].sizes) {
          _extractedDishes[idx].sizes.splice(si, 1);
          _refreshSizeRows(card, idx);
        }
      });
    });
  }

  // ── Re-render size rows after add/delete ──
  function _refreshSizeRows(card, idx) {
    const list   = card.querySelector(".itm-sizes-list");
    const sizes  = _extractedDishes[idx].sizes || [];
    list.innerHTML = sizes.map((s, si) => `
      <div class="itm-size-row" style="display:flex;gap:6px;align-items:center;" data-si="${si}">
        <input type="text" class="itm-field itm-size-label" value="${_esc(s.label || "")}"
               placeholder="Label (e.g. Small)" style="flex:1;font-size:0.8rem;">
        <input type="text" class="itm-field itm-size-price" value="${_esc(String(s.price || ""))}"
               placeholder="Price" style="max-width:90px;font-size:0.8rem;">
        <button class="itm-btn-icon itm-size-del-btn" title="Hatao"
                style="width:24px;height:24px;font-size:0.75rem;background:rgba(255,71,87,0.1);color:#FF4757;border:none;border-radius:4px;cursor:pointer;flex-shrink:0;">✕</button>
      </div>
    `).join("");
    _bindSizeEvents(card, idx);
  }

  // ─── Update confirm button ─────────────────────────────────────
  function _updateConfirmButton() {
    const cards = document.querySelectorAll(".itm-dish-card:not([data-removed='true'])");
    const count = cards.length;
    const btn = document.getElementById("itm-confirm-btn");
    btn.disabled = count === 0;
    btn.textContent = `Add ${count} Dish${count === 1 ? "" : "es"} to Menu`;
  }

  // ─── Confirm add dishes ────────────────────────────────────────
  function _confirmAddDishes() {
    const cards = document.querySelectorAll(".itm-dish-card:not([data-removed='true'])");
    const dishesToAdd = [];

    cards.forEach((card) => {
      const idx = parseInt(card.dataset.idx);
      const dish = _extractedDishes[idx];
      if (!dish) return;

      // Collect latest field values from inputs
      card.querySelectorAll("[data-field]").forEach((input) => {
        dish[input.dataset.field] = input.value;
      });
      const vegToggle = card.querySelector(".itm-veg-toggle");
      if (vegToggle) dish.veg = vegToggle.dataset.veg === "true";

      dishesToAdd.push(dish);
    });

    if (dishesToAdd.length === 0) return;

    // Dispatch custom event — admin.js mein listen karo
    const event = new CustomEvent("itm:dishes-confirmed", {
      detail: {
        dishes: dishesToAdd,
        clientId: _currentClientId,
      },
      bubbles: true,
    });
    document.dispatchEvent(event);

    // Direct integration — owner panel ke liye
    if (typeof window.ownerBulkAddDishes === "function") {
      window.ownerBulkAddDishes(dishesToAdd);
    } else if (typeof window.addDishFromImage === "function") {
      dishesToAdd.forEach((d) => window.addDishFromImage(d));
    } else if (typeof window.addDishesToMenuBulk === "function") {
      window.addDishesToMenuBulk(dishesToAdd);
    }

    closeModal();

    // Success toast
    _showToast(`✅ ${dishesToAdd.length} dish${dishesToAdd.length === 1 ? "" : "es"} menu mein add ho gayi!`);
  }

  // ─── Toast notification ────────────────────────────────────────
  function _showToast(message) {
    const existing = document.getElementById("itm-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.id = "itm-toast";
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%) translateY(20px);
      background: rgba(26, 26, 46, 0.95);
      border: 1px solid rgba(67, 233, 123, 0.3);
      color: #43E97B;
      padding: 12px 24px;
      border-radius: 10px;
      font-size: 0.9rem;
      font-weight: 600;
      z-index: 99999;
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
      transition: all 0.3s ease;
      font-family: inherit;
      pointer-events: none;
    `;
    document.body.appendChild(toast);
    requestAnimationFrame(() => {
      toast.style.transform = "translateX(-50%) translateY(0)";
      toast.style.opacity = "1";
    });
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(-50%) translateY(10px)";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // ─── Helpers ───────────────────────────────────────────────────
  function _show(id, visible) {
    const el = document.getElementById("itm-" + id);
    if (!el) return;
    if (visible) el.classList.add("active");
    else el.classList.remove("active");
  }

  function _showError(msg) {
    const el = document.getElementById("itm-error");
    el.textContent = "⚠️ " + msg;
    el.classList.add("active");
    _show("upload-zone", true);
    _show("preview-section", false);
  }

  function _esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // ─── Public API ────────────────────────────────────────────────
  window.ImageToMenu = {
    open:  openModal,
    close: closeModal,
  };

  // ─── Auto-init on DOM ready ────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();