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
const shopContent = document.getElementById('shopContent'); 
const tabContents = {
    play: document.getElementById('playTab'),
    // ВИДАЛЕНО: progress: document.getElementById('progressTab'),
    // ВИДАЛЕНО: social: document.getElementById('socialTab'),
    shop: document.getElementById('shopTab'), 
    settings: document.getElementById('settingsTab')
};

// Глобальні змінні
let gameState = 'menu';
let player, platforms, coffees, particles, clouds, camera, bonusTimer, gameTimer; 
let currentHeight = 0, currentCoffeeCount = 0, gameMode = 'classic', gameSpeedMultiplier = 1; 
let animationId;
let keys = {}, touchControls = { left: false, right: false }, gyroTilt = 0;

// Статистика гравця
let playerStats = {
    user_id: tg.initDataUnsafe?.user?.id || null,
    username: tg.initDataUnsafe?.user?.username || 'Guest',
    first_name: tg.initDataUnsafe?.user?.first_name || 'Player',
    max_height: 0, total_beans: 0, games_played: 0,
    active_skin: 'default'
};

// Налаштування гри
let gameSettings = { gyro: true, gyroSensitivity: 25 };

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
    // ОНОВЛЕНО: Додано перевірку таймера для режиму "На час"
    if (player.y > camera.y + canvas.height || (gameMode === 'timed' && gameTimer <= 0)) endGame();
}
function updatePlayer() {
    let targetVx = 0;
    if (gameSettings.gyro && gyroTilt !== null) {
        // Підвищена чутливість гіроскопа
        const tilt = Math.max(-gameSettings.gyroSensitivity, Math.min(gameSettings.gyroSensitivity, gyroTilt));
        targetVx = (tilt / gameSettings.gyroSensitivity) * player.speed * 1.5;
    } else {
        if (keys['ArrowLeft'] || touchControls.left) targetVx = -player.speed;
        if (keys['ArrowRight'] || touchControls.right) targetVx = player.speed;
    }
    player.vx += (targetVx - player.vx) * 0.2; // Плавний рух
    player.x += player.vx * gameSpeedMultiplier; // ОНОВЛЕНО: Застосування множника швидкості
    player.vy += player.gravity;
    player.y += player.vy;
    
    // "Зациклення" екрану
    if (player.x > canvas.width) player.x = -player.width;
    if (player.x + player.width < 0) player.x = canvas.width;
}
function updatePlatforms() {
    const topPlatformY = platforms[platforms.length - 1].y;
    // ОНОВЛЕНО: використовуємо gameSpeedMultiplier для швидкості генерації
    if (topPlatformY > camera.y - 100 / gameSpeedMultiplier) generatePlatform(); 
    platforms = platforms.filter(p => p.y < camera.y + canvas.height + 50);
}
function updateCamera() {
    const targetY = player.y - canvas.height * 0.4;
    if (targetY < camera.y) {
        // ОНОВЛЕНО: камера рухається швидше з множником
        camera.y += (targetY - camera.y) * 0.08 * gameSpeedMultiplier;
        
        // ОНОВЛЕНО: Розрахунок поточної висоти
        const newHeight = Math.max(0, Math.floor((-camera.y) + canvas.height * 0.6));
        if (newHeight > currentHeight) currentHeight = newHeight;
        heightScoreEl.textContent = `${currentHeight}м`;
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
        // Використовуємо більш точну перевірку на зіткнення
        const dist = Math.hypot(player.x + player.width / 2 - coffee.x, player.y + player.height / 2 - coffee.y);
        if (dist < player.width / 2 + 5) { // Радіус зіткнення
            currentCoffeeCount++;
            updateGameUI();
            createParticles(coffee.x, coffee.y, '#D2691E');
            vibrate(20);
            return false; // Видалити зерно
        }
        return true;
    });
}
function handlePlatformCollision(platform) {
    if (player.isFallingAfterBounce) return; // Ігнорувати зіткнення відразу після відскоку

    player.y = platform.y - player.height;
    player.vy = (platform.type === 'bouncy') ? -22 * Math.sqrt(gameSpeedMultiplier) : player.jumpPower; // Посилення стрибка для Bouncy
    
    if (platform.type === 'bouncy') {
        player.isFallingAfterBounce = true;
        setTimeout(() => player.isFallingAfterBounce = false, 300 / gameSpeedMultiplier); // Короткий імунітет
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
    
    // Відображення таймера для режиму "На час"
    if (gameMode === 'timed' && gameState === 'playing') {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.font = '24px Arial';
        ctx.textAlign = 'center';
        // Потрібно відняти camera.y у функції
        ctx.fillText(`⏰ ${gameTimer}`, canvas.width / 2, 40); 
    }
}
function renderPlayer() {
    let color = '#8B4513'; // Default Robot
    let eyeColor = '#FFD700';

    // ОНОВЛЕНО: Логіка відображення скінів
    if (playerStats.active_skin === 'red_hot') {
        color = '#E74C3C';
        eyeColor = '#333';
    } else if (playerStats.active_skin === 'blue_ice') {
        color = '#3498DB';
        eyeColor = '#fff';
    } 
    // Тут може бути додаткова логіка для SVG, якщо є

    ctx.fillStyle = color;
    ctx.fillRect(player.x, player.y, player.width, player.height);
    
    ctx.fillStyle = eyeColor;
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
    // Хмари видно лише в режимах Classic/Timed/Extreme
    if (gameMode === 'night') return; 
    
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    clouds.forEach(cloud => {
        ctx.beginPath();
        ctx.arc(cloud.x, cloud.y, cloud.size, 0, Math.PI * 2);
        ctx.arc(cloud.x + cloud.size * 0.8, cloud.y, cloud.size * 1.2, 0, Math.PI * 2);
        ctx.arc(cloud.x + cloud.size * 1.6, cloud.y, cloud.size, 0, Math.PI * 2);
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
function startGame(mode) {
    gameState = 'playing';
    gameMode = mode;
    gameSpeedMultiplier = 1; // Скидаємо за замовчуванням
    if (gameTimer) clearInterval(gameTimer); // Очищаємо старий таймер
    
    platforms = []; coffees = []; particles = []; clouds = [];
    camera = { y: 0 };
    currentHeight = 0; currentCoffeeCount = 0;
    
    // --- ЛОГІКА РЕЖИМІВ ГРИ ---
    if (mode === 'timed') {
        gameSpeedMultiplier = 2; // Прискорення x2 для "На час"
        gameTimer = 60; // Встановлюємо таймер на 60 секунд
        const timerInterval = setInterval(() => {
            if (gameState !== 'playing') clearInterval(timerInterval);
            gameTimer--;
            if (gameTimer <= 0) {
                clearInterval(timerInterval);
                if (gameState === 'playing') endGame();
            }
        }, 1000);
    } else if (mode === 'extreme') {
        gameSpeedMultiplier = 3; // Прискорення x3 для "Екстремальний"
    }
    
    // Зміна фону для "Нічний" режиму
    if (mode === 'night') {
        canvas.style.background = 'linear-gradient(180deg, #1C305E 0%, #081028 100%)';
    } else {
        // Стандартний фон для "Класичний", "На час" та "Екстремальний"
        canvas.style.background = 'linear-gradient(180deg, #87CEEB 0%, #98FB98 100%)';
    }
    // --- КІНЕЦЬ ЛОГІКИ РЕЖИМІВ ---

    player = {
        x: canvas.width / 2 - 15, y: canvas.height - 100,
        width: 30, height: 30, vx: 0, vy: 0,
        speed: 5, jumpPower: -13, gravity: 0.45,
        isFallingAfterBounce: false
    };

    generateInitialPlatforms();
    generateClouds();

    menuScreen.style.display = 'none';
    gameOverScreen.style.display = 'none'; 
    controls.style.display = (gameSettings.gyro ? 'none' : 'flex');
    updateGameUI();

    if (animationId) cancelAnimationFrame(animationId);
    gameLoop();
}
async function endGame() {
    gameState = 'gameOver';
    cancelAnimationFrame(animationId);
    controls.style.display = 'none';
    
    if (gameTimer) clearInterval(gameTimer); // Зупиняємо таймер
    
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
            playerStats = { ...playerStats, ...data.stats };
            updateRecordsDisplay();
            if (data.stats.active_skin) playerStats.active_skin = data.stats.active_skin; 
        }
    } catch (error) { console.error("Помилка збереження статистики:", error); }
}
function checkBonuses() {
    let bonusData = null;
    if (currentCoffeeCount >= 5000) {
        bonusData = { title: "🎁 Брендована чашка!", instruction: "Покажіть це бариста, щоб отримати приз!" };
    } else if (currentCoffeeCount >= 200) {
        bonusData = { title: "🎉 Знижка 5%!", instruction: "Покажіть це бариста, щоб отримати знижку!" };
    } else if (currentCoffeeCount >= 100) {
        bonusData = { title: "🎉 Знижка 2%!", instruction: "Покажіть це бариста, щоб отримати знижку!" };
    }
    
    if (bonusData) {
        showBonusPopup(bonusData);
    }
}
function showBonusPopup({ title, instruction }) {
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
    const rand = Math.random();

    // --- ЛОГІКА ПРОГРЕСИВНОЇ СКЛАДНОСТІ ---
    
    // Початкові шанси (висота < 500м)
    let bouncy_chance = 0.10; // 10%
    let fragile_chance = 0.08; // 8%

    // Рівень складності 1: Вище 500м
    if (currentHeight >= 500) {
        bouncy_chance = 0.15; // 15%
        fragile_chance = 0.15; // 15%
    }
    
    // Рівень складності 2: Вище 1500м
    if (currentHeight >= 1500) {
        bouncy_chance = 0.20; // 20%
        fragile_chance = 0.25; // 25% (особливо небезпечні)
    }

    // Визначення типу платформи на основі змінених шансів
    if (rand < bouncy_chance) { 
        type = 'bouncy'; 
        color = '#2ECC71'; 
    } else if (rand < (bouncy_chance + fragile_chance)) { 
        type = 'fragile'; 
        color = '#E74C3C'; 
    }
    // В іншому випадку залишається 'normal'
    
    // --- КІНЕЦЬ ЛОГІКИ ПРОГРЕСИВНОЇ СКЛАДНОСТІ ---
    
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
    // currentHeight оновлюється у updateCamera
    coffeeCountEl.textContent = `${currentCoffeeCount}`;
}
function updateRecordsDisplay() {
    bestHeightEl.textContent = `${playerStats.max_height}м`;
}
function setupEventListeners() {
    window.addEventListener('keydown', e => keys[e.code] = true);
    window.addEventListener('keyup', e => keys[e.code] = false);

    leftBtn.addEventListener('touchstart', e => { e.preventDefault(); touchControls.left = true; });
    leftBtn.addEventListener('touchend', e => { e.preventDefault(); touchControls.left = false; });
    rightBtn.addEventListener('touchstart', e => { e.preventDefault(); touchControls.right = true; });
    rightBtn.addEventListener('touchend', e => { e.preventDefault(); touchControls.right = false; });
    
    document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
        btn.addEventListener('click', () => startGame(btn.dataset.mode));
    });
    
    restartBtn.addEventListener('click', () => {
        gameOverScreen.style.display = 'none';
        startGame(gameMode);
    });
    menuBtn.addEventListener('click', () => {
        gameState = 'menu';
        gameOverScreen.style.display = 'none';
        menuScreen.style.display = 'flex';
    });

    menuTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const activeTab = tab.dataset.tab;
            menuTabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.menu-section').forEach(s => s.classList.remove('active'));
            tab.classList.add('active');
            tabContents[activeTab].classList.add('active');
            
            // ОНОВЛЕНО: Запуск функцій для нової структури меню
            if (activeTab === 'play') { 
                updateStatsDisplayInMenu(); // Потрібно оновити статистику та рейтинг, оскільки вони тепер на цій вкладці
                loadLeaderboard(); 
            }
            if (activeTab === 'shop') loadShop(); 
            // ВИДАЛЕНО: 'social' та 'progress' окремих вкладок більше немає
        });
    });
    
    gyroToggle.addEventListener('click', () => {
        if (!gameSettings.gyro) {
            requestGyroPermission();
        } else {
            gameSettings.gyro = false;
            window.removeEventListener('deviceorientation', handleOrientation);
            updateGyroToggleUI();
        }
    });
}
function updateStatsDisplayInMenu() {
    // ОНОВЛЕНО: Функція використовує елементи, які тепер знаходяться у 'playTab'
    const grid = document.getElementById('statsGrid'); 
    const leaderboardContent = document.getElementById('leaderboardContent'); 
    
    // ОНОВЛЕНО: Відображення активного скіна
    grid.innerHTML = `
        <div>🏆 Рекорд: <span>${playerStats.max_height}м</span></div>
        <div>☕ Всього зерен: <span>${playerStats.total_beans}</span></div>
        <div>🎮 Ігор зіграно: <span>${playerStats.games_played}</span></div>
        <div>🤖 Активний скін: <span>${playerStats.active_skin || 'default'}</span></div>`;
        
    // ОНОВЛЕНО: Переконаємося, що рейтинг також завантажується
    if (leaderboardContent.innerHTML === '') {
        loadLeaderboard();
    }
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
// --- НОВА ФУНКЦІОНАЛЬНІСТЬ МАГАЗИНУ ---

async function loadShop() {
    shopContent.innerHTML = '<p>Завантаження магазину...</p>';
    if (!playerStats.user_id) {
        shopContent.innerHTML = '<p>Увійдіть до Telegram-бота, щоб отримати доступ до магазину.</p>';
        return;
    }
    
    try {
        const response = await fetch(`/skins/${playerStats.user_id}`);
        const data = await response.json();
        
        if (data.success && data.skins.length > 0) {
            shopContent.innerHTML = `
                <p class="beans-balance">Ваш баланс: ☕ <span id="userTotalBeans">${playerStats.total_beans}</span></p>
                <div class="shop-grid">
                    ${data.skins.map(skin => {
                        // is_owned === True, якщо скін куплено або він дефолтний
                        const is_owned = skin.is_owned || skin.is_default; 
                        // is_active === True, якщо скін є активним
                        const is_active = skin.is_active; 

                        let button_html = '';
                        if (is_active) {
                            button_html = '<button class="skin-btn active">АКТИВНИЙ</button>';
                        } else if (is_owned) {
                            // Кнопка АКТИВУВАТИ тільки для куплених/дефолтних, але неактивних
                            button_html = `<button class="skin-btn activate-btn" data-id="${skin.id}" data-action="activate">АКТИВУВАТИ</button>`;
                        } else {
                            button_html = `<button class="skin-btn buy-btn" data-id="${skin.id}" data-action="buy">КУПИТИ за ☕ ${skin.price}</button>`;
                        }

                        return `
                            <div class="shop-item ${is_active ? 'item-active' : ''}" data-skin-name="${skin.svg_data}">
                                <div class="skin-icon">${skin.name}</div>
                                ${button_html}
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
            
            // Додаємо обробники для кнопок
            shopContent.querySelectorAll('.skin-btn').forEach(btn => {
                if (btn.dataset.id) {
                    btn.addEventListener('click', () => handleSkinAction(parseInt(btn.dataset.id), btn.dataset.action));
                }
            });
            
        } else {
            shopContent.innerHTML = '<p>Магазин поки порожній.</p>';
        }
    } catch (error) { 
        console.error("Помилка завантаження магазину:", error);
        shopContent.innerHTML = '<p>Не вдалося завантажити магазин.</p>'; 
    }
}

async function handleSkinAction(skin_id, action_type) {
    if (!playerStats.user_id) return;
    
    try {
        const response = await fetch('/skin_action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: playerStats.user_id,
                skin_id: skin_id,
                action_type: action_type
            })
        });
        const data = await response.json();

        if (response.ok) {
            tg.showPopup({ message: data.message });
            // Оновлюємо статистику користувача та магазин
            await fetchAndUpdateStats();
            // Якщо активовано, оновлюємо активний скін в грі
            if (action_type === 'activate' && data.active_skin) {
                 playerStats.active_skin = data.active_skin;
            }
            await loadShop();
        } else {
            tg.showAlert(`Помилка: ${data.detail || data.message}`);
        }
    } catch (error) {
        console.error("Помилка дії зі скіном:", error);
        tg.showAlert("Помилка зв'язку з сервером.");
    }
}

