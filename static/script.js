// Ініціалізація Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// DOM-елементи
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const coffeeCountEl = document.getElementById('coffeeCount');
const heightScoreEl = document.getElementById('heightScore');
const bestHeightEl = document.getElementById('bestHeight');
const menuScreen = document.getElementById('menuScreen');
const gameOverScreen = document.getElementById('gameOverScreen');
const bonusPopup = document.getElementById('bonusPopup');
const leftBtn = document.getElementById('leftBtn');
const rightBtn = document.getElementById('rightBtn');
const restartBtn = document.getElementById('restartBtn');
const menuBtn = document.getElementById('menuBtn');
const gyroToggle = document.getElementById('gyroToggle');
const controls = document.getElementById('controls');
const menuTabs = document.querySelectorAll('.menu-tab');
const tabContents = {
    play: document.getElementById('playTab'),
    progress: document.getElementById('progressTab'),
    social: document.getElementById('socialTab'),
    settings: document.getElementById('settingsTab')
};
const tutorialPopup = document.getElementById('tutorialPopup'); // ДОДАНО
const finalTimeEl = document.getElementById('finalTime'); // ДОДАНО

// Глобальні змінні
let gameState = 'menu';
// ОНОВЛЕНО: ДОДАНО gameSpeedMultiplier та gameTimer
let player, platforms, coffees, particles, clouds, camera, bonusTimer, gameTimer;
let currentHeight = 0, currentCoffeeCount = 0, gameMode = 'classic', gameSpeedMultiplier = 1;
let animationId;
let keys = {}, touchControls = { left: false, right: false }, gyroTilt = 0;

// Статистика гравця
let playerStats = {
    user_id: tg.initDataUnsafe?.user?.id || null,
    username: tg.initDataUnsafe?.user?.username || 'Guest',
    first_name: tg.initDataUnsafe?.user?.first_name || 'Player',
    max_height: 0, total_beans: 0, games_played: 0
};

// Налаштування гри
let gameSettings = { 
    gyro: localStorage.getItem('gyroEnabled') === 'true' || true, 
    gyroSensitivity: 25 
};


// --- ІНІЦІАЛІЗАЦІЯ ---
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvas);

// --- ГІРОСКОП ---
async function requestGyroPermission() {
    if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
        try {
            const permissionState = await DeviceOrientationEvent.requestPermission();
            gameSettings.gyro = (permissionState === 'granted');
            localStorage.setItem('gyroEnabled', gameSettings.gyro);
            if (gameSettings.gyro) window.addEventListener('deviceorientation', handleOrientation);
        } catch (error) { gameSettings.gyro = false; }
    } else if ('DeviceOrientationEvent' in window) {
        window.addEventListener('deviceorientation', handleOrientation);
    } else {
        gameSettings.gyro = false;
    }
    updateGyroToggleUI();
}
function handleOrientation(event) {
    if (!gameSettings.gyro || gameState !== 'playing') return;
    gyroTilt = event.gamma; // Left-right tilt
}
function updateGyroToggleUI() {
    gyroToggle.classList.toggle('active', gameSettings.gyro);
    if (gameSettings.gyro && !window.listenerAdded) {
        window.addEventListener('deviceorientation', handleOrientation);
        window.listenerAdded = true;
    }
}

// --- ГОЛОВНИЙ ЦИКЛ ГРИ ---
function gameLoop() {
    if (gameState !== 'playing') return;
    update();
    render();
    animationId = requestAnimationFrame(gameLoop);
}

