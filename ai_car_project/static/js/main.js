let lastCarTime = 0;
function sendCarCommand(cmd) {
    const now = Date.now();
    if (cmd !== 'stop' && now - lastCarTime < 50) return;
    lastCarTime = now;

    fetch('/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // 【更新】將網頁按鈕送出的 speed 從 60 改成 5
        body: JSON.stringify({ command: cmd, speed: 30 }) 
    }).catch(err => console.error('Car cmd err:', err));
}

let lastCamTime = 0;
function sendCameraCommand(dir) {
    const now = Date.now();
    if (now - lastCamTime < 80) return;
    lastCamTime = now;

    fetch('/camera_control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction: dir })
    }).catch(err => console.error('Cam cmd err:', err));
}

function bindHoldButton(buttonId, command) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;

    const startMove = (e) => { e.preventDefault(); sendCarCommand(command); };
    const stopMove = (e) => { e.preventDefault(); sendCarCommand('stop'); };

    btn.addEventListener('mousedown', startMove);
    btn.addEventListener('mouseup', stopMove);
    btn.addEventListener('mouseleave', stopMove);
    btn.addEventListener('touchstart', startMove, { passive: false });
    btn.addEventListener('touchend', stopMove, { passive: false });
    btn.addEventListener('touchcancel', stopMove, { passive: false });
}

bindHoldButton('btn-up', 'forward');
bindHoldButton('btn-down', 'backward');
bindHoldButton('btn-left', 'left');
bindHoldButton('btn-right', 'right');

const activeKeys = new Set();
window.addEventListener('keydown', (e) => {
    if (e.repeat) return;
    const key = e.key.toLowerCase();
    let cmd = null;

    if (key === 'w') cmd = 'forward';
    else if (key === 's') cmd = 'backward';
    else if (key === 'a') cmd = 'left';
    else if (key === 'd') cmd = 'right';

    if (cmd) {
        activeKeys.add(key);
        sendCarCommand(cmd);
    }

    if (e.key === 'ArrowUp') sendCameraCommand('cam_up');
    else if (e.key === 'ArrowDown') sendCameraCommand('cam_down');
    else if (e.key === 'ArrowLeft') sendCameraCommand('cam_left');
    else if (e.key === 'ArrowRight') sendCameraCommand('cam_right');
});

window.addEventListener('keyup', (e) => {
    const key = e.key.toLowerCase();
    if (activeKeys.has(key)) {
        activeKeys.delete(key);
        if (activeKeys.size === 0) sendCarCommand('stop');
    }
});

document.getElementById('cam-up')?.addEventListener('click', () => sendCameraCommand('cam_up'));
document.getElementById('cam-down')?.addEventListener('click', () => sendCameraCommand('cam_down'));
document.getElementById('cam-left')?.addEventListener('click', () => sendCameraCommand('cam_left'));
document.getElementById('cam-right')?.addEventListener('click', () => sendCameraCommand('cam_right'));
document.getElementById('cam-center')?.addEventListener('click', () => sendCameraCommand('cam_center'));

let autoActive = false;
const autoBtn = document.getElementById('btn-toggle-auto');
const autoStatusText = document.getElementById('auto-status-text');

autoBtn?.addEventListener('click', () => {
    autoActive = !autoActive;
    fetch('/toggle_auto', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable: autoActive })
    })
    .then(res => res.json())
    .then(data => {
        if (data.autonomous) {
            autoBtn.textContent = '🛑 關閉自駕 (切換回手動)';
            autoBtn.style.background = '#e53e3e';
            autoStatusText.textContent = '自駕巡線中 (Autonomous)';
            autoStatusText.className = 'status-on';
        } else {
            autoBtn.textContent = '🚀 啟動自駕巡線';
            autoBtn.style.background = '#38a169';
            autoStatusText.textContent = '手動模式 (Manual)';
            autoStatusText.className = 'status-off';
        }
    });
});

setInterval(() => {
    fetch('/get_status')
    .then(res => res.json())
    .then(data => {
        const offsetVal = document.getElementById('offset-val');
        const indicator = document.getElementById('offset-bar-indicator');
        if (offsetVal) offsetVal.textContent = data.offset;
        if (indicator) {
            let percentage = 50 + (data.offset / 3);
            percentage = Math.max(5, Math.min(95, percentage));
            indicator.style.left = percentage + '%';
        }
    }).catch(() => {});
}, 200);
