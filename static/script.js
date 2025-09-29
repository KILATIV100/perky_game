// Ініціалізація Telegram WebApp
const tg = window.Telegram.WebApp;

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
const soundToggle = document.getElementById('soundToggle'); // ДОДАНО
const vibrationToggle = document.getElementById('vibrationToggle'); // ДОДАНО
const controls = document.getElementById('controls');
const menuTabs = document.querySelectorAll('.menu-tab');
const shopContent = document.getElementById('shopContent'); 
const tabContents = {
    play: document.getElementById('playTab'),
    shop: document.getElementById('shopTab'), 
    settings: document.getElementById('settingsTab')
};

// --- ДОДАНО: Глобальні активи SVG ---
const assets = {};
assets.coffeeBean = new Image();
assets.coffeeBean.src = '/static/coffee.svg'; 
assets.enemyVirus = new Image(); // ДОДАНО: Ворог 1 (статичний)
assets.enemyVirus.src = '/static/enemy_virus.svg'; 
assets.enemyBug = new Image();   // ДОДАНО: Ворог 2 (рухомий)
assets.enemyBug.src = '/static/enemy_bug.svg'; 
const skinImages = {}; // Мапа для зберігання зображень скінів
// ------------------------------------


// Глобальні змінні
let gameState = 'menu';
let player, platforms, coffees, particles, clouds, camera, bonusTimer, gameTimer, enemies; // ДОДАНО ENEMIES
let currentHeight = 0, currentCoffeeCount = 0, gameMode = 'classic', gameSpeedMultiplier = 1; 
let animationId;
let keys = {}, touchControls = { left: false, right: false }, gyroTilt = 0;

// Статистика гравця
let playerStats = {
    user_id: tg.initDataUnsafe?.user?.id || null,
    username: tg.initDataUnsafe?.user?.username || 'Guest',
    first_name: tg.initDataUnsafe?.user?.first_name || 'Player',
    max_height: 0, total_beans: 0, games_played: 0,
    active_skin: 'default_robot.svg'
};

// Налаштування гри
let gameSettings = { gyro: true, gyroSensitivity: 25, sound: true, vibration: true }; // ОНОВЛЕНО

// --- ІНІЦІАЛІЗАЦІЯ ---
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvas);

// --- ГІРОСКОП / НАЛАШТУВАННЯ ---
// ... (requestGyroPermission, handleOrientation, updateGyroToggleUI без змін)

function updateSoundToggleUI() {
    soundToggle.classList.toggle('active', gameSettings.sound);
}
function updateVibrationToggleUI() {
    vibrationToggle.classList.toggle('active', gameSettings.vibration);
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
    updateCamera();
    updateParticles();
    updateEnemies(); // ДОДАНО
    checkCollisions();
    
    if (player.y > camera.y + canvas.height || (gameMode === 'timed' && gameTimer <= 0)) endGame();
}
// ... (updatePlayer, updatePlatforms, updateCamera, updateParticles без змін)

function updateEnemies() {
    enemies.forEach(e => {
        if (e.type === 'bug') {
            // Горизонтальний рух "жука"
            e.x += e.vx * gameSpeedMultiplier;
            if (e.x <= e.range[0] || e.x + e.width >= e.range[1]) {
                e.vx *= -1; // Зміна напрямку
            }
        }
    });
}

function checkCollisions() {
    // ... (перевірка зіткнень з платформами та кавою без змін)

    // --- ПЕРЕВІРКА ЗІТКНЕНЬ З ВОРОГАМИ ---
    enemies = enemies.filter(enemy => {
        // Проста перевірка зіткнення прямокутників
        if (player.x < enemy.x + enemy.width &&
            player.x + player.width > enemy.x &&
            player.y < enemy.y + enemy.height &&
            player.y + player.height > enemy.y) {
            
            playSound('hit_enemy');
            endGame(); // Гра завершується при зіткненні
            return false;
        }
        return true;
    });
    
    // ... (логіка збору кави без змін)
}
function handlePlatformCollision(platform) {
    // ... (логіка зіткнень з платформами)
    vibrate(50);
    playSound('jump'); // ДОДАНО ЗВУК
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
    renderEnemies(); // ДОДАНО
    renderPlayer(); 
    renderParticles();
    ctx.restore();
    
    // ... (відображення таймера)
}