// --- ОНОВЛЕННЯ СТАНУ ---
function update() {
    updatePlayer();
    updatePlatforms();
    updateCamera();
    updateParticles();
    checkCollisions();
    
    // Перевірка на завершення гри
    if (player.y > camera.y + canvas.height) endGame();

    // Перевірка таймера для режиму "На час"
    if (gameMode === 'timed' && gameTimer !== null) {
        // Оновлення UI таймера (якщо він відображається)
    }
}
function updatePlayer() {
    let targetVx = 0;
    if (gameSettings.gyro && gyroTilt !== null) {
        const tilt = Math.max(-gameSettings.gyroSensitivity, Math.min(gameSettings.gyroSensitivity, gyroTilt));
        targetVx = (tilt / gameSettings.gyroSensitivity) * player.speed * 1.5;
    } else {
        if (keys['ArrowLeft'] || touchControls.left) targetVx = -player.speed;
        if (keys['ArrowRight'] || touchControls.right) targetVx = player.speed;
    }
    player.vx += (targetVx - player.vx) * 0.2; // Плавний рух
    
    // ЗАСТОСУВАННЯ МНОЖНИКА ШВИДКОСТІ
    player.x += player.vx * gameSpeedMultiplier; 
    player.vy += player.gravity;
    player.y += player.vy;
    
    // "Зациклення" екрану
    if (player.x > canvas.width) player.x = -player.width;
    if (player.x + player.width < 0) player.x = canvas.width;
}
function updatePlatforms() {
    const topPlatformY = platforms.length > 0 ? platforms[platforms.length - 1].y : 0;
    if (topPlatformY > camera.y - 150) generatePlatform(); // Трохи більше запасу для генерації
    platforms = platforms.filter(p => p.y < camera.y + canvas.height + 50);
}
function updateCamera() {
    const newHeight = Math.max(0, -player.y + canvas.height - 100);
    if (newHeight > currentHeight) currentHeight = newHeight; // Оновлення рахунку
    
    const targetY = player.y - canvas.height * 0.4;
    if (targetY < camera.y) {
        camera.y += (targetY - camera.y) * 0.08;
    }
}
function updateParticles() {
    particles = particles.filter(p => {
        p.x += p.vx; p.y += p.vy; p.vy += 0.1; p.life--;
        return p.life > 0;
    });
}
function checkCollisions() {
    platforms.forEach(platform => {
        // Перевірка зіткнення тільки при падінні
        if (player.vy > 0 && 
            player.y + player.height >= platform.y && 
            player.y + player.height <= platform.y + platform.height &&
            player.x + player.width > platform.x && 
            player.x < platform.x + platform.width) {
            handlePlatformCollision(platform);
        }
    });

    coffees = coffees.filter(coffee => {
        if (Math.hypot(player.x + player.width / 2 - coffee.x, player.y + player.height / 2 - coffee.y) < player.width / 2 + 5) {
            currentCoffeeCount++;
            updateGameUI();
            createParticles(coffee.x, coffee.y, '#FFD700');
            vibrate(20);
            return false; // Видалити зерно
        }
        return true;
    });
}
function handlePlatformCollision(platform) {
    if (player.isFallingAfterBounce) return; // Ігнорувати зіткнення відразу після відскоку

    player.y = platform.y - player.height;
    player.vy = (platform.type === 'bouncy') ? -22 : player.jumpPower;
    
    if (platform.type === 'bouncy') {
        player.isFallingAfterBounce = true;
        setTimeout(() => player.isFallingAfterBounce = false, 300); // Короткий імунітет
    }
    
    if (platform.type === 'fragile') {
        platform.isBreaking = true;
        setTimeout(() => platforms = platforms.filter(p => p !== platform), 200);
    }
    
    vibrate(50);
    createParticles(player.x + player.width / 2, player.y + player.height, '#FFF', 5);
}

// --- РЕНДЕРИНГ ---
function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(0, -camera.y);
    renderClouds();
    renderPlatforms();
    renderCoffees();
    renderPlayer();
    renderParticles();
    ctx.restore();
}
function renderPlayer() {
    // Стилізований кавовий робот (квадрат + очі)
    ctx.fillStyle = '#8B4513';
    ctx.fillRect(player.x, player.y, player.width, player.height);
    ctx.fillStyle = '#FFD700';
    ctx.fillRect(player.x + 5, player.y + 8, 5, 5);
    ctx.fillRect(player.x + 20, player.y + 8, 5, 5);
}
function renderPlatforms() {
    platforms.forEach(p => {
        if (p.isBreaking) ctx.globalAlpha = 0.5;
        ctx.fillStyle = p.color;
        ctx.fillRect(p.x, p.y, p.width, p.height);
        ctx.globalAlpha = 1.0;
    });
}
function renderCoffees() {
    ctx.fillStyle = '#D2691E';
    coffees.forEach(c => {
        ctx.beginPath();
        ctx.arc(c.x, c.y, 5, 0, Math.PI * 2);
        ctx.fill();
    });
}
function renderClouds() {
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    clouds.forEach(cloud => {
        // ОНОВЛЕНО: Хмари рухаються відносно камери
        const y_relative = cloud.y - camera.y * 0.5; 
        ctx.beginPath();
        ctx.arc(cloud.x, y_relative, cloud.size, 0, Math.PI * 2);
        ctx.arc(cloud.x + cloud.size * 0.8, y_relative, cloud.size * 1.2, 0, Math.PI * 2);
        ctx.arc(cloud.x + cloud.size * 1.6, y_relative, cloud.size, 0, Math.PI * 2);
        ctx.fill();
        cloud.x += cloud.speed;
        if (cloud.x > canvas.width + cloud.size * 2) cloud.x = -cloud.size * 2;
    });
}
function renderParticles() {
    particles.forEach(p => {
        ctx.globalAlpha = p.life / 20;
        ctx.fillStyle = p.color;
        ctx.fillRect(p.x, p.y, 3, 3);
        ctx.globalAlpha = 1.0;
    });
}

