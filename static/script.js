// Initialize Telegram WebApp
if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
}

// Game variables
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

let gameState = 'menu'; // menu, playing, gameOver
let gameMode = 'classic';
let animationId;

// Game objects
let player = {};
let platforms = [];
let coffees = [];
let particles = [];
let obstacles = [];
let camera = { y: 0, targetY: 0 };

// Game stats
let score = 0;
let height = 0;
let coffeeCount = 0;
let timeLeft = 60;
let gameTimer;
let bonusTimer;
let bonusTimeLeft = 0;

// Records system
let gameStats = {
    bestHeight: 0,
    bestCoffee: 0,
    gamesPlayed: 0,
    totalCoffee: 0,
    coins: 0,
    experience: 0,
    level: 1
};

// Bonus system
let bonusesShown = {
    discount2: false,
    discount5: false,
    brandedCup: false
};

// Input handling
let keys = {};
let touchControls = { left: false, right: false };
let gyroEnabled = false;
let gyroTilt = 0;

// Settings
let gameSettings = {
    gyro: true,
    sound: true,
    vibration: true,
    autoSeason: true,
    showFPS: false
};


// --- INITIALIZATION & SETUP ---

// Resize canvas to fit container
function resizeCanvas() {
    const container = canvas.parentElement;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
}

// Game modes configuration
const gameModes = {
    classic: { name: 'Класичний', background: 'linear-gradient(180deg, #87CEEB 0%, #98FB98 100%)', platformColor: '#8B4513', timed: false, obstacles: false },
    timed: { name: 'На час', background: 'linear-gradient(180deg, #FF6B6B 0%, #FFE66D 100%)', platformColor: '#D2691E', timed: true, obstacles: false },
    night: { name: 'Нічний', background: 'linear-gradient(180deg, #2C3E50 0%, #34495E 100%)', platformColor: '#7F8C8D', timed: false, obstacles: false },
    extreme: { name: 'Екстремальний', background: 'linear-gradient(180deg, #8E2DE2 0%, #4A00E0 100%)', platformColor: '#E74C3C', timed: false, obstacles: true }
};

// Initialize player state
function initPlayer() {
    player = {
        x: canvas.width / 2,
        y: canvas.height - 100,
        width: 30,
        height: 30,
        vx: 0,
        vy: 0,
        onGround: false,
        jumpPower: -15,
        speed: 5,
        color: '#FF6B6B'
    };
}

// Generate platforms
function initPlatforms() {
    platforms = [];
    obstacles = [];
    const platformWidth = 80;
    const platformHeight = 15;

    // Starting platform
    platforms.push({ x: canvas.width / 2 - platformWidth / 2, y: canvas.height - 50, width: platformWidth, height: platformHeight, type: 'normal', broken: false });

    for (let i = 1; i < 50; i++) {
        let platformType = 'normal';
        const rand = Math.random();
        
        // Platform type distribution (bonus removed, probabilities reduced)
        if (rand < 0.08) platformType = 'bouncy';      // 8% bouncy
        else if (rand < 0.14) platformType = 'fragile'; // 6% fragile

        platforms.push({
            x: Math.random() * (canvas.width - platformWidth),
            y: canvas.height - 50 - (i * 120),
            width: platformWidth,
            height: platformHeight,
            type: platformType,
            broken: false,
            bounceAnimation: 0
        });
    }
}

// Generate coffee beans
function initCoffees() {
    coffees = [];
    platforms.forEach((platform, index) => {
        if (index > 0 && Math.random() < 0.7) {
            coffees.push({ x: platform.x + platform.width / 2 - 10, y: platform.y - 25, width: 20, height: 20, collected: false, bounce: 0 });
        }
    });
}


// --- DATA & STATE MANAGEMENT ---

function loadStats() {
    const saved = localStorage.getItem('perkyCoffeeStats');
    if (saved) {
        gameStats = { ...gameStats, ...JSON.parse(saved) };
    }
    updateStatsDisplay();
}

function saveStats() {
    localStorage.setItem('perkyCoffeeStats', JSON.stringify(gameStats));
}

