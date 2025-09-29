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
const soundToggle = document.getElementById('soundToggle'); 
const vibrationToggle = document.getElementById('vibrationToggle'); 
const pauseBtn = document.getElementById('pauseBtn'); // ВИПРАВЛЕНО: Додано кнопку Паузи
const controls = document.getElementById('controls');
const menuTabs = document.querySelectorAll('.menu-tab');

// ВИПРАВЛЕНО: Використовуємо 3-вкладочну структуру DOM
const shopContent = document.getElementById('shopContent'); 
const tabContents = {
    play: document.getElementById('playTab'),
    shop: document.getElementById('shopTab'), 
    settings: document.getElementById('settingsTab')
};

// Глобальні змінні
let gameState = 'menu';
// ОНОВЛЕНО: Додано enemies та gameSpeedMultiplier
let player, platforms, coffees, particles, clouds, camera, enemies, bonusTimer, gameTimer; 
let currentHeight = 0, currentCoffeeCount = 0, gameMode = 'classic', gameSpeedMultiplier = 1;
let animationId;
let keys = {}, touchControls = { left: false, right: false }, gyroTilt = 0;
// Початкова Y-координата гравця
let INITIAL_PLAYER_Y; 


// Зображення (Assets)
const assets = {};
assets.playerImage = new Image(); assets.playerImage.src = '/static/default_robot.svg'; // ВИПРАВЛЕНО: Базовий скін
assets.coffeeImage = new Image(); assets.coffeeImage.src = '/static/coffee.svg';
assets.virusImage = new Image(); assets.virusImage.src = '/static/enemy_virus.svg';
assets.bugImage = new Image(); assets.bugImage.src = '/static/enemy_bug.svg';
const skinImages = {}; // Мапа для керування скінами


// Статистика гравця
let playerStats = {
    user_id: tg.initDataUnsafe?.user?.id || null,
    username: tg.initDataUnsafe?.user?.username || 'Guest',
    first_name: tg.initDataUnsafe?.user?.first_name || 'Player',
    max_height: 0, total_beans: 0, games_played: 0,
    active_skin: 'default_robot.svg' // ВИПРАВЛЕНО: Додано активний скін
};

// Налаштування гри
let gameSettings = { gyro: true, gyroSensitivity: 25, sound: true, vibration: true };

// --- ІНІЦІАЛІЗАЦІЯ ---
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvas);

function loadAssets() {
    // Всі ассети вже ініціалізовані вище
}