// --- ЛОГІКА ГРИ ---
let timePlayed = 0; // Для режиму "На час"
function startGame(mode) {
    gameState = 'playing';
    gameMode = mode;
    gameSpeedMultiplier = 1; // Скидаємо за замовчуванням
    timePlayed = 0;
    gameTimer = null;
    
    platforms = []; coffees = []; particles = []; clouds = [];
    camera = { y: 0 };
    currentHeight = 0; currentCoffeeCount = 0;

    // --- ЛОГІКА РЕЖИМІВ ГРИ ---
    if (mode === 'timed') {
        gameSpeedMultiplier = 2; // Прискорення x2
        gameTimer = 60; // Встановлюємо таймер
        const timerInterval = setInterval(() => {
            if (gameState !== 'playing') clearInterval(timerInterval);
            gameTimer--;
            updateGameUI(); // Оновлюємо UI таймера
            if (gameTimer <= 0) {
                clearInterval(timerInterval);
                if (gameState === 'playing') endGame();
            }
        }, 1000);
    } else if (mode === 'extreme') {
        gameSpeedMultiplier = 3; // Прискорення x3
    }
    
    // Зміна фону для "Нічний" режиму
    if (mode === 'night') {
        canvas.style.background = 'linear-gradient(180deg, #1C305E 0%, #081028 100%)';
    } else {
        canvas.style.background = 'linear-gradient(180deg, #87CEEB 0%, #98FB98 100%)';
    }
    // --- КІНЕЦЬ ЛОГІКИ РЕЖИМІВ ---


    player = {
        x: canvas.width / 2 - 15, y: canvas.height - 100,
        width: 30, height: 30, vx: 0, vy: 0,
        speed: 5 * gameSpeedMultiplier, // Швидкість руху по горизонталі залежить від режиму
        jumpPower: -13, gravity: 0.45,
        isFallingAfterBounce: false
    };

    generateInitialPlatforms();
    generateClouds();

    menuScreen.style.display = 'none';
    gameOverScreen.style.display = 'none';
    controls.style.display = 'flex';
    updateGameUI();
    vibrate(100);

    if (animationId) cancelAnimationFrame(animationId);
    gameLoop();
}
async function endGame() {
    gameState = 'gameOver';
    cancelAnimationFrame(animationId);
    controls.style.display = 'none';
    
    // Якщо це режим на час, записуємо час
    if (gameMode === 'timed') {
        timePlayed = 60 - (gameTimer || 0);
        finalTimeEl.textContent = `${timePlayed}с`;
    } else {
        finalTimeEl.textContent = `Без обмежень`;
    }

    await saveStatsOnServer();
    
    document.getElementById('finalHeight').textContent = Math.floor(currentHeight);
    document.getElementById('finalCoffee').textContent = currentCoffeeCount;
    gameOverScreen.style.display = 'flex';
    
    checkBonuses();
}
async function saveStatsOnServer() {
    if (!playerStats.user_id) return;
    try {
        const response = await fetch('/save_stats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: playerStats.user_id,
                username: playerStats.username,
                first_name: playerStats.first_name,
                score: Math.floor(currentHeight),
                collected_beans: currentCoffeeCount
            })
        });
        const data = await response.json();
        if (data.success) {
            // Оновлюємо статистику гравця після збереження
            playerStats = { ...playerStats, ...data.stats };
            updateRecordsDisplay();
        }
    } catch (error) { console.error("Помилка збереження статистики:", error); }
}
function checkBonuses() {
    let bonusData = null;
    if (playerStats.total_beans >= 5000) { // Перевірка загальної кількості зерен
        bonusData = { title: "🎁 Брендована чашка!", instruction: "Покажіть це бариста, щоб отримати приз!" };
    } else if (playerStats.total_beans >= 200) {
        bonusData = { title: "🎉 Знижка 5%!", instruction: "Покажіть це бариста, щоб отримати знижку!" };
    } else if (playerStats.total_beans >= 100) {
        bonusData = { title: "🎉 Знижка 2%!", instruction: "Покажіть це бариста, щоб отримати знижку!" };
    }
    
    if (bonusData) {
        showBonusPopup(bonusData);
    }
}
function showBonusPopup({ title, instruction }) {
    // ... (логіка відображення бонусного попапу без змін)
    bonusPopup.innerHTML = `
        <div class="bonus-title">${title}</div>
        <div class="bonus-instruction">${instruction}</div>
        <div class="bonus-timer" id="bonusTimer">Закриється через: 10:00</div>
        <button class="close-bonus-btn">Закрити</button>`;
    bonusPopup.style.display = 'block';
    bonusPopup.querySelector('.close-bonus-btn').onclick = () => hideBonusPopup();

    let timeLeft = 600;
    const timerEl = document.getElementById('bonusTimer');
    bonusTimer = setInterval(() => {
        timeLeft--;
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        timerEl.textContent = `Закриється через: ${minutes}:${seconds.toString().padStart(2, '0')}`;
        if (timeLeft <= 0) hideBonusPopup();
    }, 1000);
}
function hideBonusPopup() {
    bonusPopup.style.display = 'none';
    if (bonusTimer) clearInterval(bonusTimer);
}

