// Ініціалізація Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// DOM-елементи
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// UI елементи
const coffeeCountEl = document.getElementById('coffeeCount');
const heightScoreEl = document.getElementById('heightScore');
const timeDisplayEl = document.getElementById('timeDisplay');
const timeLeftEl = document.getElementById('timeLeft');
const recordsDisplayEl = document.getElementById('recordsDisplay');
const bestHeightEl = document.getElementById('bestHeight');
const bestCoffeeEl = document.getElementById('bestCoffee');
const powerupIndicatorEl = document.getElementById('powerupIndicator');

// Екрани
const menuScreen = document.getElementById('menuScreen');
const gameOverScreen = document.getElementById('gameOverScreen');
const bonusPopup = document.getElementById('bonusPopup');

// Кнопки
const leftBtn = document.getElementById('leftBtn');
const rightBtn = document.getElementById('rightBtn');
const restartBtn = document.getElementById('restartBtn');
const menuBtn = document.getElementById('menuBtn');
const shopBtn = document.getElementById('shopBtn');
const customizeBtn = document.getElementById('customizeBtn');
const challengesBtn = document.getElementById('challengesBtn');
const gyroToggle = document.getElementById('gyroToggle');

// Таби
const menuTabs = document.querySelectorAll('.menu-tab');
const tabContents = {
    play: document.getElementById('playTab'),
    progress: document.getElementById('progressTab'),
    social: document.getElementById('socialTab'),
    settings: document.getElementById('settingsTab')
};

// Глобальні змінні гри
let gameState = 'menu'; // menu, playing, gameOver
let gameMode = 'classic';
let animationId;

// Об'єкти гри
let player = {};
let platforms = [];
let coffees = [];
let particles = [];
let obstacles = [];
let clouds = [];
let camera = { y: 0 };

// Статистика поточної гри
let currentHeight = 0;
let currentCoffeeCount = 0;
let timeLeft = 60;
let gameTimer;
let bonusTimer;

// Загальна статистика гравця (буде завантажена з сервера)
let playerStats = {
    user_id: tg.initDataUnsafe?.user?.id || null,
    username: tg.initDataUnsafe?.user?.username || 'Guest',
    max_height: 0,
    total_beans: 0,
    games_played: 0
};

// Налаштування гри
let gameSettings = {
    gyro: true,
    gyroSensitivity: 20 // Збільшена чутливість (менше значення = більша чутливість)
};

// Змінні для керування
let keys = {};
let touchControls = { left: false, right: false };
let gyroTilt = 0;

// --- Ініціалізація ---

function resizeCanvas() {
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
}

window.addEventListener('resize', resizeCanvas);

// --- Запит дозволу на гіроскоп ---
async function requestGyroPermission() {
    if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
        try {
            const permissionState = await DeviceOrientationEvent.requestPermission();
            if (permissionState === 'granted') {
                window.addEventListener('deviceorientation', handleOrientation);
                gameSettings.gyro = true;
            } else {
                gameSettings.gyro = false;
            }
        } catch (error) {
            console.error("Помилка запиту дозволу на гіроскоп:", error);
            gameSettings.gyro = false;
        }
    } else {
        // Для пристроїв, що не вимагають дозволу (Android)
        window.addEventListener('deviceorientation', handleOrientation);
    }
    updateGyroToggle();
}

function handleOrientation(event) {
    if (!gameSettings.gyro || gameState !== 'playing') return;
    // gamma: нахил вліво-вправо
    gyroTilt = event.gamma; 
}

function updateGyroToggle() {
    gyroToggle.classList.toggle('active', gameSettings.gyro);
}

// --- Основний ігровий цикл ---

function gameLoop() {
    if (gameState !== 'playing') return;
    
    update();
    render();
    
    animationId = requestAnimationFrame(gameLoop);
}

// --- Логіка оновлення стану гри ---

function update() {
    updatePlayer();
    updatePlatforms();
    updateCamera();
    updateParticles();
    checkCollisions();
    
    // Перевірка на програш
    if (player.y > camera.y + canvas.height + 100) {
        endGame();
    }
}