function updateStatsDisplay() {
    document.getElementById('statsBestHeight').textContent = gameStats.bestHeight;
    document.getElementById('statsBestCoffee').textContent = gameStats.bestCoffee;
    document.getElementById('statsGamesPlayed').textContent = gameStats.gamesPlayed;
    document.getElementById('statsTotalCoffee').textContent = gameStats.totalCoffee;
    document.getElementById('statsCoins').textContent = gameStats.coins;
    document.getElementById('statsLevel').textContent = gameStats.level;
    document.getElementById('bestHeight').textContent = gameStats.bestHeight;
    document.getElementById('bestCoffee').textContent = gameStats.bestCoffee;
}

function loadSettings() {
    const saved = localStorage.getItem('perkyCoffeeSettings');
    if (saved) {
        gameSettings = { ...gameSettings, ...JSON.parse(saved) };
    }
    updateSettingsDisplay();
}

function saveSettings() {
    localStorage.setItem('perkyCoffeeSettings', JSON.stringify(gameSettings));
}

function updateSettingsDisplay() {
    document.getElementById('gyroToggle').classList.toggle('active', gameSettings.gyro);
    document.getElementById('soundToggle').classList.toggle('active', gameSettings.sound);
    document.getElementById('vibrationToggle').classList.toggle('active', gameSettings.vibration);
    document.getElementById('autoSeasonToggle').classList.toggle('active', gameSettings.autoSeason);
    document.getElementById('fpsToggle').classList.toggle('active', gameSettings.showFPS);
    gyroEnabled = gameSettings.gyro;
}


// --- GAME FLOW ---

function startGame(mode) {
    gameMode = mode;
    gameState = 'playing';
    
    // Reset stats for the current game
    score = 0;
    height = 0;
    coffeeCount = 0;
    timeLeft = 60;
    bonusesShown = { discount2: false, discount5: false, brandedCup: false };
    
    // Apply mode styling and configs
    const modeConfig = gameModes[mode];
    document.querySelector('.game-container').style.background = modeConfig.background;
    
    // Initialize game elements
    initPlayer();
    initPlatforms();
    initCoffees();
    camera.y = 0;
    camera.targetY = 0;
    particles = [];
    
    // Hide menus, show game UI
    document.getElementById('menuScreen').style.display = 'none';
    document.getElementById('gameOverScreen').style.display = 'none';
    document.getElementById('timeDisplay').style.display = modeConfig.timed ? 'block' : 'none';
    
    if (modeConfig.timed) startTimer();
    
    // Start game loop
    gameLoop();
}

function endGame() {
    gameState = 'gameOver';
    
    if (gameTimer) clearInterval(gameTimer);
    if (animationId) cancelAnimationFrame(animationId);
    
    // Update and save persistent stats
    gameStats.gamesPlayed++;
    gameStats.totalCoffee += coffeeCount;
    
    let newRecords = [];
    if (height > gameStats.bestHeight) {
        gameStats.bestHeight = height;
        newRecords.push('висота');
    }
    if (coffeeCount > gameStats.bestCoffee) {
        gameStats.bestCoffee = coffeeCount;
        newRecords.push('кавові зерна');
    }
    
    saveStats();
    updateStatsDisplay();
    
    // Show game over screen with final scores
    document.getElementById('finalCoffee').textContent = coffeeCount;
    document.getElementById('finalHeight').textContent = height;
    document.getElementById('finalTime').style.display = gameModes[gameMode].timed ? 'block' : 'none';
    if (gameModes[gameMode].timed) {
        document.getElementById('timeSpent').textContent = 60 - timeLeft;
    }
    
    const existingRecord = document.querySelector('.new-record-message');
    if (existingRecord) existingRecord.remove();
    
    if (newRecords.length > 0) {
        const recordMessage = document.createElement('div');
        recordMessage.className = 'new-record-message';
        recordMessage.style.cssText = `color: #FFD700; font-size: 18px; font-weight: bold; margin: 15px 0; animation: recordGlow 1s ease-in-out infinite alternate;`;
        recordMessage.textContent = `🏆 Новий рекорд: ${newRecords.join(', ')}!`;
        document.querySelector('.final-score').appendChild(recordMessage);
    }
    
    document.getElementById('gameOverScreen').style.display = 'flex';
    
    // Check for bonuses after the game ends
    checkBonuses();
}

function gameLoop() {
    if (gameState !== 'playing') return;
    update();
    render();
    animationId = requestAnimationFrame(gameLoop);
}


// --- UPDATE & RENDER ---