// --- ГІРОСКОП / НАЛАШТУВАННЯ ---
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
// ДОДАНО: Логіка для нових налаштувань
function updateSoundToggleUI() {
    if (soundToggle) soundToggle.classList.toggle('active', gameSettings.sound);
}
function updateVibrationToggleUI() {
    if (vibrationToggle) vibrationToggle.classList.toggle('active', gameSettings.vibration);
}
function playSound(name) {
    if (!gameSettings.sound) return;
    // Тимчасова заглушка для звуку
    console.log(`Sound: ${name} played`);
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
    updateEnemies(); 
    updateCamera();
    updateParticles();
    checkCollisions();
    // ОНОВЛЕНО: Додано перевірку на час
    if (player.y > camera.y + canvas.height || (gameMode === 'timed' && gameTimer <= 0)) endGame();
}
function updatePlayer() {
    let targetVx = 0;
    // ОНОВЛЕНО: Враховуємо gameSpeedMultiplier
    const effectiveSpeed = player.speed * gameSpeedMultiplier; 
    
    if (gameSettings.gyro && gyroTilt !== null) {
        const tilt = Math.max(-gameSettings.gyroSensitivity, Math.min(gameSettings.gyroSensitivity, gyroTilt));
        targetVx = (tilt / gameSettings.gyroSensitivity) * effectiveSpeed * 1.5;
    } else {
        if (keys['ArrowLeft'] || touchControls.left) targetVx = -effectiveSpeed;
        if (keys['ArrowRight'] || touchControls.right) targetVx = effectiveSpeed;
    }
    player.vx += (targetVx - player.vx) * 0.2;
    player.x += player.vx;
    player.vy += player.gravity;
    player.y += player.vy;
    
    if (player.x > canvas.width) player.x = -player.width;
    if (player.x + player.width < 0) player.x = canvas.width;
}
function updatePlatforms() {
    const topPlatformY = platforms[platforms.length - 1].y;
    // ОНОВЛЕНО: Враховуємо gameSpeedMultiplier
    if (topPlatformY > camera.y - 100 / gameSpeedMultiplier) generatePlatform();
    platforms = platforms.filter(p => p.y < camera.y + canvas.height + 50);
}
function updateEnemies() {
    enemies.forEach(e => {
        // ОНОВЛЕНО: Враховуємо gameSpeedMultiplier
        if (e.isMoving) {
            e.x += e.vx * gameSpeedMultiplier;
            if (e.x + e.width > canvas.width || e.x < 0) {
                e.vx = -e.vx;
            }
        }
    });
    enemies = enemies.filter(e => e.y < camera.y + canvas.height + 50);
}
function updateCamera() {
    const targetY = player.y - canvas.height * 0.4;
    if (targetY < camera.y) {
        // ОНОВЛЕНО: Враховуємо gameSpeedMultiplier
        camera.y += (targetY - camera.y) * 0.08 * gameSpeedMultiplier; 
        
        // --- ВИПРАВЛЕНО: НЕКОРЕКТНІ МЕТРИ ---
        const conversion_rate = 100; // 100 ігрових одиниць = 1 метр
        // Використовуємо INITIAL_PLAYER_Y, встановлену на початку гри, як 0
        const rawHeight = INITIAL_PLAYER_Y - player.y; 
        
        const newHeight = Math.max(0, Math.floor(rawHeight / conversion_rate)); 
        
        if (newHeight > currentHeight) currentHeight = newHeight;
        heightScoreEl.textContent = `${currentHeight}м`;
        // ------------------------------------
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
        if (player.vy > 0 && 
            player.y + player.height >= platform.y && 
            player.y + player.height <= platform.y + platform.height &&
            player.x + player.width > platform.x && 
            player.x < platform.x + platform.width) {
            handlePlatformCollision(platform);
        }
    });

    // Колізії з кавою
    coffees = coffees.filter(coffee => {
        const dist = Math.hypot(player.x + player.width/2 - coffee.x, player.y + player.height/2 - coffee.y);
        if (dist < player.width/2 + 10) { 
            currentCoffeeCount++;
            updateGameUI();
            createParticles(coffee.x, coffee.y, '#D2691E');
            vibrate(20);
            return false;
        }
        return true;
    });
    
    // Колізії з ворогами
    enemies = enemies.filter(enemy => {
        if (player.x < enemy.x + enemy.width &&
            player.x + player.width > enemy.x &&
            player.y < enemy.y + enemy.height &&
            player.y + player.height > enemy.y) {
            endGame(); 
            return false;
        }
        return true;
    });
}
function handlePlatformCollision(platform) {
    if (player.isFallingAfterBounce) return;

    player.y = platform.y - player.height;
    // ОНОВЛЕНО: Враховуємо gameSpeedMultiplier
    const jumpPower = (platform.type === 'bouncy') ? -22 * Math.sqrt(gameSpeedMultiplier) : player.jumpPower; 
    player.vy = jumpPower;
    
    if (platform.type === 'bouncy') {
        player.isFallingAfterBounce = true;
        setTimeout(() => player.isFallingAfterBounce = false, 300);
    }
    
    if (platform.type === 'fragile') {
        platform.isBreaking = true;
        setTimeout(() => platforms = platforms.filter(p => p !== platform), 200);
    }
    
    vibrate(50);
    playSound('jump');
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
    renderEnemies(); 
    renderPlayer();
    renderParticles();
    ctx.restore();
}
function renderPlayer() {
    const skinName = playerStats.active_skin; 
    const skinImg = skinImages[skinName];
    const x = player.x;
    const y = player.y;
    const w = player.width;
    const h = player.height;

    // ВИПРАВЛЕНО: Логіка відображення скіна (або заглушки)
    if (skinImg && skinImg.complete) {
        ctx.drawImage(skinImg, x, y, w, h);
        return; 
    }

    // Резервна заглушка (квадрат)
    let color = '#8B4513';
    let eyeColor = '#FFD700';
    
    if (skinName.includes('skin_1.svg')) { 
        color = '#E74C3C'; 
        eyeColor = '#333';
    } else if (skinName.includes('skin_2.svg')) { 
        color = '#3498DB'; 
        eyeColor = '#fff';
    } 

    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);
    
    ctx.fillStyle = eyeColor;
    ctx.fillRect(x + 5, y + 8, 5, 5);
    ctx.fillRect(x + 20, y + 8, 5, 5);
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
    const coffeeImg = assets.coffeeImage; // ВИПРАВЛЕНО: Використовуємо правильну змінну
    
    coffees.forEach(c => {
        if (coffeeImg.complete) {
            ctx.drawImage(coffeeImg, c.x - 7.5, c.y - 7.5, 15, 15);
        } else {
            ctx.fillStyle = '#D2691E';
            ctx.beginPath();
            ctx.arc(c.x, c.y, 5, 0, Math.PI * 2);
            ctx.fill();
        }
    });
}
function renderEnemies() {
    enemies.forEach(e => {
        const img = (e.type === 'virus') ? assets.virusImage : assets.bugImage;
        if (img.complete) {
            ctx.drawImage(img, e.x, e.y, e.width, e.height);
        } else {
            ctx.fillStyle = 'red';
            ctx.beginPath();
            ctx.moveTo(e.x + e.width / 2, e.y);
            ctx.lineTo(e.x + e.width, e.y + e.height);
            ctx.lineTo(e.x, e.y + e.height);
            ctx.closePath();
            ctx.fill();
        }
    });
}
function renderClouds() {
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
    gameSpeedMultiplier = 1;
    if (gameTimer) clearInterval(gameTimer);
    
    platforms = []; coffees = []; particles = []; clouds = []; enemies = []; 
    currentHeight = 0; currentCoffeeCount = 0;
    
    // ... (логіка режимів гри)

    player = {
        // ВИКОРИСТАННЯ РОБОЧИХ КООРДИНАТ ГРАВЦЯ
        x: canvas.width / 2 - 15, y: canvas.height - 100, 
        width: 30, height: 30, vx: 0, vy: 0,
        speed: 5, jumpPower: -13, gravity: 0.45,
        isFallingAfterBounce: false
    };
    
    // ВСТАНОВЛЕННЯ ПОЧАТКОВОЇ Y-КООРДИНАТИ ДЛЯ ТОЧНОГО РОЗРАХУНКУ МЕТРІВ
    INITIAL_PLAYER_Y = player.y;
    
    camera = { 
        y: player.y - canvas.height * 0.4
    };

    generateInitialPlatforms(); 
    generateClouds();

    menuScreen.style.display = 'none';
    gameOverScreen.style.display = 'none'; 
    controls.style.display = (gameSettings.gyro ? 'none' : 'flex');
    pauseBtn.style.display = 'block'; // Показати кнопку паузи
    updateGameUI();

    if (animationId) cancelAnimationFrame(animationId);
    gameLoop();
}

