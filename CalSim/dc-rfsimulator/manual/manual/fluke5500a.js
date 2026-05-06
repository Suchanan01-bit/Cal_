/* ============================================
   FLUKE5500A.JS - Fluke 5500A Calibrator
   ============================================ */

/**
 * Module สำหรับ Fluke 5500A Multi-Product Calibrator
 * 
 * Features:
 * - Power On/Off
 * - Output On/Off (OPR/STBY)
 * - Keypad Input
 * - Multiple modes (DC V, AC V, DC A, AC A, Ω, etc.)
 * - Unit Selection
 */

// Global State สำหรับ Fluke 5500A ทั้งหมด
let flukeStates = {};

// รายการ Mode ที่รองรับ
const FLUKE_MODES = {
    'DC Voltage': { unit: 'V', prefix: '', maxValue: 1020 },
    'AC Voltage': { unit: 'V', prefix: '~', maxValue: 1020 },
    'DC Current': { unit: 'A', prefix: '', maxValue: 20 },
    'AC Current': { unit: 'A', prefix: '~', maxValue: 20 },
    'Resistance': { unit: 'Ω', prefix: '', maxValue: 1e9 },
    'Capacitance': { unit: 'F', prefix: '', maxValue: 1e-3 },
    'Frequency': { unit: 'Hz', prefix: '', maxValue: 2e6 },
    'Temperature': { unit: '°C', prefix: '', maxValue: 2315 }
};

/**
 * สร้าง HTML สำหรับ Fluke 5500A
 * @param {number} id - Component ID
 * @returns {string} - HTML string
 */