function update() {
    // Player movement
    let moveSpeed = player.speed;
    if (keys['ArrowLeft'] || touchControls.left) player.vx = -moveSpeed;
    else if (keys['ArrowRight'] || touchControls.right) player.vx = moveSpeed;
    else if (gyroEnabled && Math.abs(gyroTilt) > 0.1) player.vx = gyroTilt * moveSpeed;
    else player.vx *= 0.8; // Friction

    player.vy += 0.8; // Gravity
    player.x += player.vx;
    player.y += player.vy;

    // Screen wrapping
    if (player.x < -player.width) player.x = canvas.width;
    if (player.x > canvas.width) player.x = -player.width;

    // Platform collision
    player.onGround = false;
    platforms.forEach(platform => {
        if (platform.broken) return;
        if (player.vy > 0 &&
            player.x < platform.x + platform.width &&
            player.x + player.width > platform.x &&
            player.y + player.height > platform.y &&
            player.y + player.height < platform.y + platform.height) {
            
            player.y = platform.y - player.height;
            player.onGround = true;
            createJumpParticles(player.x + player.width/2, player.y + player.height);
            vibrate([50]);

            switch (platform.type) {
                case 'bouncy':
                    player.vy = player.jumpPower * 1.5;
                    platform.bounceAnimation = 10;
                    break;
                case 'fragile':
                    player.vy = player.jumpPower;
                    platform.broken = true;
                    break;
                default:
                    player.vy = player.jumpPower;
            }
        }
        if (platform.bounceAnimation > 0) platform.bounceAnimation--;
    });

    // Coffee collection
    coffees.forEach(coffee => {
        if (!coffee.collected &&
            player.x < coffee.x + coffee.width &&
            player.x + player.width > coffee.x &&
            player.y < coffee.y + coffee.height &&
            player.y + player.height > coffee.y) {
            
            coffee.collected = true;
            coffeeCount++;
            score += 10;
            gameStats.experience += 5;
            createCollectionParticles(coffee.x + coffee.width/2, coffee.y + coffee.height/2);
            vibrate([20]);
        }
        coffee.bounce += 0.1;
    });

    // Camera follow
    camera.targetY = player.y - canvas.height * 0.6;
    if (camera.targetY < camera.y) {
        camera.y += (camera.targetY - camera.y) * 0.1;
    }

    // Update height score
    const newHeight = Math.max(height, Math.floor((canvas.height - player.y) / 10));
    if (newHeight > height) {
        height = newHeight;
        if (height > gameStats.bestHeight) document.getElementById('bestHeight').classList.add('new-record');
    }

    // Update particles
    particles = particles.filter(p => {
        p.x += p.vx; p.y += p.vy; p.vy += 0.2; p.life--;
        return p.life > 0;
    });

    // Game over condition
    if (player.y > camera.y + canvas.height + 100) endGame();

    // Update UI
    document.getElementById('coffeeCount').textContent = coffeeCount;
    document.getElementById('heightScore').textContent = height;
    if (coffeeCount > gameStats.bestCoffee) document.getElementById('bestCoffee').classList.add('new-record');
}

function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(0, -camera.y);

    // Draw game elements
    platforms.forEach(p => { if (!p.broken) drawPlatform(p) });
    coffees.forEach(c => { if (!c.collected) drawCoffee(c) });
    drawPlayer();
    particles.forEach(p => {
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.life / p.maxLife;
        ctx.fillRect(p.x, p.y, p.size, p.size);
    });
    ctx.globalAlpha = 1;

    ctx.restore();
}

// --- DRAWING FUNCTIONS ---

function drawPlayer() {
    // A more detailed robot design
    const bodyColor = '#B0C4DE';
    const headColor = '#D3D3D3';
    const eyeColor = '#FF4500';

    // Body
    ctx.fillStyle = bodyColor;
    ctx.fillRect(player.x, player.y + 10, player.width, player.height - 10);
    // Head
    ctx.fillStyle = headColor;
    ctx.fillRect(player.x + 5, player.y, player.width - 10, 12);
    // Eye
    ctx.fillStyle = eyeColor;
    ctx.beginPath();
    ctx.arc(player.x + player.width / 2, player.y + 6, 4, 0, Math.PI * 2);
    ctx.fill();
    // Antenna
    ctx.strokeStyle = '#696969';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(player.x + player.width / 2, player.y);
    ctx.lineTo(player.x + player.width / 2, player.y - 5);
    ctx.stroke();
    // Antenna light
    ctx.fillStyle = '#ADFF2F';
    ctx.beginPath();
    ctx.arc(player.x + player.width / 2, player.y - 7, 3, 0, Math.PI * 2);
    ctx.fill();
}


