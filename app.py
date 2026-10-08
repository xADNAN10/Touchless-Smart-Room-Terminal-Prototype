import serial
import threading
import time
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
PORT = 'COM5'
BAUD = 115200

# System State shared with frontend
system_state = {
    "motion": "0",
    "gesture": "SYSTEM READY",
    "instant_zone": "NONE", # For zero-delay game controls
    "sleep_mode": False
}

last_motion_time = time.time()
DWELL_TIME = 0.2 # Seconds required to trigger a menu gesture (adjust to 0.5s tomorrow)

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    ser.setDTR(False)
    ser.setRTS(False)
except Exception as e:
    print(f"Failed to connect to ESP32: {e}")
    ser = None

def read_serial_data():
    global system_state, last_motion_time
    
    active_zone = None
    zone_entry_time = 0
    action_triggered = False

    while True:
        if not ser: break
        try:
            line = ser.readline().decode('utf-8').strip()
            if not line: continue
            data = line.split(',')
            
            if len(data) == 65:
                # PIR Motion & Sleep Logic
                motion_val = data[64]
                system_state["motion"] = motion_val
                
                if motion_val == "1":
                    last_motion_time = time.time()
                    system_state["sleep_mode"] = False
                elif time.time() - last_motion_time > 5: # 5 Minutes
                    system_state["sleep_mode"] = True

                # LiDAR Pixel Counting
                click_hits, left_hits, right_hits, back_hits = 0, 0, 0, 0
                
                for i in range(64):
                    try:
                        dist = int(data[i])
                        if dist <= 0 or dist > 600: continue
                            
                        x = i % 8
                        y = i // 8
                        
                        if dist <= 50:
                            if x in (2, 3) and y in (2, 3): click_hits += 1
                        elif 150 <= dist <= 350:
                            if x in (2, 3) and y in (0, 1): left_hits += 1
                            elif x in (2, 3) and y in (5, 6): right_hits += 1
                        elif 350 < dist <= 600:
                            back_hits += 1
                    except ValueError: pass
                
                # Determine Instant Zone (Used for the Game)
                current_zone = "NONE"
                if click_hits >= 2: current_zone = "CLICK"
                elif left_hits >= 2 and right_hits >= 2: current_zone = "DUAL"
                elif left_hits >= 2: current_zone = "LEFT"
                elif right_hits >= 2: current_zone = "RIGHT"
                elif back_hits >= 5: current_zone = "BACK"
                
                system_state["instant_zone"] = current_zone

                # Menu Timer Logic (Debounced)
                if current_zone == active_zone and current_zone != "NONE":
                    if not action_triggered and (time.time() - zone_entry_time >= DWELL_TIME):
                        system_state["gesture"] = current_zone
                        action_triggered = True
                elif current_zone != active_zone:
                    active_zone = current_zone
                    zone_entry_time = time.time()
                    action_triggered = False
                    # Clear menu gesture if hand moves away
                    if current_zone == "NONE":
                        system_state["gesture"] = "NONE"
                                
        except Exception as e:
            print(f"Data processing error: {e}") 

threading.Thread(target=read_serial_data, daemon=True).start()

