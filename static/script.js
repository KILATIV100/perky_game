// IIFE для інкапсуляції коду гри
(function() {
    'use strict';

    // Ініціалізація Telegram WebApp
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    // Отримання елементів DOM
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');

    // UI елементи
    const ui = {
        screens: {
            menu: document.getElementById('menuScreen'),
            gameOver: document.getElementById('gameOverScreen'),
            shop: document.getElementById('shopScreen'),
            customize: document.getElementById('customizeScreen'),
        },
        buttons: {
            // Керування
            left: document.getElementById('leftBtn'),
            right: document.getElementById('rightBtn'),
            // Перезапуск та меню
            restart: document.getElementById('restartBtn'),
            toMenu: document.getElementById('menuBtn'),
            // Навігація в меню
            shop: document.getElementById('shopBtn'),
            shopBack: document.getElementById('shopBackBtn'),
            customize: document.getElementById('customizeBtn'),
            customizeBack: document.getElementById('customizeBackBtn'),
        },
        displays: {
            // Ігрові
            heightScore: document.getElementById('heightScore'),
            coffeeCount: document.getElementById('coffeeCount'),
            timeDisplay: document.getElementById('timeDisplay'),
            timeLeft: document.getElementById('timeLeft'),
            // Рекорди
            bestHeight: document.getElementById('bestHeight'),
            bestCoffee: document.getElementById('bestCoffee'),
            // Екран завершення гри
            finalHeight: document.getElementById('finalHeight'),
            finalCoffee: document.getElementById('finalCoffee'),
            finalTime: document.getElementById('finalTime'),
            timeSpent: document.getElementById('timeSpent'),
            // Магазин
            shopCoins: document.getElementById('shopCoins'),
            shopGrid: document.getElementById('shopGrid'),
             // Кастомізація
            customizeCoins: document.getElementById('customizeCoins'),
            skinsGrid: document.getElementById('skinsGrid'),
        },
        containers: {
            stats: document.getElementById('statsGrid'),
            leaderboard: document.getElementById('leaderboardContent'),
        },
        popups: {
            bonus: document.getElementById('bonusPopup'),
            bonusTitle: document.getElementById('bonusTitle'),
            bonusContent: document.getElementById('bonusContent'),
            bonusInstruction: document.getElementById('bonusInstruction'),
            bonusTimer: document.getElementById('bonusTimer'),
            closeBonus: document.getElementById('closeBonusBtn'),
        },
        toggles: {
            gyro: document.getElementById('gyroToggle'),
            vibration: document.getElementById('vibrationToggle'),
        },
        tabs: document.querySelectorAll('.menu-tab'),
        tabSections: document.querySelectorAll('.menu-section'),
    };

    // Стан гри
    let gameState = 'menu'; // menu, playing, gameOver
    let gameMode = 'classic';
    let animationId;
    let lastTime = 0;
    let difficultyTimer = 0;

    // Ігрові об'єкти
    let player, platforms, coffees, particles, clouds;
    let cameraY = 0;
    
    // Ігрова статистика
    let height = 0;
    let coffeeCount = 0;
    let timeLeft = 60;
    let gameTimer;
    let bonusTimer;

    // Глобальна статистика гравця
    let userStats = {
        id: tg.initDataUnsafe?.user?.id || null,
        username: tg.initDataUnsafe?.user?.username || 'Player',
        highScore: 0,
        totalBeans: 0,
        gamesPlayed: 0,
        purchasedSkins: ['default'],
    };

    // Налаштування гри
    const config = {
        player: {
            width: 35,
            height: 35,
            jumpPower: -16,
            speed: 6,
            gravity: 0.7,
        },
        platform: {
            width: 85,
            height: 15,
            minGapY: 80,
            maxGapY: 130,
            maxGapX: 200,
        },
        difficulty: {
            increaseInterval: 5000, // ms
            speedIncrement: 0.1,
            maxSpeed: 10,
        },
        gyro: {
            enabled: false,
            sensitivity: 20, // Збільшена чутливість (менший кут для макс. швидкості)
            tilt: 0,
        },
        vibration: {
            enabled: true,
        },
    };
    
    // Товари в магазині (тимчасово, поки немає API)
    const shopItems = {
        'double_jump': { name: 'Подвійний стрибок', price: 500, description: 'Дозволяє стрибнути раз у повітрі.' },
        'magnet': { name: 'Магніт для зерен', price: 750, description: 'Автоматично притягує зерна.' },
    };

    // Скіни для кастомізації
    const skins = {
        'default': { name: 'Класичний', emoji: '🤖', price: 0 },
        'ninja': { name: 'Ніндзя', emoji: '🥷', price: 250 },
        'wizard': { name: 'Чарівник', emoji: '🧙‍♂️', price: 300 },
        'alien': { name: 'Прибулець', emoji: '👽', price: 350 },
        'superhero': { name: 'Супергерой', emoji: '🦸‍♂️', price: 500 },
    };
    
    // Сезонні теми
    const themes = {
        spring: { bg: 'linear-gradient(180deg, #87CEEB 0%, #98FB98 100%)', platform: '#8B4513' },
        summer: { bg: 'linear-gradient(180deg, #42C2FF 0%, #FFD700 100%)', platform: '#D2691E' },
        autumn: { bg: 'linear-gradient(180deg, #F39C12 0%, #E74C3C 100%)', platform: '#A0522D' },
        winter: { bg: 'linear-gradient(180deg, #FFFFFF 0%, #B0E0E6 100%)', platform: '#A9A9A9' },
        halloween: { bg: 'linear-gradient(180deg, #1A1A1A 0%, #4A00E0 100%)', platform: '#FF7F50' },
        valentines: { bg: 'linear-gradient(180deg, #FFC0CB 0%, #FF69B4 100%)', platform: '#DB7093' },
    };
    let currentTheme = themes.spring;


    /**
     * ========================================
     * ОСНОВНІ ФУНКЦІЇ ГРИ
     * ========================================
     */

    // Головний ігровий цикл
    function gameLoop(time) {
        if (gameState !== 'playing') return;

        const deltaTime = time - lastTime;
        lastTime = time;

        update(deltaTime);
        render();

        animationId = requestAnimationFrame(gameLoop);
    }

    // Ініціалізація та запуск гри
    function startGame(mode) {
        gameMode = mode;
        gameState = 'playing';

        // Скидання стану гри
        height = 0;
        coffeeCount = 0;
        cameraY = 0;
        difficultyTimer = 0;
        config.player.speed = 6;

        player = {
            x: canvas.width / 2 - config.player.width / 2,
            y: canvas.height - 100,
            width: config.player.width,
            height: config.player.height,
            vx: 0,
            vy: 0,
            onPlatform: null,
            skin: skins[userStats.currentSkin || 'default'].emoji,
        };

        platforms = [];
        coffees = [];
        particles = [];
        
        // Створення початкових платформ
        let startPlatform = createPlatform(canvas.width / 2 - config.platform.width / 2, canvas.height - 50, 'normal');
        platforms.push(startPlatform);
        player.onPlatform = startPlatform;

        for (let i = 0; i < 15; i++) {
            generateNextPlatform();
        }

        ui.screens.menu.style.display = 'none';
        ui.screens.gameOver.style.display = 'none';

        if (gameMode === 'timed') {
            timeLeft = 60;
            ui.displays.timeDisplay.style.display = 'block';
            startTimer();
        } else {
            ui.displays.timeDisplay.style.display = 'none';
        }

        lastTime = performance.now();
        animationId = requestAnimationFrame(gameLoop);
    }

    // Завершення гри
    function endGame() {
        if (gameState === 'gameOver') return;
        gameState = 'gameOver';

        cancelAnimationFrame(animationId);
        if (gameTimer) clearInterval(gameTimer);

        userStats.gamesPlayed++;
        userStats.totalBeans += coffeeCount;
        userStats.highScore = Math.max(userStats.highScore, height);
        
        saveStatsOnServer();

        ui.displays.finalHeight.textContent = height;
        ui.displays.finalCoffee.textContent = coffeeCount;

        if (gameMode === 'timed') {
            ui.displays.finalTime.style.display = 'block';
            ui.displays.timeSpent.textContent = 60 - timeLeft;
        } else {
            ui.displays.finalTime.style.display = 'none';
        }
        
        ui.screens.gameOver.style.display = 'flex';
        checkBonuses(); // Перевірка бонусів ТІЛЬКИ після програшу
    }


    /**
     * ========================================
     * ЛОГІКА ОНОВЛЕННЯ СТАНУ (UPDATE)
     * ========================================
     */

    function update(deltaTime) {
        // Оновлення складності
        difficultyTimer += deltaTime;
        if (difficultyTimer > config.difficulty.increaseInterval) {
            if(config.player.speed < config.difficulty.maxSpeed) {
                config.player.speed += config.difficulty.speedIncrement;
            }
            difficultyTimer = 0;
        }

        // Керування
        let targetVx = 0;
        if (config.gyro.enabled && Math.abs(config.gyro.tilt) > 0.05) {
            targetVx = config.gyro.tilt * (config.player.speed + 2);
        } else if (ui.buttons.left.pressed) {
            targetVx = -config.player.speed;
        } else if (ui.buttons.right.pressed) {
            targetVx = config.player.speed;
        }
        player.vx += (targetVx - player.vx) * 0.2; // Плавний рух
        player.x += player.vx;

        // Гравітація
        player.vy += config.player.gravity;
        player.y += player.vy;

        // Перевірка виходу за межі екрану
        if (player.x < -player.width) player.x = canvas.width;
        if (player.x > canvas.width) player.x = -player.width;

        // Перевірка падіння
        if (player.y > cameraY + canvas.height) {
            endGame();
            return;
        }

        // Камера
        let targetCameraY = player.y - canvas.height * 0.4;
        cameraY += (targetCameraY - cameraY) * 0.1;

        // Оновлення висоти
        let currentHeight = Math.max(0, Math.floor(-(player.y - (canvas.height - 50)) / 10));
        if (currentHeight > height) {
            height = currentHeight;
            if (height > userStats.highScore) {
                ui.displays.bestHeight.classList.add('new-record-animation');
            }
        }

        // Перевірка зіткнень з платформами
        player.onPlatform = null;
        for (const platform of platforms) {
            if (
                player.vy > 0 &&
                player.x < platform.x + platform.width &&
                player.x + player.width > platform.x &&
                player.y + player.height > platform.y &&
                player.y + player.height < platform.y + platform.height + 20 // Збільшена зона для стабільності
            ) {
                player.onPlatform = platform;
                player.y = platform.y - player.height;
                player.vy = config.player.jumpPower;

                vibrateDevice([50]);
                
                // Ефекти платформ
                if (platform.type === 'bouncy') {
                    player.vy *= 1.6;
                    platform.isBouncing = true;
                }
                if (platform.type === 'fragile' && !platform.isBroken) {
                    platform.isBroken = true;
                }
                
                // Виходимо з циклу після першого зіткнення
                break; 
            }
        }

        // Збір кавових зерен
        for (let i = coffees.length - 1; i >= 0; i--) {
            const coffee = coffees[i];
            if (
                player.x < coffee.x + 15 &&
                player.x + player.width > coffee.x - 15 &&
                player.y < coffee.y + 15 &&
                player.y + player.height > coffee.y - 15
            ) {
                coffees.splice(i, 1);
                coffeeCount++;
                vibrateDevice([30]);
                if (coffeeCount > userStats.bestCoffee) {
                    ui.displays.bestCoffee.classList.add('new-record-animation');
                }
            }
        }
        
        // Генерація та видалення платформ
        if (platforms[0].y > cameraY + canvas.height) {
            platforms.shift();
            generateNextPlatform();
        }

        // Оновлення UI
        ui.displays.heightScore.textContent = height;
        ui.displays.coffeeCount.textContent = coffeeCount;
        ui.displays.bestHeight.textContent = userStats.highScore;
        ui.displays.bestCoffee.textContent = userStats.bestCoffee || 0;
    }

    /**
     * ========================================
     * ЛОГІКА ВІДОБРАЖЕННЯ (RENDER)
     * ========================================
     */
    function render() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Малюємо фон
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        const [color1, color2] = currentTheme.bg.match(/#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})/g);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Хмари
        renderClouds();

        ctx.save();
        ctx.translate(0, -cameraY);

        // Малюємо платформи
        for (const platform of platforms) {
            if (platform.isBroken && platform.opacity > 0) {
                platform.opacity -= 0.05;
            }
            ctx.globalAlpha = platform.opacity;

            ctx.fillStyle = platform.color;
            let bounceOffset = 0;
            if (platform.isBouncing) {
                platform.bounceFrame = (platform.bounceFrame || 0) + 1;
                bounceOffset = Math.sin(platform.bounceFrame * 0.5) * 5;
                if(platform.bounceFrame > 20) platform.isBouncing = false;
            }

            ctx.fillRect(platform.x, platform.y + bounceOffset, platform.width, platform.height);
        }
        ctx.globalAlpha = 1;

        // Малюємо кавові зерна
        for (const coffee of coffees) {
            ctx.fillStyle = '#6F4E37';
            ctx.beginPath();
            ctx.ellipse(coffee.x, coffee.y, 8, 10, Math.PI / 4, 0, 2 * Math.PI);
            ctx.fill();
        }

        // Малюємо гравця
        ctx.font = '30px sans-serif';
        ctx.fillText(player.skin, player.x, player.y + player.height - 5);
        
        ctx.restore();
    }
    
    function renderClouds() {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        clouds.forEach(cloud => {
            ctx.beginPath();
            ctx.arc(cloud.x, cloud.y - cameraY * 0.5, cloud.r, 0, 2 * Math.PI);
            ctx.closePath();
            ctx.fill();

            // Рух хмар
            cloud.x += cloud.speed;
            if (cloud.x > canvas.width + cloud.r) {
                cloud.x = -cloud.r;
            }
        });
    }

    /**
     * ========================================
     * ДОПОМІЖНІ ФУНКЦІЇ
     * ========================================
     */

    function createPlatform(x, y, type) {
        let color = currentTheme.platform;
        if (type === 'bouncy') color = '#32CD32';
        if (type === 'fragile') color = '#FF4500';

        return {
            x, y, type, color,
            width: config.platform.width,
            height: config.platform.height,
            isBroken: false,
            opacity: 1,
        };
    }

    function generateNextPlatform() {
        const lastPlatform = platforms[platforms.length - 1];
        
        let newY = lastPlatform.y - (config.platform.minGapY + Math.random() * (config.platform.maxGapY - config.platform.minGapY));
        let newX = lastPlatform.x + (Math.random() - 0.5) * config.platform.maxGapX;
        
        // Перевірка, щоб платформа не виходила за межі екрану
        newX = Math.max(0, Math.min(newX, canvas.width - config.platform.width));

        let type = 'normal';
        const rand = Math.random();
        if (rand < 0.15) type = 'bouncy'; // 15%
        else if (rand < 0.25) type = 'fragile'; // 10%
        
        platforms.push(createPlatform(newX, newY, type));

        // Додавання кавових зерен
        if (Math.random() < 0.4) {
            coffees.push({ x: newX + config.platform.width / 2, y: newY - 20 });
        }
    }

    function startTimer() {
        gameTimer = setInterval(() => {
            timeLeft--;
            ui.displays.timeLeft.textContent = timeLeft;
            if (timeLeft <= 0) {
                clearInterval(gameTimer);
                endGame();
            }
        }, 1000);
    }
    
    function vibrateDevice(pattern) {
        if (config.vibration.enabled && navigator.vibrate) {
            navigator.vibrate(pattern);
        }
    }
    
    // Визначення сезону
    function setSeasonalTheme() {
        const date = new Date();
        const month = date.getMonth();
        const day = date.getDate();

        if (month === 9 && day >= 24 && day <= 31) {
            currentTheme = themes.halloween;
        } else if (month === 1 && day >= 7 && day <= 14) {
            currentTheme = themes.valentines;
        } else if (month >= 2 && month <= 4) {
            currentTheme = themes.spring;
        } else if (month >= 5 && month <= 7) {
            currentTheme = themes.summer;
        } else if (month >= 8 && month <= 10) {
            currentTheme = themes.autumn;
        } else {
            currentTheme = themes.winter;
        }
    }
    
    // Ініціалізація хмар
    function initClouds() {
        clouds = [];
        for (let i = 0; i < 5; i++) {
            clouds.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                r: Math.random() * 20 + 20,
                speed: Math.random() * 0.2 + 0.1,
            });
        }
    }
    
     /**
     * ========================================
     * ЛОГІКА БОНУСІВ
     * ========================================
     */
    function checkBonuses() {
        let bonus = null;
        if (coffeeCount >= 5000) {
            bonus = { title: '🎁 Брендована чашка!', instruction: 'Покажіть це бариста, щоб отримати вашу брендовану чашку Perky Coffee!' };
        } else if (coffeeCount >= 200) {
            bonus = { title: '🎁 Знижка 5%!', instruction: 'Покажіть це бариста, щоб отримати знижку 5% на будь-який напій.' };
        } else if (coffeeCount >= 100) {
            bonus = { title: '🎁 Знижка 2%!', instruction: 'Покажіть це бариста, щоб отримати знижку 2% на будь-який напій.' };
        }

        if (bonus) {
            showBonusPopup(bonus.title, bonus.instruction);
        }
    }

    function showBonusPopup(title, instruction) {
        ui.popups.bonusTitle.textContent = title;
        ui.popups.bonusContent.textContent = `Ви зібрали ${coffeeCount} зерен!`;
        ui.popups.bonusInstruction.textContent = instruction;
        ui.popups.bonus.classList.add('show');

        let timeLeft = 600; // 10 хвилин
        
        const updateTimer = () => {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            ui.popups.bonusTimer.textContent = `⏰ Час дії: ${minutes}:${seconds.toString().padStart(2, '0')}`;
            if (timeLeft <= 0) {
                hideBonusPopup();
            }
            timeLeft--;
        };

        updateTimer();
        bonusTimer = setInterval(updateTimer, 1000);
    }
    
    function hideBonusPopup() {
        ui.popups.bonus.classList.remove('show');
        if (bonusTimer) clearInterval(bonusTimer);
    }

    /**
     * ========================================
     * РОБОТА З СЕРВЕРОМ
     * ========================================
     */
    async function saveStatsOnServer() {
        if (!userStats.id) return;
        try {
            await fetch('/save_stats', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userStats.id,
                    username: userStats.username,
                    score: height,
                    collected_beans: coffeeCount,
                }),
            });
        } catch (error) {
            console.error('Failed to save stats:', error);
        }
    }

    async function fetchUserStats() {
        if (!userStats.id) return;
        try {
            const response = await fetch(`/stats/${userStats.id}`);
            const data = await response.json();
            if (data && !data.error) {
                userStats.highScore = data.high_score || 0;
                userStats.totalBeans = data.total_beans || 0;
                userStats.gamesPlayed = data.games_played || 0;
                userStats.bestCoffee = data.best_coffee || 0;
                userStats.purchasedSkins = data.purchased_skins ? JSON.parse(data.purchased_skins) : ['default'];
                userStats.currentSkin = data.current_skin || 'default';
            }
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
        updateStatsUI();
        updateShopUI();
        updateCustomizeUI();
    }
    
    async function fetchLeaderboard() {
        try {
            const response = await fetch('/leaderboard');
            const data = await response.json();
            if (data.leaderboard) {
                updateLeaderboardUI(data.leaderboard);
            }
        } catch (error) {
            console.error('Failed to fetch leaderboard:', error);
        }
    }

     /**
     * ========================================
     * ОНОВЛЕННЯ UI
     * ========================================
     */
    function updateStatsUI() {
        ui.containers.stats.innerHTML = `
            <div>🏆 Рекорд висоти: ${userStats.highScore} м</div>
            <div>☕ Рекорд зерен: ${userStats.bestCoffee || 0}</div>
            <div>🎮 Всього ігор: ${userStats.gamesPlayed}</div>
            <div>💰 Всього зерен: ${userStats.totalBeans}</div>
        `;
    }

    function updateLeaderboardUI(leaderboard) {
        if (leaderboard.length === 0) {
            ui.containers.leaderboard.innerHTML = `<p style="color: white; text-align: center;">Таблиця лідерів порожня. Будьте першим!</p>`;
            return;
        }
        const emoji = ['🥇', '🥈', '🥉'];
        ui.containers.leaderboard.innerHTML = leaderboard.map((player, index) => `
            <div class="leaderboard-item">
                <span class="leaderboard-rank rank-${index + 1}">${emoji[index] || (index + 1) + '.'}</span>
                <span class="leaderboard-name">${player.username || 'Гравець'}</span>
                <span class="leaderboard-score">${player.high_score} м</span>
            </div>
        `).join('');
    }
    
    function updateShopUI() {
        ui.displays.shopCoins.textContent = userStats.totalBeans;
        // Тут буде логіка відображення товарів, коли вони будуть реалізовані
        ui.containers.shopGrid.innerHTML = `<p style="color: #555; text-align: center;">Магазин у розробці. Збирайте зерна!</p>`;
    }
    
    function updateCustomizeUI() {
        ui.displays.customizeCoins.textContent = userStats.totalBeans;
        ui.containers.skinsGrid.innerHTML = '';
        for (const [id, skin] of Object.entries(skins)) {
            const isPurchased = userStats.purchasedSkins.includes(id);
            const isActive = (userStats.currentSkin || 'default') === id;
            const canAfford = userStats.totalBeans >= skin.price;

            const item = document.createElement('div');
            item.className = 'customize-item';
            if (isActive) item.classList.add('active');
            if (!isPurchased && !canAfford) item.classList.add('locked');
            
            item.innerHTML = `
                <div class="customize-preview">${skin.emoji}</div>
                <div class="customize-name">${skin.name}</div>
                <div class="customize-cost">${isPurchased ? 'Придбано' : skin.price + ' ☕'}</div>
            `;
            
            item.onclick = () => handleSkinSelection(id, skin.price, isPurchased);
            ui.containers.skinsGrid.appendChild(item);
        }
    }
    
    async function handleSkinSelection(id, price, isPurchased) {
        if (isPurchased) {
            userStats.currentSkin = id;
        } else if (userStats.totalBeans >= price) {
            userStats.totalBeans -= price;
            userStats.purchasedSkins.push(id);
            userStats.currentSkin = id;
        } else {
            // Можна додати повідомлення "недостатньо зерен"
            return;
        }
        
        await saveSkinSettings();
        updateCustomizeUI();
    }
    
    async function saveSkinSettings() {
        if (!userStats.id) return;
        try {
            await fetch('/save_skins', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userStats.id,
                    purchased_skins: JSON.stringify(userStats.purchasedSkins),
                    current_skin: userStats.currentSkin
                }),
            });
        } catch (error) {
            console.error('Failed to save skin settings:', error);
        }
    }

    /**
     * ========================================
     * ОБРОБНИКИ ПОДІЙ
     * ========================================
     */
    function setupEventListeners() {
        // Керування з клавіатури
        const keyMap = { 'ArrowLeft': 'left', 'KeyA': 'left', 'ArrowRight': 'right', 'KeyD': 'right' };
        document.addEventListener('keydown', (e) => {
            if (gameState !== 'playing') return;
            const direction = keyMap[e.code];
            if (direction) ui.buttons[direction].pressed = true;
        });
        document.addEventListener('keyup', (e) => {
            if (gameState !== 'playing') return;
            const direction = keyMap[e.code];
            if (direction) ui.buttons[direction].pressed = false;
        });

        // Керування дотиком
        function handleTouch(e, isPressed) {
            for (const touch of e.changedTouches) {
                if (touch.clientX < window.innerWidth / 2) {
                    ui.buttons.left.pressed = isPressed;
                } else {
                    ui.buttons.right.pressed = isPressed;
                }
            }
        }
        canvas.addEventListener('touchstart', (e) => { e.preventDefault(); handleTouch(e, true); }, { passive: false });
        canvas.addEventListener('touchend', (e) => { e.preventDefault(); handleTouch(e, false); }, { passive: false });
        
        // Керування мишкою (для десктопу)
        ui.buttons.left.addEventListener('mousedown', () => ui.buttons.left.pressed = true);
        ui.buttons.left.addEventListener('mouseup', () => ui.buttons.left.pressed = false);
        ui.buttons.left.addEventListener('mouseleave', () => ui.buttons.left.pressed = false);
        ui.buttons.right.addEventListener('mousedown', () => ui.buttons.right.pressed = true);
        ui.buttons.right.addEventListener('mouseup', () => ui.buttons.right.pressed = false);
        ui.buttons.right.addEventListener('mouseleave', () => ui.buttons.right.pressed = false);

        // Кнопки інтерфейсу
        ui.buttons.restart.addEventListener('click', () => startGame(gameMode));
        ui.buttons.toMenu.addEventListener('click', showMenu);
        ui.popups.closeBonus.addEventListener('click', hideBonusPopup);

        // Навігація в меню
        ui.buttons.shop.addEventListener('click', () => showScreen('shop'));
        ui.buttons.shopBack.addEventListener('click', showMenu);
        ui.buttons.customize.addEventListener('click', () => showScreen('customize'));
        ui.buttons.customizeBack.addEventListener('click', showMenu);

        // Перемикання вкладок меню
        ui.tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;
                ui.tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                ui.tabSections.forEach(section => {
                    section.style.display = 'none';
                    if (section.id === `${targetTab}Tab`) {
                        section.style.display = 'block';
                    }
                });

                if (targetTab === 'social') fetchLeaderboard();
                if (targetTab === 'progress') fetchUserStats();
            });
        });
        
        // Перемикачі налаштувань
        ui.toggles.vibration.addEventListener('click', () => {
            config.vibration.enabled = !config.vibration.enabled;
            ui.toggles.vibration.classList.toggle('active', config.vibration.enabled);
        });

        ui.toggles.gyro.addEventListener('click', () => {
            if (!config.gyro.enabled) {
                requestGyroPermission();
            } else {
                config.gyro.enabled = false;
                ui.toggles.gyro.classList.toggle('active', false);
            }
        });
        
        // Запуск гри з меню
        document.querySelectorAll('.mode-btn[data-mode]').forEach(btn => {
            btn.addEventListener('click', () => startGame(btn.dataset.mode));
        });
        
        // Зміна розміру вікна
        window.addEventListener('resize', resizeCanvas);
    }
    
    function showScreen(screenName) {
        for (const screen in ui.screens) {
            ui.screens[screen].style.display = 'none';
        }
        ui.screens[screenName].style.display = 'flex';
    }

    function showMenu() {
        gameState = 'menu';
        showScreen('menu');
        document.querySelector('.menu-tab[data-tab="play"]').click();
        fetchUserStats();
    }
    
     /**
     * ========================================
     * ГІРОСКОП
     * ========================================
     */
    function requestGyroPermission() {
        if (typeof DeviceOrientationEvent.requestPermission === 'function') {
            DeviceOrientationEvent.requestPermission()
                .then(response => {
                    if (response === 'granted') {
                        window.addEventListener('deviceorientation', handleGyro);
                        config.gyro.enabled = true;
                        ui.toggles.gyro.classList.add('active');
                    }
                })
                .catch(() => { config.gyro.enabled = false; });
        } else {
            // Для Android та інших пристроїв без запиту дозволу
             window.addEventListener('deviceorientation', handleGyro);
             config.gyro.enabled = true;
             ui.toggles.gyro.classList.add('active');
        }
    }

    function handleGyro(event) {
        // gamma: нахил вліво-вправо
        let tilt = event.gamma || 0;
        config.gyro.tilt = Math.max(-1, Math.min(1, tilt / config.gyro.sensitivity));
    }


    /**
     * ========================================
     * ІНІЦІАЛІЗАЦІЯ
     * ========================================
     */
    function init() {
        resizeCanvas();
        setSeasonalTheme();
        initClouds();
        setupEventListeners();
        showMenu(); // Починаємо з меню
    }
    
    // Запускаємо все
    init();

})();