// --- ГЕНЕРАЦІЯ ОБ'ЄКТІВ ---
function generateInitialPlatforms() {
    platforms.push({ x: canvas.width / 2 - 40, y: canvas.height - 50, width: 80, height: 15, type: 'normal', color: '#A0522D' });
    for (let i = 0; i < 20; i++) generatePlatform();
}
function generatePlatform() {
    const lastPlatform = platforms[platforms.length - 1];
    const y = lastPlatform.y - (60 + Math.random() * 70);
    const x = Math.random() * (canvas.width - 80);
    
    let type = 'normal', color = '#A0522D';
    let rand = Math.random();
    
    // --- ПРОГРЕСИВНА СКЛАДНІСТЬ (ПЕРЕШКОДИ З'ЯВЛЯЮТЬСЯ З 5 РІВНЯ / 500М) ---
    const difficultyMultiplier = Math.min(1, Math.floor(currentHeight / 500) * 0.2 + 1);
    
    // Шанси збільшуються з висотою
    const bouncyChance = 0.10 * difficultyMultiplier;
    const fragileChance = 0.08 * difficultyMultiplier;

    if (rand < bouncyChance) { 
        type = 'bouncy'; 
        color = '#2ECC71'; 
    } else if (rand < bouncyChance + fragileChance) { 
        type = 'fragile'; 
        color = '#E74C3C'; 
    }
    // --- КІНЕЦЬ ПРОГРЕСИВНОЇ СКЛАДНОСТІ ---
    
    platforms.push({ x, y, width: 80, height: 15, type, color });

    if (type === 'normal' && Math.random() < 0.5) {
        coffees.push({ x: x + 40, y: y - 20 });
    }
}
function generateClouds() {
    clouds = [];
    for (let i = 0; i < 5; i++) {
        clouds.push({
            x: Math.random() * canvas.width, y: camera.y + Math.random() * canvas.height,
            size: 20 + Math.random() * 20, speed: 0.2 + Math.random() * 0.3
        });
    }
}
function createParticles(x, y, color, count = 10) {
    for (let i = 0; i < count; i++) {
        particles.push({
            x, y,
            vx: (Math.random() - 0.5) * 4, vy: (Math.random() - 0.5) * 4,
            life: 20, color
        });
    }
}