function drawPlatform(platform) {
    switch (platform.type) {
        case 'bouncy': ctx.fillStyle = '#4CAF50'; break;
        case 'fragile': ctx.fillStyle = '#F44336'; break;
        default: ctx.fillStyle = gameModes[gameMode].platformColor;
    }
    
    let yOffset = platform.type === 'bouncy' && platform.bounceAnimation > 0 ? Math.sin(platform.bounceAnimation * 0.5) * 3 : 0;
    ctx.fillRect(platform.x, platform.y + yOffset, platform.width, platform.height);
}

function drawCoffee(coffee) {
    const bounceOffset = Math.sin(coffee.bounce) * 3;
    const centerX = coffee.x + coffee.width / 2;
    const centerY = coffee.y + coffee.height / 2 + bounceOffset;
    
    // Gradient for coffee bean
    const gradient = ctx.createRadialGradient(centerX - 3, centerY - 3, 0, centerX, centerY, coffee.width / 2);
    gradient.addColorStop(0, '#D2691E');
    gradient.addColorStop(0.7, '#8B4513');
    gradient.addColorStop(1, '#654321');
    
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.ellipse(centerX, centerY, coffee.width / 2, coffee.height / 2, 0, 0, Math.PI * 2);
    ctx.fill();
}

// --- PARTICLE EFFECTS ---

function createJumpParticles(x, y) {
    for (let i = 0; i < 8; i++) {
        particles.push({ x, y, vx: (Math.random() - 0.5) * 6, vy: Math.random() * -3, size: Math.random() * 4 + 2, color: '#FFD700', life: 30, maxLife: 30 });
    }
}

function createCollectionParticles(x, y) {
    for (let i = 0; i < 12; i++) {
        particles.push({ x, y, vx: (Math.random() - 0.5) * 8, vy: (Math.random() - 0.5) * 8, size: Math.random() * 3 + 1, color: '#8B4513', life: 40, maxLife: 40 });
    }
}


// --- UI & BONUSES ---

function checkBonuses() {
    if (coffeeCount >= 50 && !bonusesShown.discount2) {
        showBonus('discount2', '2% знижка на каву!', 'Покажіть це бариста для отримання знижки 2% на напій.');
        bonusesShown.discount2 = true;
    } else if (coffeeCount >= 100 && !bonusesShown.discount5) {
        showBonus('discount5', '5% знижка на каву!', 'Покажіть це бариста для отримання знижки 5% на напій.');
        bonusesShown.discount5 = true;
    } else if (coffeeCount >= 5000 && !bonusesShown.brandedCup) {
        showBonus('brandedCup', '🥤 Брендований стакан!', 'Покажіть це бариста для отримання безкоштовного стакану Perky Coffee!');
        bonusesShown.brandedCup = true;
    }
}

function showBonus(type, title, instruction) {
    if (gameState !== 'gameOver') return;
    document.getElementById('bonusTitle').textContent = '🎁 ' + title;
    document.getElementById('bonusContent').innerHTML = `<div style="font-size: 20px; margin: 10px 0;">☕ Зібрано ${coffeeCount} зерен!</div>`;
    document.getElementById('bonusInstruction').textContent = instruction;
    document.getElementById('bonusPopup').style.display = 'block';

    bonusTimeLeft = 600; // 10 minutes
    updateBonusTimer();
    bonusTimer = setInterval(() => {
        bonusTimeLeft--;
        updateBonusTimer();
        if (bonusTimeLeft <= 0) closeBonusPopup();
    }, 1000);
}