function updatePlayer() {
    // Горизонтальний рух
    let moveSpeed = player.speed;
    let targetVx = 0;

    if (gameSettings.gyro && gyroTilt !== null) {
        // Керування гіроскопом
        const tilt = Math.max(-gameSettings.gyroSensitivity, Math.min(gameSettings.gyroSensitivity, gyroTilt));
        targetVx = (tilt / gameSettings.gyroSensitivity) * moveSpeed * 1.5;
    } else {
        // Кнопкове керування
        if (keys['ArrowLeft'] || touchControls.left) {
            targetVx = -moveSpeed;
        } else if (keys['ArrowRight'] || touchControls.right) {
            targetVx = moveSpeed;
        }
    }
    
    // Плавний рух
    player.vx += (targetVx - player.vx) * 0.2;
    player.x += player.vx;

    // Гравітація
    player.vy += player.gravity;
    player.y += player.vy;

    // Зациклення екрану
    if (player.x + player.width < 0) player.x = canvas.width;
    if (player.x > canvas.width) player.x = -player.width;
}

function updatePlatforms() {
    // Генерація нових платформ
    while (platforms.length > 0 && platforms[0].y > camera.y - 100) {
        generatePlatform();
    }
    // Видалення старих
    platforms = platforms.filter(p => p.y < camera.y + canvas.height + 50);
}

function updateCamera() {
    const targetY = player.y - canvas.height * 0.4;
    // Плавне слідування камери
    if (targetY < camera.y) {
        camera.y += (targetY - camera.y) * 0.08;
    }
}

function updateParticles() {
    particles = particles.filter(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.1;
        p.life--;
        return p.life > 0;
    });
}

function checkCollisions() {
    // Зіткнення з платформами
    platforms.forEach(platform => {
        if (player.vy > 0 && // Рухається вниз
            player.y + player.height > platform.y &&
            player.y + player.height < platform.y + platform.height + 10 &&
            player.x + player.width > platform.x &&
            player.x < platform.x + platform.width) {

            handlePlatformCollision(platform);
        }
    });

    // Збір кавових зерен
    coffees.forEach((coffee, index) => {
        if (!coffee.collected) {
             const dist = Math.hypot(player.x - coffee.x, player.y - coffee.y);
             if (dist < player.width/2 + 10) {
                 coffee.collected = true;
                 currentCoffeeCount++;
                 updateUI();
                 createParticles(coffee.x, coffee.y, '#D2691E');
                 vibrate(20);
             }
        }
    });
    coffees = coffees.filter(c => !c.collected);
}

function handlePlatformCollision(platform) {
    if (platform.isBouncy && player.isFalling) return; // Ігноруємо відскок, якщо вже падаємо після нього

    player.y = platform.y - player.height;
    
    if (platform.type === 'bouncy') {
        player.vy = -20; // Сильний відскок
        platform.isBouncy = true;
        setTimeout(() => platform.isBouncy = false, 500); // Запобігаємо мульти-відскокам
    } else {
        player.vy = player.jumpPower;
    }

    if (platform.type === 'fragile') {
        platform.isBreaking = true;
        setTimeout(() => {
            platforms = platforms.filter(p => p !== platform);
        }, 300);
    }
    
    vibrate(50);
    createParticles(player.x + player.width / 2, player.y + player.height, '#FFFFFF', 5);
}


// --- Рендеринг ---

function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Зберігаємо контекст для зміщення камери
    ctx.save();
    ctx.translate(0, -camera.y);

    renderClouds();
    renderPlatforms();
    renderCoffees();
    renderPlayer();
    renderParticles();
    
    // Відновлюємо контекст
    ctx.restore();
}

function renderPlayer() {
    ctx.fillStyle = '#8B4513';
    ctx.fillRect(player.x, player.y, player.width, player.height);
    // Очі
    ctx.fillStyle = '#FFD700';
    ctx.fillRect(player.x + 5, player.y + 8, 5, 5);
    ctx.fillRect(player.x + 20, player.y + 8, 5, 5);
}