// --- UI ТА ОБРОБНИКИ ПОДІЙ ---
function updateGameUI() {
    heightScoreEl.textContent = `${Math.floor(currentHeight)}м`;
    coffeeCountEl.textContent = `☕ ${currentCoffeeCount}`;
    
    // Оновлення таймера в UI під час гри
    if (gameMode === 'timed' && gameTimer !== null) {
        heightScoreEl.textContent = `🕒 ${gameTimer.toString().padStart(2, '0')}с`;
    }
}
function updateRecordsDisplay() {
    bestHeightEl.textContent = `${playerStats.max_height}м`;
}
function setupEventListeners() {
    // ... (обробники клавіатури, тач-керування)
    window.addEventListener('keydown', e => keys[e.code] = true);
    window.addEventListener('keyup', e => keys[e.code] = false);

    leftBtn.addEventListener('touchstart', e => { e.preventDefault(); touchControls.left = true; });
    leftBtn.addEventListener('touchend', e => { e.preventDefault(); touchControls.left = false; });
    rightBtn.addEventListener('touchstart', e => { e.preventDefault(); touchControls.right = true; });
    rightBtn.addEventListener('touchend', e => { e.preventDefault(); touchControls.right = false; });
    
    document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
        btn.addEventListener('click', () => {
            startGame(btn.dataset.mode);
            localStorage.setItem('hasPlayed', 'true'); // Відмічаємо, що гравець грав
            hideTutorial();
        });
    });
    
    restartBtn.addEventListener('click', () => {
        gameOverScreen.style.display = 'none';
        startGame(gameMode);
    });
    menuBtn.addEventListener('click', () => {
        gameState = 'menu';
        gameOverScreen.style.display = 'none';
        menuScreen.style.display = 'flex';
        vibrate(50);
    });

    // ... (обробники вкладок меню та гіроскопа)
    menuTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const activeTab = tab.dataset.tab;
            menuTabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.menu-section').forEach(s => s.classList.remove('active'));
            tab.classList.add('active');
            tabContents[activeTab].classList.add('active');
            
            if (activeTab === 'social') loadLeaderboard();
            if (activeTab === 'progress') updateStatsDisplayInMenu();
        });
    });
    
    gyroToggle.addEventListener('click', () => {
        if (!gameSettings.gyro) {
            requestGyroPermission();
        } else {
            gameSettings.gyro = false;
            localStorage.setItem('gyroEnabled', gameSettings.gyro);
            window.removeEventListener('deviceorientation', handleOrientation);
            updateGyroToggleUI();
        }
        vibrate(10);
    });
    
    // Обробник кнопки туторіалу
    if (document.getElementById('closeTutorialBtn')) {
        document.getElementById('closeTutorialBtn').addEventListener('click', hideTutorial);
    }
}
function updateStatsDisplayInMenu() {
    const grid = document.getElementById('statsGrid');
    grid.innerHTML = `
        <div>🏆 Рекорд: <span>${playerStats.max_height}м</span></div>
        <div>☕ Всього зерен: <span>${playerStats.total_beans}</span></div>
        <div>🎮 Ігор зіграно: <span>${playerStats.games_played}</span></div>`;
}
async function loadLeaderboard() {
    const content = document.getElementById('leaderboardContent');
    content.innerHTML = '<p>Завантаження...</p>';
    try {
        const response = await fetch('/leaderboard');
        const data = await response.json();
        if (data.success && data.leaderboard.length > 0) {
            const emojis = ["🥇", "🥈", "🥉"];
            content.innerHTML = data.leaderboard.map((user, i) => {
                const name = user.username || user.first_name || "Гравець";
                const emoji = emojis[i] || `<b>${i + 1}.</b>`;
                return `<div class="leaderboard-item">${emoji} ${name} - ${user.max_height} м</div>`;
            }).join('');
        } else {
            content.innerHTML = '<p>Рейтинг поки порожній.</p>';
        }
    } catch (error) { 
        content.innerHTML = '<p>Не вдалося завантажити рейтинг.</p>'; 
    }
}
function vibrate(duration) {
    if ('vibrate' in navigator) {
        navigator.vibrate(duration);
    }
}

// --- ТУТОРІАЛ ---
function showTutorial() {
    tutorialPopup.style.display = 'flex';
}
function hideTutorial() {
    tutorialPopup.style.display = 'none';
}

// --- ПОЧАТКОВИЙ ЗАПУСК ---
async function initializeApp() {
    resizeCanvas();
    setupEventListeners();
    updateGyroToggleUI();
    
    if (gameSettings.gyro) requestGyroPermission();
    
    if (playerStats.user_id) {
        try {
            const response = await fetch(`/stats/${playerStats.user_id}`);
            const data = await response.json();
            if (data.success) {
                playerStats = { ...playerStats, ...data.stats };
            }
        } catch (error) {
            console.error("Не вдалося завантажити статистику:", error);
        }
    }
    
    updateRecordsDisplay();
    updateStatsDisplayInMenu();
    
    // Перевірка на перший запуск
    if (localStorage.getItem('hasPlayed') !== 'true') {
        showTutorial();
    }
}

initializeApp();
