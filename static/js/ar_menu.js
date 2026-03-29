// clientId — HTML template mein inject hota hai

const modelEl = document.querySelector("#ar-model");
const sceneEl = document.querySelector("a-scene");

let currentRotation = { x: 0, y: 0, z: 0 };
let isAutoRotating = false;
let currentScale = 1;

// ======================
// AR LOADER
// ======================
const loaderEl = document.getElementById('ar-loader');
const loaderCanvas = document.getElementById('loader-canvas');
const lctx = loaderCanvas.getContext('2d');
const lcx = 110, lcy = 90;

const loaderBalls = [
    { rx:70, ry:17, tiltX:0,  tiltZ:0,  color:'#6C63FF', angle:0,           baseSpeed:0.065, dir:1  },
    { rx:70, ry:17, tiltX:0,  tiltZ:0,  color:'#6C63FF', angle:Math.PI,     baseSpeed:0.065, dir:1  },
    { rx:17, ry:70, tiltX:0,  tiltZ:0,  color:'#FF6584', angle:0,           baseSpeed:0.055, dir:-1 },
    { rx:17, ry:70, tiltX:0,  tiltZ:0,  color:'#FF6584', angle:Math.PI,     baseSpeed:0.055, dir:-1 },
    { rx:70, ry:17, tiltX:55, tiltZ:45, color:'#43E97B', angle:0,           baseSpeed:0.040, dir:1  },
    { rx:70, ry:17, tiltX:55, tiltZ:45, color:'#43E97B', angle:Math.PI,     baseSpeed:0.040, dir:1  },
];
loaderBalls.forEach(b => {
    b.drift  = (Math.random() - 0.5) * 0.018;
    b.wobble = Math.random() * Math.PI * 2;
});

let loaderT = 0;
let loaderRunning = true;

function lProject(x3, y3, z3) {
    return { x: lcx + x3, y: lcy - y3 * 0.6 + z3 * 0.4 };
}

function lGetPos(ball) {
    const tx = ball.tiltX * Math.PI / 180;
    const tz = ball.tiltZ * Math.PI / 180;
    const speed = ball.baseSpeed + ball.drift * Math.sin(loaderT * 0.02 + ball.wobble);
    ball.angle += ball.dir * speed;
    let x = ball.rx * Math.cos(ball.angle);
    let y = ball.ry * Math.sin(ball.angle);
    let z = 0;
    let y2 = y * Math.cos(tx) - z * Math.sin(tx);
    let z2 = y * Math.sin(tx) + z * Math.cos(tx);
    let x3 = x * Math.cos(tz) - y2 * Math.sin(tz);
    let y3 = x * Math.sin(tz) + y2 * Math.cos(tz);
    return { p: lProject(x3, y3, z2), depth: z2, angle: ball.angle };
}

function lHexToRgb(hex) {
    return `${parseInt(hex.slice(1,3),16)},${parseInt(hex.slice(3,5),16)},${parseInt(hex.slice(5,7),16)}`;
}

function drawLoader() {
    if (!loaderRunning) return;
    lctx.clearRect(0, 0, loaderCanvas.width, loaderCanvas.height);

    // faint rings
    [[70,17,'rgba(108,99,255,0.15)'],[17,70,'rgba(255,101,132,0.15)'],[45,45,'rgba(67,233,123,0.12)']].forEach(([rx,ry,color]) => {
        lctx.beginPath();
        lctx.ellipse(lcx, lcy, rx, ry, 0, 0, Math.PI*2);
        lctx.strokeStyle = color;
        lctx.lineWidth = 1;
        lctx.stroke();
    });

    let drawBalls = [];
    loaderBalls.forEach(b => {
        const rgb = lHexToRgb(b.color);
        const isVertical = b.rx < b.ry;
        const { p, depth, angle } = lGetPos(b);
        const sinVal = isVertical ? -Math.sin(angle) : Math.sin(angle);
        const size = 3.5 + sinVal * 2.5;
        const alpha = 0.35 + (sinVal + 1) * 0.32;
        drawBalls.push({ x: p.x, y: p.y, size: Math.max(1.5, size), alpha, rgb, depth });
    });

    drawBalls.sort((a, b) => a.depth - b.depth);
    drawBalls.forEach(b => {
        lctx.beginPath();
        lctx.arc(b.x, b.y, b.size, 0, Math.PI*2);
        lctx.fillStyle = `rgba(${b.rgb},${b.alpha})`;
        lctx.fill();
    });

    // center dot
    lctx.beginPath(); lctx.arc(lcx, lcy, 6, 0, Math.PI*2);
    lctx.fillStyle = '#6C63FF'; lctx.fill();
    lctx.beginPath(); lctx.arc(lcx, lcy, 3, 0, Math.PI*2);
    lctx.fillStyle = '#FF6584'; lctx.fill();

    loaderT++;
    requestAnimationFrame(drawLoader);
}

function showLoader() {
    loaderRunning = true;
    loaderEl.classList.remove('hidden');
    drawLoader();
}

function hideLoader() {
    loaderEl.classList.add('hidden');
    setTimeout(() => { loaderRunning = false; }, 400);
}

// Page load pe loader start
drawLoader();

// ======================
// LOAD MENU
// ======================
async function loadMenu() {
    const res = await fetch(`/api/menu/${clientId}`);
    const data = await res.json();
    const carousel = document.getElementById("carousel-wrapper");

    // GLB load events
    modelEl.addEventListener('model-loaded', () => hideLoader());
    modelEl.addEventListener('model-error',  () => hideLoader());

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
            showLoader();
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

    const rect = menuBtn.getBoundingClientRect();

    const bubble = document.createElement('div');
    bubble.id = 'hint-bubble';
    bubble.textContent = '📋 Menu & ordering yahan hai';
    document.body.appendChild(bubble);

    requestAnimationFrame(() => {
        const bw = bubble.offsetWidth;
        const bh = bubble.offsetHeight;

        const top  = rect.bottom + 10;
        const left = rect.right - bw;

        bubble.style.top  = `${top}px`;
        bubble.style.left = `${left}px`;

        const originX = rect.left + rect.width / 2 - left;
        const originY = rect.top + rect.height / 2 - top;
        bubble.style.transformOrigin = `${originX}px ${originY}px`;

        requestAnimationFrame(() => {
            bubble.classList.add('phase-expand');

            setTimeout(() => {
                bubble.classList.remove('phase-expand');
                bubble.classList.add('phase-shrink');
                setTimeout(() => bubble.remove(), 500);
            }, 2500);
        });
    });
}

// Page load hone ke 1s baad dikhao
setTimeout(showHintBubble, 1000);
