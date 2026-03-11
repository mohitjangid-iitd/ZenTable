// clientId — HTML template mein inject hota hai

const modelEl = document.querySelector("#ar-model");
const sceneEl = document.querySelector("a-scene");

let currentRotation = { x: 0, y: 0, z: 0 };
let isAutoRotating = false;
let currentScale = 1;

// ======================
// LOAD MENU
// ======================
async function loadMenu() {
    const res = await fetch(`/api/menu/${clientId}`);
    const data = await res.json();
    const carousel = document.getElementById("carousel-wrapper");

    const arItems = data.items.filter(item => item.model_url);
    arItems.forEach((item, index) => {
        const btn = document.createElement("div");
        btn.className = "dish-btn";
        btn.innerHTML = `
            ${item.image
                ? `<img class="thumb" src="${item.image}" alt="${item.name}"
                   onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
                : ''}
            <div class="thumb-placeholder" style="${item.image ? 'display:none' : ''}">🍽️</div>
            <div class="dish-label">${item.name}</div>
            <div class="dish-price-label">${item.price}</div>
        `;

        btn.onclick = () => {
            modelEl.setAttribute("gltf-model", item.model_url);
            modelEl.setAttribute("position", item.position || "0 0 0");
            modelEl.setAttribute("scale", item.scale || "1 1 1");

            currentRotation = { x: 0, y: 0, z: 0 };
            currentScale = parseFloat((item.scale || "1 1 1").split(" ")[0]);

            if (item.auto_rotate === true) {
                isAutoRotating = true;
                modelEl.setAttribute("animation", {
                    property: "rotation",
                    to: `0 360 0`,
                    dur: item.rotate_speed || 10000,
                    easing: "linear",
                    loop: true
                });
            } else {
                isAutoRotating = false;
                modelEl.removeAttribute("animation");
            }

            document.querySelectorAll(".dish-btn")
                .forEach((b, i) => b.classList.toggle("active", i === index));
        };

        carousel.appendChild(btn);
        if (index === 0) btn.click();
    });
}
loadMenu();

// ======================
// RESTRICTED TOUCH ROTATION (Y-AXIS ONLY)
// ======================
let isDragging = false;
let previousTouchX = 0;

function stopAutoRotate() {
    if (isAutoRotating) {
        modelEl.removeAttribute("animation");
        isAutoRotating = false;
    }
}

sceneEl.addEventListener("touchstart", (e) => {
    stopAutoRotate();
    if (e.touches.length === 1) {
        isDragging = true;
        previousTouchX = e.touches[0].clientX;
    }
});

sceneEl.addEventListener("touchmove", (e) => {
    if (!modelEl.getAttribute("gltf-model")) return;
    if (e.touches.length === 1 && isDragging) {
        const currentX = e.touches[0].clientX;
        const deltaX = currentX - previousTouchX;
        currentRotation.y += deltaX * 0.5;
        modelEl.setAttribute("rotation", `0 ${currentRotation.y} 0`);
        previousTouchX = currentX;
    }
});

sceneEl.addEventListener("touchend", () => {
    isDragging = false;
});

// ======================
// SCREENSHOT
// ======================
document.getElementById("screenshot-btn").onclick = () => {
    const canvas = sceneEl.components.screenshot.getCanvas("perspective");
    const link = document.createElement("a");
    link.download = "AR.png";
    link.href = canvas.toDataURL();
    link.click();
};

// ======================
// SHARE
// ======================
document.getElementById("share-btn").onclick = async () => {
    if (navigator.share) {
        await navigator.share({
            title: "AR Menu",
            text: "Check this AR Menu!",
            url: window.location.href
        });
    } else {
        navigator.clipboard.writeText(window.location.href);
        alert("Link copied!");
    }
};

// ======================
// HINT BUBBLE
// ======================
function showHintBubble() {
    const menuBtn = document.getElementById('menu-btn');
    if (!menuBtn) return;

    // Button ki position lo
    const rect = menuBtn.getBoundingClientRect();

    // Bubble banao
    const bubble = document.createElement('div');
    bubble.id = 'hint-bubble';
    bubble.textContent = '📋 Menu & ordering yahan hai';
    document.body.appendChild(bubble);

    // Bubble ki size lo (render hone ke baad)
    requestAnimationFrame(() => {
        const bw = bubble.offsetWidth;
        const bh = bubble.offsetHeight;

        // Button ke paas position — right-aligned, button ke neeche
        const top  = rect.bottom + 10;
        const left = rect.right - bw;

        bubble.style.top  = `${top}px`;
        bubble.style.left = `${left}px`;

        // transform-origin bhi button center pe set karo
        const originX = rect.left + rect.width / 2 - left;
        const originY = rect.top + rect.height / 2 - top;
        bubble.style.transformOrigin = `${originX}px ${originY}px`;

        // Phase 1: expand
        requestAnimationFrame(() => {
            bubble.classList.add('phase-expand');

            // Phase 2: 2.5s baad shrink wapas button mein
            setTimeout(() => {
                bubble.classList.remove('phase-expand');
                bubble.classList.add('phase-shrink');

                // Animation khatam hone ke baad remove karo
                setTimeout(() => bubble.remove(), 500);
            }, 2500);
        });
    });
}

// Page load hone ke 1s baad dikhao
setTimeout(showHintBubble, 1000);