function renderPlatforms() {
    platforms.forEach(p => {
        if (p.isBreaking) {
            ctx.globalAlpha = 0.5;
        }
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
        ctx.beginPath();
        ctx.arc(cloud.x, cloud.y, cloud.size, 0, Math.PI * 2);
        ctx.arc(cloud.x + cloud.size*0.8, cloud.y, cloud.size*1.2, 0, Math.PI * 2);
        ctx.arc(cloud.x + cloud.size*1.6, cloud.y, cloud.size, 0, Math.PI * 2);
        ctx.fill();

        // Рух хмар
        cloud.x += cloud.speed;
        if (cloud.x > canvas.width + cloud.size * 2) {
            cloud.x = -cloud.size * 2;
        }
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

// --- Логіка гри ---

function startGame(mode) {
    gameState = 'playing';
    gameMode = mode;
    
    // Скидання стану
    platforms = [];
    coffees = [];
    particles = [];
    currentHeight = 0;
    currentCoffeeCount = 0;
    camera.y = 0;
    
    // Ініціалізація гравця
    player = {
        x: canvas.width / 2 - 15,
        y: canvas.height - 100,
        width: 30, height: 30,
        vx: 0, vy: 0,
        speed: 5,
        jumpPower: -12,
        gravity: 0.4,
        isFalling: false // Для логіки зелених блоків
    };
    
    // Генерація початкових об'єктів
    generateInitialPlatforms();
    generateClouds();
    
    // UI
    menuScreen.style.display = 'none';
    gameOverScreen.style.display = 'none';
    updateUI();
    
    // Запуск ігрового циклу
    if (animationId) cancelAnimationFrame(animationId);
    gameLoop();
}

async function endGame() {
    gameState = 'gameOver';
    cancelAnimationFrame(animationId);

    // Зберігаємо результат
    await saveStatsOnServer();
    
    // Відображаємо екран завершення
    document.getElementById('finalHeight').textContent = Math.floor(currentHeight);
    document.getElementById('finalCoffee').textContent = currentCoffeeCount;
    gameOverScreen.style.display = 'flex';
    
    // Перевірка на бонуси
    checkBonuses();
}

async function saveStatsOnServer() {
    if (!playerStats.user_id) {
        console.warn("Немає user_id, статистика не буде збережена.");
        return;
    }
    try {
        const response = await fetch('/save_stats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: playerStats.user_id,
                username: playerStats.username,
                score: Math.floor(currentHeight),
                collected_beans: currentCoffeeCount
            })
        });
        const data = await response.json();
        if (data.success) {
            // Оновлюємо локальну статистику
            playerStats.max_height = data.stats.max_height;
            playerStats.total_beans = data.stats.total_beans;
            playerStats.games_played = data.stats.games_played;
            updateRecordsDisplay();
        }
    } catch (error) {
        console.error("Помилка збереження статистики:", error);
    }
}