# --- FRONTEND HTML/JS/CSS ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Room Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
    <style>
        /* BASE DESIGN - Tweak colors and borders here for the Motionrec aesthetic */
        :root {
            --bg: #000000;
            --fg: #ffffff; /* Cyan text */
            --dim: #004433; /* Dark green for menu highlight */
            --bg-image: url("/static/DarkBG.png");
        }
        .light-mode { 
            --bg: #e0f8f5; 
            --fg: #000000; 
            --dim: #88ccbb; 
            --bg-image: url("/static/LightBG.png");
        }
        body { 
            background-color: var(--bg);
            background-image: var(--bg-image);
            background-size: cover; 
            background-position: center;
            image-rendering: pixelated;
            image-rendering: crisp-edges; 
            color: var(--fg); /* This forces the text to not be black */
            font-family: 'Press Start 2P', monospace; 
            margin: 0; padding: 20px; overflow: hidden;
            display: flex; justify-content: center; align-items: center; height: 90vh;
            transition: background 0.5s, color 0.5s;
        }
        

        /* SCREEN VIEWS */
        .screen { display: none; height: 100%; flex-direction: column; justify-content: space-between; }
        .active-screen { display: flex; }

        /* HUD ELEMENTS */
        .header { display: flex; justify-content: space-between; font-size: 14px; padding-bottom: 10px;}
        .center-clock { text-align: center; font-size: 48px; margin: auto; }
        
        /* CHARACTER ANIMATION */
        #character { text-align: center; font-size: 32px; height: 40px; }
        
        /* SLEEP OVERLAY */
        #sleep-overlay {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,1); display: none; 
            justify-content: center; align-items: center; font-size: 40px; color: #555;
            z-index: 100;
        }

        /* SETTINGS MENU */
        .menu-row { display: flex; justify-content: space-around; align-items: center; height: 100%; }
        .menu-item { padding: 20px; border: 2px solid transparent; text-align: center; }
        .menu-item.selected { border-color: var(--fg); background: var(--dim); }

        /* GAME GRID */
        #game-board { 
            display: grid; grid-template-columns: repeat(8, 1fr); grid-template-rows: repeat(10, 1fr);
            width: 100%; height: 100%; border: 2px solid var(--dim);
        }
        .cell { border: 1px dotted rgba(0, 255, 204, 0.1); display: flex; justify-content: center; align-items: center; font-size: 20px;}
    </style>