// ... (endGame, saveStatsOnServer, checkBonuses, showBonusPopup, hideBonusPopup без змін)

// --- ГЕНЕРАЦІЯ ОБ'ЄКТІВ ---
function generateInitialPlatforms() {
    // ВИКОРИСТАННЯ РОБОЧОЇ ЛОГІКИ ГЕНЕРАЦІЇ
    platforms.push({ x: canvas.width / 2 - 40, y: canvas.height - 50, width: 80, height: 15, type: 'normal', color: '#A0522D' });
    for (let i = 0; i < 20; i++) generatePlatform();
}

function generatePlatform() {
    const lastPlatform = platforms[platforms.length - 1];
    const y = lastPlatform.y - (60 + Math.random() * 70);
    const x = Math.random() * (canvas.width - 80);
    
    let type = 'normal', color = '#A0522D';
    const rand = Math.random();

    // ВИПРАВЛЕНО: Інтеграція логіки складності та ворогів
    let bouncy_chance = 0.10; 
    let fragile_chance = 0.08; 

    if (currentHeight >= 5) { // Зменшення порогу для тесту
        bouncy_chance = 0.15; 
        fragile_chance = 0.15;
        if (Math.random() < 0.1) generateEnemy(y - 50, 'virus'); 
    }
    
    if (currentHeight >= 15) { // Зменшення порогу для тесту
        bouncy_chance = 0.20; 
        fragile_chance = 0.25; 
        if (Math.random() < 0.15) generateEnemy(y - 50, 'bug'); 
    }

    if (rand < bouncy_chance) { 
        type = 'bouncy'; 
        color = '#2ECC71'; 
    } else if (rand < (bouncy_chance + fragile_chance)) { 
        type = 'fragile'; 
        color = '#E74C3C'; 
    }
    
    platforms.push({ x, y, width: 80, height: 15, type, color });

    if (type === 'normal' && Math.random() < 0.5) {
        coffees.push({ x: x + 40, y: y - 20 });
    }
}
function generateEnemy(y, type) {
    const x = Math.random() * (canvas.width - 40);
    const width = 40;
    const height = 40;

    let enemy = { x, y, width, height, type, isMoving: (type === 'bug') };

    if (type === 'bug') {
        enemy.vx = (Math.random() > 0.5 ? 1 : -1) * 1.5;
        enemy.range = [Math.max(0, x - canvas.width * 0.2), Math.min(canvas.width - width, x + canvas.width * 0.2)];
    }
    
    enemies.push(enemy);
}
// ... (generateClouds, createParticles без змін)

