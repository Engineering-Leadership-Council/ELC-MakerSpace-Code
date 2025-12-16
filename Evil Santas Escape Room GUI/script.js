document.addEventListener('DOMContentLoaded', () => {
    // Configuration
    const PIN_CODE = "4345";
    const SECTOR_CODES = ["TESLA", "FUSION", "2397", "1225"]; // Arbitrary codes
    const FINAL_CODE = "TINY TOOLBOX";
    const TIMER_DURATION_MINUTES = 40;

    // Quadrant Text Configuration
    const QUADRANT_CONFIG = [
        {
            title: "",
            placeholder: "OVERRIDE",
            icon: `<svg viewBox="0 0 24 24" class="quadrant-icon"><path fill="currentColor" d="M7 2v11h3v9l7-12h-4l4-8z"/></svg>`
        },
        {
            title: "",
            placeholder: "OVERRIDE",
            icon: `<svg viewBox="0 0 24 24" class="quadrant-icon"><path fill="currentColor" d="M19.8 18.4L14 8V4h1V2H9v2h1v4L4.2 18.4C3.4 19.6 4.2 21 5.6 21h12.8c1.4 0 2.2-1.4 1.4-2.6zM7 19l3.5-7h2.9l3.5 7H7z"/></svg>`
        },
        {
            title: "",
            placeholder: "OVERRIDE",
            icon: `<svg viewBox="0 0 24 24" class="quadrant-icon"><path fill="currentColor" d="M12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5zm7.43-2.53c.04-.32.07-.66.07-1s-.03-.68-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65A.506.506 0 0 0 14 2h-4c-.25 0-.46.18-.5.44l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.63c-.04.32-.07.66-.07 1s.03.68.07 1l-2.11 1.63c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.31.61.22l2.49-1c.52.39 1.06.73 1.69.98l.37 2.65c.04.26.25.44.5.44h4c.25 0 .46-.18.5-.44l.37-2.65c.63-.25 1.17-.59 1.69-.98l2.49 1c.22.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.63z"/></svg>`
        },
        {
            title: "",
            placeholder: "OVERRIDE",
            icon: `<svg viewBox="0 0 24 24" class="quadrant-icon"><path fill="currentColor" d="M5 21h14v-4h-5V7h5V3H5v4h5v10H5v4z"/></svg>`
        }
    ];

    // State
    let currentPin = "";
    let isUnlocked = false;
    let timerInterval;
    let endTime;
    let sectorsUnlocked = [false, false, false, false];

    // DOM Elements
    const pinScreen = document.getElementById('pin-screen');
    const mainScreen = document.getElementById('main-screen');
    const pinDots = document.querySelectorAll('.pin-dot');
    const keys = document.querySelectorAll('.key');
    const timerDisplay = document.getElementById('timer');
    const codeInputs = document.querySelectorAll('.code-input');
    const alarmSound = document.getElementById('alarm-sound');

    // Final Popup Elements
    const finalPopup = document.getElementById('final-popup');
    const finalStatus = document.getElementById('final-status');
    const finalMessage = document.getElementById('final-message');

    // Audio Elements
    const ambientMusic = document.getElementById('ambient-music');
    const clickSound = document.getElementById('click-sound');
    const successSound = document.getElementById('success-sound');
    const failSound = document.getElementById('fail-sound');
    const unlockSound = document.getElementById('unlock-sound');

    // Start ambient music on first interaction
    document.body.addEventListener('click', () => {
        if (ambientMusic.paused) {
            ambientMusic.volume = 0.3;
            ambientMusic.play().catch(e => console.log("Ambient play failed:", e));
        }
    }, { once: true });

    // Initialize Quadrant Text
    function initializeQuadrants() {
        QUADRANT_CONFIG.forEach((config, index) => {
            const quadrant = document.getElementById(`q${index + 1}`);
            if (quadrant) {
                const titleElement = quadrant.querySelector('h2');
                const inputElement = quadrant.querySelector('.code-input');

                if (titleElement) {
                    titleElement.textContent = config.title;
                    // Insert icon before title
                    if (config.icon) {
                        const iconContainer = document.createElement('div');
                        iconContainer.innerHTML = config.icon;
                        quadrant.insertBefore(iconContainer.firstChild, titleElement);
                    }
                }
                if (inputElement) inputElement.placeholder = config.placeholder;
            }
        });
    }
    initializeQuadrants();

    function playSound(sound) {
        sound.currentTime = 0;
        sound.play().catch(e => console.log("Sound play failed:", e));
    }

    // PIN Logic
    keys.forEach(key => {
        key.addEventListener('click', () => {
            playSound(clickSound);
            const value = key.dataset.key;
            handlePinInput(value);
        });
    });

    function handlePinInput(value) {
        if (value === 'clear') {
            currentPin = "";
        } else if (value === 'enter') {
            checkPin();
        } else {
            if (currentPin.length < 4) {
                currentPin += value;
            }
        }
        updatePinDisplay();
    }

    function updatePinDisplay() {
        pinDots.forEach((dot, index) => {
            if (index < currentPin.length) {
                dot.classList.add('filled');
            } else {
                dot.classList.remove('filled');
            }
        });
    }

    function checkPin() {
        if (currentPin === PIN_CODE) {
            playSound(successSound);
            unlockApp();
        } else {
            playSound(failSound);
            currentPin = "";
            updatePinDisplay();
            // Simple visual feedback could be added here
        }
    }

    function unlockApp() {
        isUnlocked = true;
        pinScreen.classList.remove('active');
        setTimeout(() => {
            pinScreen.style.display = 'none';
            mainScreen.style.display = 'flex';
            setTimeout(() => {
                mainScreen.classList.add('active');
                setTimeout(startTimer, 500); // Wait for fade in
            }, 50);
        }, 500);
    }

    // Timer Logic
    function startTimer() {
        const now = Date.now();
        endTime = now + (TIMER_DURATION_MINUTES * 60 * 1000);

        updateTimer(); // Initial call
        timerInterval = setInterval(updateTimer, 31); // ~30fps for ms
    }

    function updateTimer() {
        const now = Date.now();
        const remaining = endTime - now;

        if (remaining <= 0) {
            clearInterval(timerInterval);
            timerDisplay.textContent = "00:00:00";
            timerDisplay.classList.add('timer-critical');
            playAlarm();
            return;
        }

        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        const ms = Math.floor((remaining % 1000) / 10); // Show 2 digits for ms

        timerDisplay.textContent = `${pad(minutes)}:${pad(seconds)}:${pad(ms)}`;
    }

    function pad(num) {
        return num.toString().padStart(2, '0');
    }

    function playAlarm() {
        alarmSound.loop = true;
        alarmSound.play().catch(e => console.log("Audio play failed:", e));
    }

    // Quadrant Logic
    codeInputs.forEach(input => {
        input.addEventListener('input', (e) => {
            const index = parseInt(e.target.dataset.index);
            const value = e.target.value.toUpperCase();

            if (!sectorsUnlocked[index] && value === SECTOR_CODES[index]) {
                unlockSector(index);
            }
        });
    });

    function unlockSector(index) {
        playSound(unlockSound);
        sectorsUnlocked[index] = true;
        const quadrant = document.getElementById(`q${index + 1}`);
        quadrant.classList.add('unlocked');
        quadrant.querySelector('.status-indicator').textContent = "SYSTEM BYPASSED";
        quadrant.querySelector('.code-input').disabled = true;

        // Check if all sectors are unlocked
        if (sectorsUnlocked.every(s => s)) {
            setTimeout(triggerVictory, 1000);
        }
    }

    // Final Popup Logic
    function triggerVictory() {
        clearInterval(timerInterval);

        // Hide main screen
        mainScreen.classList.remove('active');
        setTimeout(() => {
            mainScreen.style.display = 'none';

            // Show final screen
            finalPopup.style.display = 'flex';
            setTimeout(() => {
                finalPopup.classList.add('active');
            }, 50);
        }, 500);

        // Stop alarm if playing
        alarmSound.pause();
        alarmSound.currentTime = 0;
    }
});