async function fetchAndUpdateStats() {
    if (playerStats.user_id) {
        try {
            const response = await fetch(`/stats/${playerStats.user_id}`);
            const data = await response.json();
            if (data.success) {
                playerStats = { ...playerStats, ...data.stats };
                // Оновлення активного скіна, отриманого з БД
                if (data.stats.active_skin) playerStats.active_skin = data.stats.active_skin; 
            }
        } catch (error) {
            console.error("Не вдалося оновити статистику:", error);
        }
    }
    updateRecordsDisplay();
    // Оновлення балансу в UI, якщо потрібно
    const userTotalBeansEl = document.getElementById('userTotalBeans');
    if (userTotalBeansEl) userTotalBeansEl.textContent = playerStats.total_beans;
}
// --- КІНЕЦЬ НОВОЇ ФУНКЦІОНАЛЬНОСТІ МАГАЗИНУ ---

function vibrate(duration) {
    if ('vibrate' in navigator) {
        navigator.vibrate(duration);
    }
}

// --- ПОЧАТКОВИЙ ЗАПУСК ---
async function initializeApp() {
    resizeCanvas();
    setupEventListeners();
    updateGyroToggleUI();
    
    await fetchAndUpdateStats(); 
    
    if (gameSettings.gyro) requestGyroPermission(); // Запит дозволу після завантаження скіна
    
    updateStatsDisplayInMenu(); // Початкове завантаження контенту вклад