// --- UI ТА ОБРОБНИКИ ПОДІЙ ---
function updateGameUI() {
    // currentHeight оновлюється у updateCamera
    coffeeCountEl.textContent = `${currentCoffeeCount}`;
}
function updateRecordsDisplay() {
    bestHeightEl.textContent = `${playerStats.max_height}м`;
}
function goToMenu() {
    // Функція паузи та повернення в меню
    gameState = 'menu';
    cancelAnimationFrame(animationId);
    controls.style.display = 'none';
    pauseBtn.style.display = 'none';
    menuScreen.style.display = 'flex';
}
// ... (setupEventListeners та всі інші функції без змін)

function setupEventListeners() {
    // Обробники клавіш та дотиків без змін
    window.addEventListener('keydown', e => keys[e.code] = true);
    window.addEventListener('keyup', e => keys[e.code] = false);

    leftBtn.addEventListener('touchstart', e => { e.preventDefault(); touchControls.left = true; });
    leftBtn.addEventListener('touchend', e => { e.preventDefault(); touchControls.left = false; });
    rightBtn.addEventListener('touchstart', e => { e.preventDefault(); touchControls.right = true; });
    rightBtn.addEventListener('touchend', e => { e.preventDefault(); touchControls.right = false; });
    
    // Обробники кнопок режимів гри без змін
    document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
        btn.addEventListener('click', () => startGame(btn.dataset.mode));
    });
    
    // Обробники кнопок кінця гри без змін
    restartBtn.addEventListener('click', () => {
        gameOverScreen.style.display = 'none';
        startGame(gameMode);
    });
    menuBtn.addEventListener('click', () => {
        gameState = 'menu';
        gameOverScreen.style.display = 'none';
        menuScreen.style.display = 'flex';
    });
    
    // --- ДОДАНО: ОБРОБНИК КНОПКИ ПАУЗИ ---
    if (pauseBtn) {
        pauseBtn.addEventListener('click', goToMenu);
    }
    // ------------------------------------

    // --- ДОДАНО: ОБРОБНИКИ НАЛАШТУВАНЬ ---
    if (soundToggle) {
        soundToggle.addEventListener('click', () => {
            gameSettings.sound = !gameSettings.sound;
            updateSoundToggleUI();
        });
    }
    if (vibrationToggle) {
        vibrationToggle.addEventListener('click', () => {
            gameSettings.vibration = !gameSettings.vibration;
            updateVibrationToggleUI();
            if (gameSettings.vibration) vibrate(100);
        });
    }

    // Обробники кнопок меню (ОНОВЛЕНО для 3 вкладок)
    menuTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const activeTab = tab.dataset.tab;
            
            // Логіка перемикання вкладок
            menuTabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.menu-section').forEach(s => s.classList.remove('active'));
            tab.classList.add('active');
            
            // Вкладка "Гра" містить все, включаючи статистику і рейтинг
            if (activeTab === 'play') { 
                document.getElementById('playTab').classList.add('active'); 
                updateStatsDisplayInMenu(); 
                loadLeaderboard(); 
            } else if (activeTab === 'shop') {
                document.getElementById('shopTab').classList.add('active'); 
                loadShop(); 
            } else if (activeTab === 'settings') {
                document.getElementById('settingsTab').classList.add('active'); 
            }
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
    
    // ОНОВЛЕНО: Відображення активного скіна
    grid.innerHTML = `
        <div>🏆 Рекорд: <span>${playerStats.max_height}м</span></div>
        <div>☕ Всього зерен: <span>${playerStats.total_beans}</span></div>
        <div>🎮 Ігор зіграно: <span>${playerStats.games_played}</span></div>
        <div>🤖 Активний скін: <span>${playerStats.active_skin.replace('.svg', '') || 'default'}</span></div>`;
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
        
        // Попереднє завантаження скінів у кеш (для renderPlayer)
        data.skins.forEach(skin => {
            if (!skinImages[skin.svg_data]) {
                const img = new Image();
                img.src = `/static/${skin.svg_data}`;
                skinImages[skin.svg_data] = img;
            }
        });
        
        if (data.success && data.skins.length > 0) {
            shopContent.innerHTML = `
                <p class="beans-balance">Ваш баланс: ☕ <span id="userTotalBeans">${playerStats.total_beans}</span></p>
                <div class="shop-grid">
                    ${data.skins.map(skin => {
                        const is_owned = skin.is_owned || skin.is_default; 
                        const is_active = skin.is_active; 

                        let button_html = '';
                        // Вставка зображення для скіна
                        const skinImageHtml = `<img src="/static/${skin.svg_data}" alt="${skin.name}" class="shop-skin-img">`;

                        if (is_active) {
                            button_html = '<button class="skin-btn active">АКТИВНИЙ</button>';
                        } else if (is_owned) {
                            button_html = `<button class="skin-btn activate-btn" data-id="${skin.id}" data-action="activate">АКТИВУВАТИ</button>`;
                        } else {
                            button_html = `<button class="skin-btn buy-btn" data-id="${skin.id}" data-action="buy">КУПИТИ за ☕ ${skin.price}</button>`;
                        }

                        return `
                            <div class="shop-item ${is_active ? 'item-active' : ''}" data-skin-name="${skin.svg_data}">
                                <div class="skin-icon">${skinImageHtml}</div> 
                                <div class="skin-name-text">${skin.name}</div>
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
            content.innerHTML = '<p>Магазин поки порожній.</p>';
        }
    } catch (error) { 
        console.error("Помилка завантаження магазину:", error);
        content.innerHTML = '<p>Не вдалося завантажити магазин.</p>'; 
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
    if (gameSettings.vibration && 'vibrate' in navigator) { // ОНОВЛЕНО: Перевірка налаштувань
        navigator.vibrate(duration);
    }
}

// --- ПОЧАТКОВИЙ ЗАПУСК ---
async function initializeApp() {
    // --- ВИПРАВЛЕННЯ: РОЗГОРТАННЯ ЕКРАНА ---
    tg.ready();
    await fetchAndUpdateStats(); 
    tg.expand();
    // ----------------------------------------
    
    resizeCanvas();
    setupEventListeners();
    updateGyroToggleUI();
    updateSoundToggleUI();     // ОНОВЛЕНО
    updateVibrationToggleUI(); // ОНОВЛЕНО
    
    if (gameSettings.gyro) requestGyroPermission(); 
    
    // ОНОВЛЕНО: Завантаження контенту вкладки "Гра" при запуску
    updateStatsDisplayInMenu(); 
    loadLeaderboard(); 
}

initializeApp();