</head>
<body>

    <div id="terminal-frame">
        <!-- SLEEP MODE -->
        <div id="sleep-overlay">( ˘-˘ )zZ</div>

        <!-- MAIN MENU -->
        <div id="screen-main" class="screen active-screen">
            <div class="header">
                <div id="weather">W: --°C</div>
                <div id="prayer">NEXT PRAYER: --:--</div>
            </div>
            <div class="center-clock" id="clock">00:00:00</div>
            <div id="character">( ˶ˆᗜˆ˵ )</div>
        </div>

        <!-- SETTINGS MENU -->
        <div id="screen-settings" class="screen">
            <h2 style="text-align:center;">SETTINGS</h2>
            <div class="menu-row" id="settings-row">
                <div class="menu-item selected" id="opt-theme">THEME: DARK</div>
                <div class="menu-item" id="opt-region">REGION: RUH</div>
                <div class="menu-item" id="opt-back">BACK</div>
            </div>
        </div>

        <!-- GAME MENU -->
        <div id="screen-game" class="screen">
            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span>SCORE: <span id="g-score">0</span></span>
                <span>HP: <span id="g-hp">3</span></span>
            </div>
            <div id="game-board"></div>
        </div>
    </div>

    <script>
        // --- STATE & ROUTING ---
        let currentScreen = "MAIN"; // MAIN, SETTINGS, GAME
        let gestureCooldown = false;
        let isLightMode = false;
        const regions = [
            { code: "RUH", city: "Riyadh", lat: 24.7136, lon: 46.6753 },
            { code: "JED", city: "Jeddah", lat: 21.4858, lon: 39.1925 },
            { code: "DMM", city: "Dammam", lat: 26.4207, lon: 50.0888 }
        ];
        let regionIdx = 0;
        function switchScreen(screenName) {
            document.querySelectorAll('.screen').forEach(el => el.classList.remove('active-screen'));
            document.getElementById(`screen-${screenName.toLowerCase()}`).classList.add('active-screen');
            currentScreen = screenName;
            
            if(screenName === "GAME") startGame();
            if(screenName === "MAIN") stopGame();
        }

        // --- FETCH APIs (Weather & Prayer for Riyadh) ---
        async function fetchInfo() {
            // Open-Meteo API for Riyadh
            try {
                let wRes = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${regions[regionIdx].lat}&longitude=${regions[regionIdx].lon}&current_weather=true`);
                let wData = await wRes.json();
                document.getElementById('weather').innerText = `W: ${wData.current_weather.temperature}°C`;
            } catch(e) {}

            // Aladhan API for Riyadh
            try {
                let now = new Date();
                let currentMinutes = now.getHours() * 60 + now.getMinutes();
                let date = new Date();
                let dd = String(date.getDate()).padStart(2, '0');
                let mm = String(date.getMonth() + 1).padStart(2, '0');
                let yyyy = date.getFullYear();
                let pRes = await fetch(`https://api.aladhan.com/v1/timings/${dd}-${mm}-${yyyy}?latitude=${regions[regionIdx].lat}&longitude=${regions[regionIdx].lon}&method=4`);
                let pData = await pRes.json();
                let timings = pData.data.timings;
                const schedule = [
                    { name: "Fajr", timeStr: timings.Fajr },
                    { name: "Dhuhr", timeStr: timings.Dhuhr },
                    { name: "Asr", timeStr: timings.Asr },
                    { name: "Maghrib", timeStr: timings.Maghrib },
                    { name: "Isha", timeStr: timings.Isha }
                ];
                let foundNext = false;

                for (let i = 0; i < schedule.length; i++) {
                    let timeParts = schedule[i].timeStr.split(":");
                    let prayerMins = parseInt(timeParts[0]) * 60 + parseInt(timeParts[1]);

                    // If the current time is less than 30 minutes past this prayer's time
                    if (currentMinutes < prayerMins + 30) {
                        document.getElementById('prayer').innerText = `${schedule[i].name} Prayer: ${schedule[i].timeStr}`;
                        foundNext = true;
                        break; // Stop the loop! We found the next one.
                    }
                }

                // If it's late at night and all prayers have passed, roll over to tomorrow's Fajr
                if (!foundNext) {
                    document.getElementById('prayer').innerText = `${schedule[0].name} Prayer: ${schedule[0].timeStr}`;
                }
                // --- END NEW LOGIC ---

                } catch(e) {
                    console.log("Prayer API Error:", e); // Good practice to see why it fails in the browser console
                }
        }
        fetchInfo();
        setInterval(fetchInfo, 3600000); // Update every hour

        // --- CLOCK & ANIMATION ---
        const charFrames = ["( ˶ˆᗜˆ˵ )", "( ˶>ᗜ<˵ )", "( ˶ˆᗜˆ˵ )", "( ˶-ᗜ-˵ )"];
        let frameIdx = 0;
        
        setInterval(() => {
            let d = new Date();
            document.getElementById('clock').innerText = d.toLocaleTimeString('en-US', { hour12: false });
            
            // Character Idle Animation (Swap these for image elements if using pixel art!)
            frameIdx = (frameIdx + 1) % charFrames.length;
            if(currentScreen === "MAIN") document.getElementById('character').innerText = charFrames[frameIdx];
        }, 1000);

        // --- MAIN SYSTEM LOOP ---
                setInterval(() => {
                    fetch('/data')
                        .then(r => r.json())
                        .then(data => {
                            const overlay = document.getElementById('sleep-overlay');
                            if (data.sleep_mode) {
                                overlay.style.display = 'flex';
                                return; 
                            } else {
                                overlay.style.display = 'none';
                            }

                            let gesture = data.gesture;
                            let instant = data.instant_zone;

                            // --- THE FIX: Unlock only when hand is removed ---
                            if (gesture === "NONE") {
                                gestureCooldown = false; 
                            }

                            // If we detect a gesture and we aren't in cooldown
                            if (gesture !== "NONE" && !gestureCooldown) {
                                gestureCooldown = true; // Lock instantly until hand is removed
                                
                                if (currentScreen === "MAIN") {
                                    if (gesture === "BACK") { switchScreen("SETTINGS"); }
                                    else if (gesture === "CLICK") { switchScreen("GAME"); }
                                }
                                else if (currentScreen === "SETTINGS") {
                                    handleSettingsInput(gesture);
                                }
                            }

                            if (currentScreen === "GAME") {
                                handleGameInput(instant); 
                            }
                        });
                }, 100);

        function triggerCooldown() {
            gestureCooldown = true;
            setTimeout(() => gestureCooldown = false, 1500); // 1.5s lock after switching menus
        }

        // --- SETTINGS LOGIC ---
        let settingIndex = 0;
        const settingsItems = ['opt-theme', 'opt-region', 'opt-back'];
        
        function handleSettingsInput(gesture) {
            if (gesture === "RIGHT") { settingIndex = (settingIndex + 1) % 3; }
            if (gesture === "LEFT") { settingIndex = (settingIndex - 1 + 3) % 3; }
            
            settingsItems.forEach((id, idx) => {
                document.getElementById(id).classList.toggle('selected', idx === settingIndex);
            });

            // ALL click actions must live inside this block
            if (gesture === "CLICK") {
                if (settingIndex === 0) { // Theme
                    isLightMode = !isLightMode;
                    document.body.classList.toggle('light-mode', isLightMode);
                    document.getElementById('opt-theme').innerText = isLightMode ? "THEME: LIGHT" : "THEME: DARK";
                }
                else if (settingIndex === 1) { // Region
                    regionIdx = (regionIdx + 1) % regions.length;
                    document.getElementById('opt-region').innerText = `REGION: ${regions[regionIdx].code}`;
                    fetchInfo(); 
                }
                else if (settingIndex === 2) { // Back
                    switchScreen("MAIN"); 
                }
            }
            
            if (gesture === "BACK") { switchScreen("MAIN"); }
        }

        // --- ARCADE GAME LOGIC ---
        let gameLoop, enemyLoop;
        let pX = 3, score = 0, hp = 3;
        let bullets = [], enemies = [];
        let moveLock = false, shootLock = false;

        function startGame() {
            pX = 3; score = 0; hp = 3; bullets = []; enemies = [];
            document.getElementById('g-score').innerText = score;
            document.getElementById('g-hp').innerText = hp;
            gameLoop = setInterval(drawGame, 100);
            enemyLoop = setInterval(spawnEnemy, 1500); // Enemies spawn every 1.5s
        }

        function stopGame() {
            clearInterval(gameLoop);
            clearInterval(enemyLoop);
        }

        function handleGameInput(zone) {
            if (zone === "BACK") { switchScreen("MAIN"); return; }
            
            if (zone === "LEFT" && !moveLock && pX > 0) { pX--; moveLock = true; setTimeout(()=>moveLock=false, 300); }
            if (zone === "RIGHT" && !moveLock && pX < 7) { pX++; moveLock = true; setTimeout(()=>moveLock=false, 300); }
            if (zone === "CLICK" && !shootLock) { 
                bullets.push({x: pX, y: 8}); 
                shootLock = true; setTimeout(()=>shootLock=false, 500); // Fire rate cooldown
            }
        }

        function spawnEnemy() {
            enemies.push({x: Math.floor(Math.random() * 8), y: 0});
        }

        function drawGame() {
            const board = document.getElementById('game-board');
            board.innerHTML = ""; // Clear board
            
            // Move entities
            bullets.forEach(b => b.y--);
            bullets = bullets.filter(b => b.y >= 0);
            
            // Very basic slow enemy movement
            if(Math.random() > 0.5) enemies.forEach(e => e.y++); 
            
            // Collisions
            for (let i = enemies.length - 1; i >= 0; i--) {
                let e = enemies[i];
                // Player hit
                if (e.y >= 9 && e.x === pX) {
                    hp--; document.getElementById('g-hp').innerText = hp;
                    enemies.splice(i, 1);
                    if (hp <= 0) { alert("GAME OVER! Score: " + score); switchScreen("MAIN"); return; }
                    continue;
                }
                // Missed player
                if (e.y > 9) { enemies.splice(i, 1); continue; }
                
                // Bullet hit
                for (let j = bullets.length - 1; j >= 0; j--) {
                    if (bullets[j].x === e.x && bullets[j].y === e.y) {
                        score += 10; document.getElementById('g-score').innerText = score;
                        enemies.splice(i, 1); bullets.splice(j, 1);
                        break;
                    }
                }
            }

            // Draw 8x10 Grid
            for (let y = 0; y < 10; y++) {
                for (let x = 0; x < 8; x++) {
                    let cell = document.createElement('div');
                    cell.className = 'cell';
                    
                    if (y === 9 && x === pX) cell.innerText = "▲"; // Player
                    if (bullets.some(b => b.x === x && b.y === y)) cell.innerText = "|"; // Bullet
                    if (enemies.some(e => e.x === x && e.y === y)) cell.innerText = "M"; // Enemy
                    
                    board.appendChild(cell);
                }
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def data_endpoint():
    return jsonify(system_state)

if __name__ == '__main__':
    print("Server running. Access via http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)