function renderEnemies() {
    enemies.forEach(e => {
        const img = (e.type === 'virus') ? assets.enemyVirus : assets.enemyBug;
        if (img.complete) {
            ctx.drawImage(img, e.x, e.y, e.width, e.height);
        } else {
            // Заглушка для ворога (червоний трикутник)
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
// ... (renderPlayer, renderCoffees, renderClouds, renderParticles без змін)

// --- ЛОГІКА ГРИ ---
function startGame(mode) {
    gameState = 'playing';
    gameMode = mode;
    gameSpeedMultiplier = 1; // Скидаємо за замовчуванням
    if (gameTimer) clearInterval(gameTimer); // Очищаємо старий таймер
    
    platforms = []; coffees = []; particles = []; clouds = []; enemies = []; // ІНІЦІАЛІЗАЦІЯ ВОРОГІВ
    camera = { y: 0 };
    currentHeight = 0; currentCoffeeCount = 0;
    
    // ... (логіка режимів гри)

    player = {
        // ВИПРАВЛЕННЯ: Гравець починає на 150px від низу
        x: canvas.width / 2 - 15, y: canvas.height - 150, 
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
// ... (endGame, saveStatsOnServer, checkBonuses, showBonusPopup, hideBonusPopup без змін)

// --- ГЕНЕРАЦІЯ ОБ'ЄКТІВ ---
// ... (generateInitialPlatforms без змін)

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
        if (Math.random() < 0.1) generateEnemy(y - 50, 'virus'); // 10% шанс статичного ворога
    }
    
    // Рівень складності 2: Вище 1500м
    if (currentHeight >= 1500) {
        bouncy_chance = 0.20; // 20%
        fragile_chance = 0.25; // 25% (особливо небезпечні)
        if (Math.random() < 0.15) generateEnemy(y - 50, 'bug'); // 15% шанс рухомого ворога
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
function generateEnemy(y, type) {
    const x = Math.random() * (canvas.width - 40);
    const width = 40;
    const height = 40;

    let enemy = { x, y, width, height, type };

    if (type === 'bug') {
        // Рухомий ворог
        enemy.vx = (Math.random() > 0.5 ? 1 : -1) * 1.5;
        // Діапазон руху: 20% ширини канвасу
        enemy.range = [Math.max(0, x - canvas.width * 0.2), Math.min(canvas.width - width, x + canvas.width * 0.2)];
    }
    
    enemies.push(enemy);
}
// ... (generateClouds, createParticles без змін)

// --- UI ТА ОБРОБНИКИ ПОДІЙ ---
// ... (updateGameUI, updateRecordsDisplay без змін)

function setupEventListeners() {
    // ... (існуючі обробники)

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
    
    // ... (існуючі обробники меню)
}
// ... (updateStatsDisplayInMenu, loadLeaderboard, loadShop, handleSkinAction, fetchAndUpdateStats, vibrate без змін)

// --- ПОЧАТКОВИЙ ЗАПУСК ---
async function initializeApp() {
    tg.ready();
    await fetchAndUpdateStats(); 
    tg.expand();
    
    resizeCanvas();
    setupEventListeners();
    updateGyroToggleUI();
    updateSoundToggleUI();     // ОНОВЛЕНО
    updateVibrationToggleUI(); // ОНОВЛЕНО
    
    if (gameSettings.gyro) requestGyroPermission(); 
    
    updateStatsDisplayInMenu(); 
    loadLeaderboard(); 
}

initializeApp();