function createFluke(id) {
    // กำหนดค่าเริ่มต้น
    flukeStates[id] = {
        power: true,
        output: false,
        mode: 'DC Voltage',
        value: 0,
        unit: 'V',
        baseValue: 0,
        inputBuffer: '0'
    };

    return `
        <div class="fluke-device" id="fluke-device-${id}">
            <div class="device-header">
                <div class="device-brand">
                    <span class="fluke-logo">FLUKE</span>
                    <span class="device-model">5500A</span>
                </div>
                <button class="delete-btn" onclick="deleteComponent(${id})">×</button>
            </div>
            
            <div class="device-body" style="padding: 10px;">
                <!-- Dual LCD Displays -->
                <div class="fluke-displays" style="margin-bottom: 20px;">
                    <!-- Output Display (Left) -->
                    <div class="fluke-lcd" style="flex: 1;">
                        <div class="fluke-lcd-inner">
                            <div class="fluke-lcd-label">OUTPUT DISPLAY</div>
                            <div class="fluke-lcd-value">
                                <span id="fluke-value-${id}">0.00000</span>
                                <span class="fluke-lcd-unit" id="fluke-unit-${id}">V</span>
                            </div>
                            <div class="fluke-lcd-status" id="fluke-status-${id}">STBY</div>
                        </div>
                    </div>
                    
                    <!-- Auxiliary Display (Right) -->
                    <div class="fluke-lcd" style="flex: 1;">
                        <div class="fluke-lcd-inner">
                            <div class="fluke-lcd-label">AUXILIARY DISPLAY</div>
                            <div class="fluke-lcd-value" style="font-size:28px;">
                                <span id="fluke-input-${id}">0</span>
                            </div>
                            <div class="fluke-lcd-status">
                                Mode: <span id="fluke-mode-${id}">DC Voltage</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Main Control Panel -->
                <div class="fluke-controls">
                    <!-- 1. LEFT: Connectors -->
                    <div class="fluke-left-controls">
                        <div class="fluke-connector-panel-real">
                            <!-- NORMAL Group -->
                            <div class="conn-group">
                                <div class="conn-title">NORMAL</div>
                                <div class="conn-subtitle">V, Ω, ⏚<br>RTD</div>
                                <div class="jack-container">
                                    <div class="jack-ring red" data-connection="output" data-component-id="${id}">
                                        <div class="jack-hole"></div>
                                    </div>
                                    <span class="jack-label hi">HI</span>
                                    <span class="limit-text limit-normal-hi">1000V<br>RMS<br>MAX</span>
                                </div>
                                <div class="warning-triangle"></div>
                                <div class="jack-container">
                                    <div class="jack-ring black"><div class="jack-hole"></div></div>
                                    <span class="jack-label lo">LO</span>
                                    <span class="limit-text limit-normal-lo">20V PK<br>MAX</span>
                                </div>
                                <div class="ground-symbol" style="margin-left: -30px;"></div>
                            </div>

                            <!-- AUX Group -->
                            <div class="conn-group">
                                <div class="conn-title">AUX</div>
                                <div class="conn-subtitle">A, Ω -SENSE,<br>AUX V</div>
                                <div class="jack-container">
                                    <div class="jack-ring red"><div class="jack-hole"></div></div>
                                    <span class="limit-text limit-aux-hi">20V<br>RMS<br>MAX</span>
                                </div>
                                <div class="jack-container">
                                    <div class="jack-ring black"><div class="jack-hole"></div></div>
                                    <span class="limit-text limit-aux-lo">1V PK<br>MAX</span>
                                </div>
                            </div>

                            <!-- SCOPE Group -->
                            <div class="conn-group">
                                <div class="conn-title">SCOPE</div>
                                <div class="conn-subtitle">150V PK<br>MAX</div>
                                <div class="bnc"><div class="bnc-inner"><div class="bnc-pin"></div></div></div>
                                <div class="conn-title" style="margin-top: 5px;">TRIG<br>OUT</div>
                                <div class="bnc"><div class="bnc-inner"><div class="bnc-pin"></div></div></div>
                            </div>

                            <!-- TC Slot -->
                            <div class="tc-slot">
                                <span class="tc-label">TC</span>
                                <div class="tc-hole"></div>
                                <div class="tc-hole"></div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 2. CENTER: Keypad & Unit Selectors -->
                    <div class="fluke-keypad" style="flex: 1; display: flex; flex-direction: column; gap: 5px;">
                        <!-- Top Function Row -->
                        <div class="fluke-function-row-left">
                            <button class="fluke-func-btn" onclick="setFlukeStandby(${id})">STBY</button>
                            <button class="fluke-func-btn" onclick="toggleFlukeOutput(${id})">OPR</button>
                            <button class="fluke-func-btn">EARTH</button>
                            <button class="fluke-func-btn">SCOPE</button>
                            <button class="fluke-func-btn">BOOST</button>
                            <button class="fluke-func-btn">PREV MENU</button>
                        </div>
                        
                        <!-- Main Button Grid (7 columns) -->
                        <div class="fluke-main-grid">
                            <!-- Row 1: Numbers 7-8-9 + Units -->
                            <button class="fluke-key" onclick="flukeKeypad(${id},'7')">7</button>
                            <button class="fluke-key" onclick="flukeKeypad(${id},'8')">8</button>
                            <button class="fluke-key" onclick="flukeKeypad(${id},'9')">9</button>
                            <div></div>
                            <button class="fluke-key small" onclick="flukeSetUnit(${id},'m')">m / μ</button>
                            <button class="fluke-key small" onclick="flukeSetUnit(${id},'V')">V / dBm</button>
                            <button class="fluke-key small" onclick="flukeSetUnit(${id},'Hz')">Hz / s</button>

                            <!-- Row 2: Numbers 4-5-6 + Units -->
                            <button class="fluke-key" onclick="flukeKeypad(${id},'4')">4</button>
                            <button class="fluke-key" onclick="flukeKeypad(${id},'5')">5</button>
                            <button class="fluke-key" onclick="flukeKeypad(${id},'6')">6</button>
                            <div></div>
                            <button class="fluke-key small" onclick="flukeSetUnit(${id},'k')">k / n</button>
                            <button class="fluke-key small" onclick="flukeSetUnit(${id},'A')">A / W</button>
                            <button class="fluke-key small" onclick="flukeSetMode(${id},'Temperature')">°C / °F</button>

                            <!-- Row 3: Numbers 1-2-3 + Units -->
                            <button class="fluke-key" onclick="flukeKeypad(${id},'1')">1</button>
                            <button class="fluke-key" onclick="flukeKeypad(${id},'2')">2</button>
                            <button class="fluke-key" onclick="flukeKeypad(${id},'3')">3</button>
                            <div></div>
                            <button class="fluke-key small" onclick="flukeSetUnit(${id},'M')">M / p</button>
                            <button class="fluke-key small" onclick="flukeSetMode(${id},'Resistance')">Ω</button>
                            <button class="fluke-key small" onclick="flukeSetMode(${id},'Capacitance')">f (CAP)</button>

                            <!-- Row 4: +/- 0 . + Enter -->
                            <button class="fluke-key function" onclick="flukeKeypad(${id},'+/-')">+/−</button>
                            <button class="fluke-key" onclick="flukeKeypad(${id},'0')">0</button>
                            <button class="fluke-key" onclick="flukeKeypad(${id},'.')">.</button>
                            <div></div>
                            <button class="fluke-key small" onclick="flukeKeypad(${id},'C')">CE</button>
                            <button class="fluke-key small" onclick="flukeKeypad(${id},'backspace')">←</button>
                            <button class="fluke-key enter" onclick="flukeEnter(${id})">ENTER</button>
                        </div>
                    </div>
                    
                    <!-- 3. RIGHT: Controls -->
                    <div class="fluke-right-controls">
                        <!-- Softkey Row -->
                        <div class="fluke-softkey-row">
                            <button class="fluke-triangle-btn" onclick="flukeSetMode(${id},'DC Voltage')">▲</button>
                            <button class="fluke-triangle-btn" onclick="flukeSetMode(${id},'AC Voltage')">▼</button>
                            <button class="fluke-triangle-btn" onclick="flukeSetMode(${id},'DC Current')">◀</button>
                            <button class="fluke-triangle-btn" onclick="flukeSetMode(${id},'AC Current')">▶</button>
                        </div>

                        <!-- Function Stack & Knob -->
                        <div class="fluke-right-lower">
                            <!-- Left Column: Function Keys -->
                            <div class="fluke-func-stack">
                                <button class="fluke-key small">SETUP</button>
                                <button class="fluke-key small" onclick="flukeReset(${id})">RESET</button>
                                <button class="fluke-key small">NEW REF</button>
                                <button class="fluke-key small" onclick="flukeKeypad(${id},'C')">CE</button>
                                <button class="fluke-key small">MEAS TC</button>
                                <button class="fluke-key small">TRIG OUT</button>
                                <button class="fluke-key small" onclick="flukeMultiply(${id})">MULT X</button>
                                <button class="fluke-key small" onclick="flukeDivide(${id})">DIV ÷</button>
                            </div>

                            <!-- Right Column: Edit & Knob -->
                            <div class="fluke-edit-knob-stack">
                                <div class="fluke-edit-field-group">
                                    <button class="fluke-white-btn" style="min-width: 30px;" onclick="flukeAdjust(${id}, -1)">◀</button>
                                    <button class="fluke-white-btn" style="min-width: 60px; font-size:9px; line-height:1.1;">EDIT<br>FIELD</button>
                                    <button class="fluke-white-btn" style="min-width: 30px;" onclick="flukeAdjust(${id}, 1)">▶</button>
                                </div>
                                <div class="fluke-knob">
                                    <div style="position:absolute; bottom:-15px; width:100%; text-align:center; font-size:8px; color:#555;">ADJUST</div>
                                </div>
                            </div>
                        </div>

                        <!-- Power Switch Section -->
                        <div class="fluke-power-section">
                            <div class="fluke-power-label">POWER</div>
                            <button class="fluke-power-btn-real power-on" id="fluke-power-btn-${id}" onclick="toggleFlukePower(${id})"></button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/* ============================================
   POWER CONTROL
   ============================================ */

/**
 * เปิด/ปิดเครื่อง
 * @param {number} id - Component ID
 */
function toggleFlukePower(id) {
    const state = flukeStates[id];
    state.power = !state.power;
    
    const device = document.getElementById(`fluke-device-${id}`);
    const btn = document.getElementById(`fluke-power-btn-${id}`);
    
    if (state.power) {
        btn.classList.add('power-on');
        device.classList.remove('power-off');
        console.log(`🔌 Fluke 5500A [${id}] Power: ON`);
    } else {
        btn.classList.remove('power-on');
        device.classList.add('power-off');
        // Turn off output when power off
        if (state.output) {
            toggleFlukeOutput(id);
        }
        console.log(`🔌 Fluke 5500A [${id}] Power: OFF`);
    }
}

/* ============================================
   OUTPUT CONTROL
   ============================================ */

/**
 * เปิด/ปิด Output (OPR/STBY)
 * @param {number} id - Component ID
 */
function toggleFlukeOutput(id) {
    const state = flukeStates[id];
    
    // Guard: ต้องเปิดเครื่องก่อน
    if (!state.power) {
        console.warn('⚠️ Please turn on power first');
        return;
    }
    
    state.output = !state.output;
    const statusEl = document.getElementById(`fluke-status-${id}`);
    
    if (statusEl) {
        if (state.output) {
            statusEl.textContent = 'OPR';
            statusEl.style.color = '#0f0';
            console.log(`⚡ Fluke 5500A [${id}] Output: OPERATE`);
        } else {
            statusEl.textContent = 'STBY';
            statusEl.style.color = '#ff6b00';
            console.log(`⚡ Fluke 5500A [${id}] Output: STANDBY`);
        }
    }
    
    // อัปเดตการเชื่อมต่อ
    if (typeof updateConnections === 'function') {
        updateConnections();
    }
}

/**
 * ตั้งค่าเป็น Standby
 * @param {number} id - Component ID
 */
function setFlukeStandby(id) {
    const state = flukeStates[id];
    if (state.output) {
        toggleFlukeOutput(id);
    }
}

/* ============================================
   KEYPAD INPUT
   ============================================ */

/**
 * รับค่าจาก Keypad
 * @param {number} id - Component ID
 * @param {string} key - ปุ่มที่กด
 */
function flukeKeypad(id, key) {
    const state = flukeStates[id];
    
    // Guard: ต้องเปิดเครื่องก่อน
    if (!state.power) return;
    
    switch (key) {
        case 'C':
            // Clear
            state.inputBuffer = '0';
            break;
            
        case 'backspace':
            // ลบตัวสุดท้าย
            if (state.inputBuffer.length > 1) {
                state.inputBuffer = state.inputBuffer.slice(0, -1);
            } else {
                state.inputBuffer = '0';
            }
            break;
            
        case '+/-':
            // สลับเครื่องหมาย
            const val = parseFloat(state.inputBuffer);
            state.inputBuffer = String(val * -1);
            break;
            
        case '.':
            // จุดทศนิยม
            if (!state.inputBuffer.includes('.')) {
                state.inputBuffer += '.';
            }
            break;
            
        default:
            // ตัวเลข 0-9
            if (!isNaN(key)) {
                if (state.inputBuffer === '0') {
                    state.inputBuffer = key;
                } else {
                    state.inputBuffer += key;
                }
            }
    }
    
    // อัปเดต Display
    const inputEl = document.getElementById(`fluke-input-${id}`);
    if (inputEl) {
        inputEl.textContent = state.inputBuffer;
    }
}

/**
 * กด Enter - ยืนยันค่า
 * @param {number} id - Component ID
 */
function flukeEnter(id) {
    const state = flukeStates[id];
    
    // Guard: ต้องเปิดเครื่องก่อน
    if (!state.power) return;
    
    const value = parseFloat(state.inputBuffer);
    
    if (!isNaN(value)) {
        state.value = value;
        state.baseValue = value;
        state.inputBuffer = '0';
        
        updateFlukeDisplay(id);
        
        // อัปเดตการเชื่อมต่อ
        if (typeof updateConnections === 'function') {
            updateConnections();
        }
        
        console.log(`✅ Fluke 5500A [${id}] Value set to: ${value} ${state.unit}`);
    }
}

/* ============================================
   MODE & UNIT SELECTION
   ============================================ */

/**
 * เปลี่ยน Mode
 * @param {number} id - Component ID
 * @param {string} mode - Mode name
 */
function flukeSetMode(id, mode) {
    const state = flukeStates[id];
    if (!state.power) return;
    
    if (FLUKE_MODES[mode]) {
        state.mode = mode;
        state.unit = FLUKE_MODES[mode].unit;
        
        // อัปเดต Display
        document.getElementById(`fluke-mode-${id}`).textContent = mode;
        document.getElementById(`fluke-unit-${id}`).textContent = state.unit;
        
        console.log(`🔧 Fluke 5500A [${id}] Mode: ${mode}`);
    }
}

/**
 * เปลี่ยน Unit Prefix
 * @param {number} id - Component ID
 * @param {string} unit - Unit string
 */
function flukeSetUnit(id, unit) {
    const state = flukeStates[id];
    if (!state.power) return;
    
    // Map units to modes
    const unitModeMap = {
        'V': 'DC Voltage',
        'A': 'DC Current',
        'Hz': 'Frequency'
    };
    
    if (unitModeMap[unit]) {
        flukeSetMode(id, unitModeMap[unit]);
    }
    
    // Handle prefix (m, k, M)
    // TODO: Implement prefix logic
}

/* ============================================
   MATH FUNCTIONS
   ============================================ */

/**
 * คูณค่าปัจจุบัน
 * @param {number} id - Component ID
 */
function flukeMultiply(id) {
    const state = flukeStates[id];
    if (!state.power) return;
    
    const multiplier = prompt('Multiply by:', '10');
    if (multiplier && !isNaN(multiplier)) {
        state.value = state.value * parseFloat(multiplier);
        updateFlukeDisplay(id);
        console.log(`✖️ Fluke 5500A [${id}] Multiplied by ${multiplier}`);
    }
}

/**
 * หารค่าปัจจุบัน
 * @param {number} id - Component ID
 */
function flukeDivide(id) {
    const state = flukeStates[id];
    if (!state.power) return;
    
    const divisor = prompt('Divide by:', '10');
    if (divisor && !isNaN(divisor) && parseFloat(divisor) !== 0) {
        state.value = state.value / parseFloat(divisor);
        updateFlukeDisplay(id);
        console.log(`➗ Fluke 5500A [${id}] Divided by ${divisor}`);
    }
}

/**
 * Adjust ค่าด้วยลูกศร
 * @param {number} id - Component ID
 * @param {number} direction - 1 = เพิ่ม, -1 = ลด
 */
function flukeAdjust(id, direction) {
    const state = flukeStates[id];
    if (!state.power) return;
    
    // Adjust by step (based on current value magnitude)
    const step = Math.abs(state.value) < 10 ? 0.1 : 1;
    state.value += step * direction;
    updateFlukeDisplay(id);
}

/* ============================================
   DISPLAY UPDATE
   ============================================ */

/**
 * อัปเดต Display
 * @param {number} id - Component ID
 */
function updateFlukeDisplay(id) {
    const state = flukeStates[id];
    
    const valueEl = document.getElementById(`fluke-value-${id}`);
    const inputEl = document.getElementById(`fluke-input-${id}`);
    
    if (valueEl) {
        valueEl.textContent = state.value.toFixed(5);
    }
    if (inputEl) {
        inputEl.textContent = state.inputBuffer;
    }
}

/**
 * Reset ค่าทั้งหมด
 * @param {number} id - Component ID
 */
function flukeReset(id) {
    const state = flukeStates[id];
    if (!state.power) return;
    
    state.value = 0;
    state.baseValue = 0;
    state.inputBuffer = '0';
    state.output = false;
    
    updateFlukeDisplay(id);
    
    const statusEl = document.getElementById(`fluke-status-${id}`);
    if (statusEl) {
        statusEl.textContent = 'STBY';
        statusEl.style.color = '#ff6b00';
    }
    
    if (typeof updateConnections === 'function') {
        updateConnections();
    }
    
    console.log(`🔄 Fluke 5500A [${id}] RESET`);
}

/* ============================================
   UTILITY FUNCTIONS
   ============================================ */

/**
 * ดึงค่า Output สำหรับส่งต่อ
 * @param {number} id - Component ID
 * @returns {object} - Output values
 */
function getFlukeOutput(id) {
    const state = flukeStates[id];
    if (state && state.power && state.output) {
        return {
            value: state.value,
            unit: state.unit,
            mode: state.mode,
            active: true
        };
    }
    return { active: false };
}

/**
 * ลบ State เมื่อ Component ถูกลบ
 * @param {number} id - Component ID
 */
function removeFlukeState(id) {
    delete flukeStates[id];
}

console.log('✅ fluke5500a.js loaded');