function updateBonusTimer() {
    const minutes = Math.floor(bonusTimeLeft / 60);
    const seconds = bonusTimeLeft % 60;
    document.getElementById('bonusTimer').textContent = `⏰ Закриється через: ${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function closeBonusPopup() {
    document.getElementById('bonusPopup').style.display = 'none';
    if (bonusTimer) clearInterval(bonusTimer);
}

function switchMenuTab(tabName) {
    document.querySelectorAll('.menu-tab').forEach(tab => tab.classList.toggle('active', tab.dataset.tab === tabName));
    document.querySelectorAll('#playTab, #progressTab, #socialTab, #settingsTab').forEach(content => content.style.display = 'none');
    document.getElementById(tabName + 'Tab').style.display = 'block';
    if (tabName === 'progress') updateStatsDisplay();
}


// --- INPUT & CONTROLS ---

function initGyroscope() {
    if (window.DeviceOrientationEvent) {
        window.addEventListener('deviceorientation', (event) => {
            if (gyroEnabled && gameState === 'playing') {
                gyroTilt = event.gamma || 0;
                // Increased sensitivity from ±30° to ±20°
                gyroTilt = Math.max(-20, Math.min(20, gyroTilt)) / 20;
            }
        });
    }
}

function requestGyroPermission() {
    if (gameSettings.gyro && typeof DeviceOrientationEvent.requestPermission === 'function') {
        DeviceOrientationEvent.requestPermission()
            .then(response => {
                if (response === 'granted') {
                    gyroEnabled = true;
                    initGyroscope();
                } else {
                    // Gyro denied, update setting
                    gameSettings.gyro = false;
                    updateSettingsDisplay();
                    saveSettings();
                }
            }).catch(console.error);
    } else {
        gyroEnabled = gameSettings.gyro;
        initGyroscope();
    }
}

function vibrate(pattern = [100]) {
    if (gameSettings.vibration && navigator.vibrate) {
        navigator.vibrate(pattern);
    }
}


// --- EVENT LISTENERS ---

document.addEventListener('keydown', e => { keys[e.code] = true; e.preventDefault(); });
document.addEventListener('keyup', e => { keys[e.code] = false; });

const controls = {
    leftBtn: document.getElementById('leftBtn'),
    rightBtn: document.getElementById('rightBtn')
};

['touchstart', 'mousedown'].forEach(evt => {
    controls.leftBtn.addEventListener(evt, e => { touchControls.left = true; e.preventDefault(); });
    controls.rightBtn.addEventListener(evt, e => { touchControls.right = true; e.preventDefault(); });
});
['touchend', 'mouseup', 'mouseleave'].forEach(evt => {
    controls.leftBtn.addEventListener(evt, e => { touchControls.left = false; e.preventDefault(); });
    controls.rightBtn.addEventListener(evt, e => { touchControls.right = false; e.preventDefault(); });
});

document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => btn.addEventListener('click', () => startGame(btn.dataset.mode)));
document.getElementById('restartBtn').addEventListener('click', () => startGame(gameMode));
document.getElementById('menuBtn').addEventListener('click', () => {
    gameState = 'menu';
    document.getElementById('gameOverScreen').style.display = 'none';
    document.getElementById('menuScreen').style.display = 'flex';
    document.querySelector('.game-container').style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
});

document.getElementById('closeBonusBtn').addEventListener('click', closeBonusPopup);
document.querySelectorAll('.menu-tab').forEach(tab => tab.addEventListener('click', () => switchMenuTab(tab.dataset.tab)));

// Settings Toggles
document.getElementById('gyroToggle').addEventListener('click', () => {
    gameSettings.gyro = !gameSettings.gyro;
    requestGyroPermission(); // Request permission if toggled on
    updateSettingsDisplay();
    saveSettings();
});
document.getElementById('soundToggle').addEventListener('click', () => { gameSettings.sound = !gameSettings.sound; updateSettingsDisplay(); saveSettings(); });
document.getElementById('vibrationToggle').addEventListener('click', () => { gameSettings.vibration = !gameSettings.vibration; updateSettingsDisplay(); saveSettings(); });
document.getElementById('autoSeasonToggle').addEventListener('click', () => { gameSettings.autoSeason = !gameSettings.autoSeason; updateSettingsDisplay(); saveSettings(); });
document.getElementById('fpsToggle').addEventListener('click', () => { gameSettings.showFPS = !gameSettings.showFPS; updateSettingsDisplay(); saveSettings(); });

window.addEventListener('resize', resizeCanvas);
document.addEventListener('contextmenu', e => e.preventDefault());


// --- INITIAL GAME LAUNCH ---

resizeCanvas();
loadStats();
loadSettings();
requestGyroPermission(); // Attempt to activate gyro on load if enabled in settings