function checkBonuses() {
    let bonusData = null;
    if (currentCoffeeCount >= 5000) {
        bonusData = { title: "🎁 Брендована чашка!", instruction: "Покажіть це бариста, щоб отримати безкоштовну брендовану чашку!" };
    } else if (currentCoffeeCount >= 200) {
        bonusData = { title: "🎉 Знижка 5%!", instruction: "Покажіть це бариста, щоб отримати знижку 5% на каву!" };
    } else if (currentCoffeeCount >= 100) {
        bonusData = { title: "🎉 Знижка 2%!", instruction: "Покажіть це бариста, щоб отримати знижку 2% на каву!" };
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
        <button class="close-bonus-btn" id="closeBonusBtn">Закрити</button>
    `;
    bonusPopup.style.display = 'block';

    document.getElementById('closeBonusBtn').onclick = hideBonusPopup;

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
    clearInterval(bonusTimer);
}


// --- Генерація об'єктів ---

function generateInitialPlatforms() {
    platforms.push({ x: canvas.width / 2 - 40, y: canvas.height - 50, width: 80, height: 15, type: 'normal', color: '#A0522D' });
    for (let i = 1; i < 20; i++) {
        generatePlatform(canvas.height - 50 - i * 80);
    }
}

function generatePlatform(yPos) {
    const lastPlatform = platforms[platforms.length - 1];
    const y = yPos || lastPlatform.y - (60 + Math.random() * 60);
    const x = Math.random() * (canvas.width - 80);
    
    let type = 'normal';
    let color = '#A0522D';
    const rand = Math.random();

    if (rand < 0.15) { // 15%
        type = 'bouncy';
        color = '#2ECC71';
    } else if (rand < 0.25) { // 10%
        type = 'fragile';
        color = '#E74C3C';
    }
    
    platforms.push({ x, y, width: 80, height: 15, type, color });

    // Додаємо кавові зерна
    if (Math.random() < 0.5) {
        coffees.push({ x: x + 40, y: y - 20, collected: false });
    }
}

function generateClouds() {
    for (let i = 0; i < 5; i++) {
        clouds.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: 20 + Math.random() * 20,
            speed: 0.2 + Math.random() * 0.3
        });
    }
}

function createParticles(x, y, color, count = 10) {
    for (let i = 0; i < count; i++) {
        particles.push({
            x, y,
            vx: (Math.random() - 0.5) * 4,
            vy: (Math.random() - 0.5) * 4,
            life: 20,
            color
        });
    }
}


// --- UI та Event Listeners ---

function updateUI() {
    const newHeight = Math.max(0, -player.y + canvas.height - 100);
    if (newHeight > currentHeight) {
        currentHeight = newHeight;
    }
    heightScoreEl.textContent = `${Math.floor(currentHeight)}м`;
    coffeeCountEl.textContent = currentCoffeeCount;
}

function updateRecordsDisplay() {
    bestHeightEl.textContent = `${playerStats.max_height}м`;
    bestCoffeeEl.textContent = playerStats.total_beans;
}

function setupEventListeners() {
    // Керування клавіатурою
    window.addEventListener('keydown', e => { keys[e.code] = true; });
    window.addEventListener('keyup', e => { keys[e.code] = false; });

    // Керування дотиком
    leftBtn.addEventListener('touchstart', e => { e.preventDefault(); touchControls.left = true; });
    leftBtn.addEventListener('touchend', e => { e.preventDefault(); touchControls.left = false; });
    rightBtn.addEventListener('touchstart', e => { e.preventDefault(); touchControls.right = true; });
    rightBtn.addEventListener('touchend', e => { e.preventDefault(); touchControls.right = false; });
    
    // Кнопки меню
    document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
        btn.addEventListener('click', () => startGame(btn.dataset.mode));
    });

    restartBtn.addEventListener('click', () => startGame(gameMode));
    menuBtn.addEventListener('click', () => {
        gameState = 'menu';
        gameOverScreen.style.display = 'none';
        menuScreen.style.display = 'flex';
    });

    // Таби
    menuTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const activeTab = tab.dataset.tab;
            menuTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            Object.values(tabContents).forEach(content => content.style.display = 'none');
            tabContents[activeTab].style.display = 'block';

            if (activeTab === 'social') {
                loadLeaderboard();
            }
             if (activeTab === 'progress') {
                updateStatsDisplayInMenu();
            }
        });
    });
    
    // Гіроскоп
    gyroToggle.addEventListener('click', () => {
        if (!gameSettings.gyro) {
            requestGyroPermission();
        } else {
            gameSettings.gyro = false;
            window.removeEventListener('deviceorientation', handleOrientation);
            updateGyroToggle();
        }
    });
}

function updateStatsDisplayInMenu() {
    const grid = document.getElementById('statsGrid');
    grid.innerHTML = `
        <div>🏆 Найкраща висота: <span>${playerStats.max_height}м</span></div>
        <div>☕ Всього зерен: <span>${playerStats.total_beans}</span></div>
        <div>🎮 Всього ігор: <span>${playerStats.games_played}</span></div>
    `;
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
            content.innerHTML = '<p>Рейтинг поки порожній. Станьте першим!</p>';
        }
    } catch (error) {
        content.innerHTML = '<p>Не вдалося завантажити рейтинг.</p>';
        console.error("Помилка завантаження рейтингу:", error);
    }
}


function vibrate(duration) {
    if ('vibrate' in navigator) {
        navigator.vibrate(duration);
    }
}

// --- Початковий запуск ---

async function initializeApp() {
    resizeCanvas();
    setupEventListeners();
    updateGyroToggle();
    
    // Завантажуємо статистику гравця з сервера при першому запуску
    if (playerStats.user_id) {
        try {
            const response = await fetch(`/stats/${playerStats.user_id}`);
            const data = await response.json();
            if (data.success) {
                playerStats = { ...playerStats, ...data.stats };
            }
        } catch (error) {
            console.error("Не вдалося завантажити статистику гравця:", error);
        }
    }
    updateRecordsDisplay();
    updateStatsDisplayInMenu();
}

initializeApp();
