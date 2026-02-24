/**
 * Fluke5522A.jsx
 * Fluke 5522A Multi-Product Calibrator
 * Uses same design as Fluke 5500A
 */

import { useCallback, useState } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import './Fluke5522A.css';

// Available modes
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

function Fluke5522A({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, isComponentConnected } = useSimulator();
    const state = component.state || {};
    const isConnected = isComponentConnected(component.id);

    const [inputState, setInputState] = useState({
        primaryBuffer: '',
        secondaryBuffer: '',
        primaryUnit: '',
        secondaryUnit: '',
        activeLine: 1, // 1 or 2
        isPrimaryLocked: false
    });

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // Keypad input - Sequential Logic
    const handleKeypad = useCallback((key) => {
        if (!state.power) return;

        setInputState(prev => {
            const newState = { ...prev };

            // If primary is locked (unit selected) and user types a number,
            // automatically switch to line 2 and start typing there
            if (prev.isPrimaryLocked && prev.activeLine === 1 && !isNaN(key)) {
                newState.activeLine = 2;
                newState.secondaryBuffer = key; // Start new buffer with this key
                return newState;
            }

            // Determine active buffer key based on activeLine
            const bufferKey = newState.activeLine === 1 ? 'primaryBuffer' : 'secondaryBuffer';

            // If primary is locked but activeLine is still 1 (waiting for next input), 
            // and key is NOT a number (e.g. backspace), handle accordingly
            if (prev.isPrimaryLocked && prev.activeLine === 1) {
                if (key === 'backspace') {
                    // Unlock and allow editing unit/value again
                    newState.isPrimaryLocked = false;
                    newState.primaryUnit = '';
                    return newState;
                }
                // Ignore other keys while locked waiting for line 2 start
                return prev;
            }

            switch (key) {
                case 'C':
                    // Clear all
                    return {
                        primaryBuffer: '',
                        secondaryBuffer: '',
                        primaryUnit: '',
                        secondaryUnit: '',
                        activeLine: 1,
                        isPrimaryLocked: false
                    };
                case 'backspace':
                    // Handle backspace per line
                    if (newState[bufferKey].length > 0) {
                        newState[bufferKey] = newState[bufferKey].slice(0, -1);
                    } else if (prev.activeLine === 2 && newState[bufferKey].length === 0) {
                        // If line 2 is empty, go back to line 1 and unlock
                        newState.activeLine = 1;
                        newState.isPrimaryLocked = false;
                        newState.primaryUnit = ''; // Clear unit to allow re-entry
                    }
                    return newState;
                case '+/-':
                    if (newState[bufferKey]) {
                        const val = parseFloat(newState[bufferKey]);
                        newState[bufferKey] = String(val * -1);
                    }
                    return newState;
                case '.':
                    if (!newState[bufferKey].includes('.')) {
                        newState[bufferKey] = newState[bufferKey] ? newState[bufferKey] + '.' : '0.';
                    }
                    return newState;
                default:
                    if (!isNaN(key)) {
                        newState[bufferKey] = newState[bufferKey] + key;
                    }
                    return newState;
            }
        });
    }, [state.power]);

    // Set Unit Logic (triggered by unit buttons)
    const handleSetUnit = useCallback((unit) => {
        if (!state.power) return;

        setInputState(prev => {
            // Cannot set unit if no value entered
            if (prev.activeLine === 1 && !prev.primaryBuffer) return prev;
            if (prev.activeLine === 2 && !prev.secondaryBuffer) return prev;

            const newState = { ...prev };

            if (prev.activeLine === 1) {
                // Set primary unit, lock line 1, BUT STAY ON LINE 1 until next number input
                newState.primaryUnit = unit;
                newState.isPrimaryLocked = true;
                // activeLine remains 1
            } else if (prev.activeLine === 2) {
                // Set secondary unit
                newState.secondaryUnit = unit;
            }
            return newState;
        });
    }, [state.power]);

    // Enter - Confirm and Parse Input
    const handleEnter = useCallback(() => {
        if (!state.power) return;

        const { primaryBuffer, primaryUnit, secondaryBuffer, secondaryUnit } = inputState;

        if (!primaryBuffer) return; // Nothing to enter

        let newMode = state.mode;
        let newValue = parseFloat(primaryBuffer);
        let newFreq = state.frequency;

        // Infer Mode and Value
        if (primaryUnit === 'V') {
            if (secondaryUnit === 'Hz' || secondaryUnit === 'kH' || secondaryUnit === 'MH') { // Simplification for Hz check
                newMode = 'AC Voltage';
            } else {
                newMode = 'DC Voltage';
            }
        } else if (primaryUnit === 'A') {
            if (secondaryUnit === 'Hz' || secondaryUnit.includes('Hz')) {
                newMode = 'AC Current';
            } else {
                newMode = 'DC Current';
            }
        } else if (primaryUnit === 'Ω') {
            newMode = 'Resistance';
        } else if (primaryUnit === 'F' || primaryUnit === 'μF' || primaryUnit === 'nF' || primaryUnit === 'pF') { // Unit handling needs robustness
            newMode = 'Capacitance';
            // Handle unit prefixes for value if implemented later
        } else if (primaryUnit === 'Hz') {
            newMode = 'Frequency';
        }

        // Handle Frequency Input
        if (secondaryBuffer && (secondaryUnit === 'Hz' || secondaryUnit === 'kHz' || secondaryUnit === 'MHz')) {
            newFreq = parseFloat(secondaryBuffer);
            // handle multipliers if units have prefixes (not implemented fully in keypad yet but logic ready)
            if (secondaryUnit === 'kHz') newFreq *= 1000;
            if (secondaryUnit === 'MHz') newFreq *= 1000000;
        }

        setState({
            mode: newMode,
            value: newValue,
            unit: primaryUnit,
            frequency: newFreq
        });

        // Reset Input State
        setInputState({
            primaryBuffer: '',
            secondaryBuffer: '',
            primaryUnit: '',
            secondaryUnit: '',
            activeLine: 1,
            isPrimaryLocked: false
        });

    }, [state.power, inputState, setState, state.mode, state.frequency]);

    // Toggle power
    const togglePower = useCallback(() => {
        const newPower = !state.power;
        setState({ power: newPower, output: false });
    }, [state.power, setState]);

    // Toggle output
    const toggleOutput = useCallback(() => {
        if (state.power) {
            setState({ output: !state.output });
        }
    }, [state.power, state.output, setState]);

    // Set mode directly (from right buttons) - Clears input
    const handleSetMode = useCallback((newMode) => {
        if (!state.power || !FLUKE_MODES[newMode]) return;
        setState({ mode: newMode, unit: FLUKE_MODES[newMode].unit });
        // Clear input on mode change
        setInputState({
            primaryBuffer: '', secondaryBuffer: '', primaryUnit: '', secondaryUnit: '', activeLine: 1, isPrimaryLocked: false
        });
    }, [state.power, setState]);

    // Adjust value
    const handleAdjust = useCallback((step) => {
        if (!state.power) return;
        const newValue = (state.value || 0) + step;
        setState({ value: newValue });
    }, [state.power, state.value, setState]);

    // Frequency Adjust
    const handleFrequencyAdjust = useCallback((multiplier) => {
        if (!state.power) return;
        const currentFreq = state.frequency || 1000;
        let newFreq = multiplier > 1 ? Math.min(currentFreq * multiplier, 2000000) : Math.max(currentFreq * multiplier, 10);
        setState({ frequency: newFreq });
    }, [state.power, state.frequency, setState]);

    // Reset
    const handleReset = useCallback(() => {
        if (!state.power) return;
        setState({ value: 0, output: false });
        setInputState({ primaryBuffer: '', secondaryBuffer: '', primaryUnit: '', secondaryUnit: '', activeLine: 1, isPrimaryLocked: false });
    }, [state.power, setState]);

    // Delete
    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    const displayValue = (state.value || 0).toFixed(5);

    return (
        <div
            className={`placed-component fluke-device ${!state.power ? 'power-off' : ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Header */}
            <div className="device-header">
                <div className="device-brand">
                    <span className="fluke-logo">FLUKE</span>
                    <span className="device-model">5522A</span>
                </div>
                <button className="delete-btn" onClick={handleDelete}>×</button>
            </div>

            <div className="device-body">
                {/* Dual LCD Displays */}
                <div className="fluke-displays">
                    {/* Output Display */}
                    <div className="fluke-lcd">
                        <div className="fluke-lcd-inner">
                            <div className="fluke-lcd-label">OUTPUT DISPLAY - {mode}</div>
                            <div className="fluke-lcd-value">
                                <span>{displayValue}</span>
                                <span className="fluke-lcd-unit">{state.unit || 'V'}</span>
                            </div>
                            <div className="fluke-lcd-status" style={{ color: state.output ? '#0f0' : '#ff6b00' }}>
                                {state.output ? '● OPR' : '○ STBY'}
                                {/* Show input state on output display contextually if needed found on real device, 
                                    but usually main display shows programmed output. 
                                    Let's keep main display clean and focus on AUX display for input editing as requested "Input Display".
                                    But we can show "EDIT" status. */}
                                {(inputState.primaryBuffer || inputState.secondaryBuffer) && !state.output && (
                                    <span style={{ marginLeft: '10px', color: '#ffff00', animation: 'blink 1s infinite' }}>EDIT</span>
                                )}
                                {(mode === 'AC Voltage' || mode === 'AC Current') && (
                                    <span style={{ marginLeft: '10px', color: '#00bfff' }}>
                                        @ {state.frequency || 1000} Hz
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Auxiliary Display / Input Display */}
                    <div className="fluke-lcd">
                        <div className="fluke-lcd-inner">
                            {/* Line 1 */}
                            <div className="fluke-lcd-value" style={{ fontSize: '24px', height: '30px', display: 'flex', alignItems: 'center' }}>
                                <span style={{ color: inputState.activeLine === 1 ? '#0f0' : '#888' }}>
                                    {inputState.primaryBuffer}
                                </span>
                                <span className="fluke-lcd-unit" style={{
                                    fontSize: '14px',
                                    marginLeft: '5px',
                                    color: inputState.activeLine === 1 ? '#0f0' : '#888'
                                }}>
                                    {inputState.primaryUnit}
                                </span>
                            </div>

                            {/* Line 2 */}
                            <div className="fluke-lcd-value" style={{ fontSize: '24px', height: '30px', display: 'flex', alignItems: 'center' }}>
                                <span style={{ color: inputState.activeLine === 2 ? '#00ffff' : '#888' }}>
                                    {inputState.secondaryBuffer}
                                </span>
                                <span className="fluke-lcd-unit" style={{
                                    fontSize: '14px',
                                    marginLeft: '5px',
                                    color: inputState.activeLine === 2 ? '#00ffff' : '#888'
                                }}>
                                    {inputState.secondaryUnit}
                                </span>
                            </div>

                            <div className="fluke-lcd-status">
                                <span>{inputState.primaryBuffer || inputState.secondaryBuffer ? 'ENTER to Confirm' : 'Type to Edit'}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Main Control Panel */}
                <div className="fluke-controls">
                    {/* LEFT: Connectors */}
                    <div className="fluke-left-controls">
                        <div className="fluke-connector-panel-real">
                            {/* NORMAL Group */}
                            <div className="conn-group">
                                <div className="conn-title">NORMAL</div>
                                <div className="conn-subtitle">V, Ω, ⏚<br />RTD</div>
                                <div className="jack-container">
                                    <div className="jack-ring red">
                                        <div className="jack-hole">
                                            <ConnectionPoint
                                                type="output"
                                                componentId={component.id}
                                                polarity="hi"
                                                style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                            />
                                        </div>
                                    </div>
                                    <span className="jack-label hi">HI</span>
                                </div>
                                <div className="warning-triangle"></div>
                                <div className="jack-container">
                                    <div className="jack-ring black">
                                        <div className="jack-hole">
                                            <ConnectionPoint
                                                type="output"
                                                componentId={component.id}
                                                polarity="lo"
                                                style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                            />
                                        </div>
                                    </div>
                                    <span className="jack-label lo">LO</span>
                                </div>
                            </div>

                            {/* AUX Group */}
                            <div className="conn-group">
                                <div className="conn-title">AUX</div>
                                <div className="conn-subtitle">A, Ω-SENSE<br />AUX V</div>
                                <div className="jack-container">
                                    <div className="jack-ring red"><div className="jack-hole"></div></div>
                                </div>
                                <div className="jack-container">
                                    <div className="jack-ring black"><div className="jack-hole"></div></div>
                                </div>
                            </div>

                            {/* SCOPE Group */}
                            <div className="conn-group">
                                <div className="conn-title">SCOPE</div>
                                <div className="conn-subtitle">150V PK<br />MAX</div>
                                <div className="bnc"><div className="bnc-inner"><div className="bnc-pin"></div></div></div>
                                <div className="conn-title" style={{ marginTop: '5px' }}>TRIG<br />OUT</div>
                                <div className="bnc"><div className="bnc-inner"><div className="bnc-pin"></div></div></div>
                            </div>

                            {/* TC Slot */}
                            <div className="tc-slot">
                                <span className="tc-label">TC</span>
                                <div className="tc-hole"></div>
                                <div className="tc-hole"></div>
                            </div>
                        </div>
                    </div>

                    {/* CENTER: Keypad */}
                    <div className="fluke-keypad">
                        {/* Function Row */}
                        <div className="fluke-function-row-left">
                            <button className="fluke-func-btn" onClick={() => setState({ output: false })}>STBY</button>
                            <button className="fluke-func-btn" onClick={toggleOutput}>OPR</button>
                            <button className="fluke-func-btn">EARTH</button>
                            <button className="fluke-func-btn">SCOPE</button>
                            <button className="fluke-func-btn">BOOST</button>
                            <button className="fluke-func-btn">PREV MENU</button>
                        </div>

                        {/* Main Grid */}
                        <div className="fluke-main-grid">
                            {/* Row 1 */}
                            <button className="fluke-key" onClick={() => handleKeypad('7')}>7</button>
                            <button className="fluke-key" onClick={() => handleKeypad('8')}>8</button>
                            <button className="fluke-key" onClick={() => handleKeypad('9')}>9</button>
                            <div></div>
                            <button className="fluke-key small" onClick={() => handleSetUnit('m')}>m / μ</button>
                            <button className="fluke-key small" onClick={() => handleSetUnit('V')}>V / dBm</button>
                            <button className="fluke-key small" onClick={() => handleSetUnit('Hz')}>Hz / s</button>

                            {/* Row 2 */}
                            <button className="fluke-key" onClick={() => handleKeypad('4')}>4</button>
                            <button className="fluke-key" onClick={() => handleKeypad('5')}>5</button>
                            <button className="fluke-key" onClick={() => handleKeypad('6')}>6</button>
                            <div></div>
                            <button className="fluke-key small">k / n</button>
                            <button className="fluke-key small" onClick={() => handleSetUnit('A')}>A / W</button>
                            <button className="fluke-key small" onClick={() => handleSetMode('Temperature')}>°C / °F</button>

                            {/* Row 3 */}
                            <button className="fluke-key" onClick={() => handleKeypad('1')}>1</button>
                            <button className="fluke-key" onClick={() => handleKeypad('2')}>2</button>
                            <button className="fluke-key" onClick={() => handleKeypad('3')}>3</button>
                            <div></div>
                            <button className="fluke-key small">M / p</button>
                            <button className="fluke-key small" onClick={() => handleSetMode('Resistance')}>Ω</button>
                            <button className="fluke-key small" onClick={() => handleSetMode('Capacitance')}>f (CAP)</button>

                            {/* Row 4 */}
                            <button className="fluke-key function" onClick={() => handleKeypad('+/-')}>+/−</button>
                            <button className="fluke-key" onClick={() => handleKeypad('0')}>0</button>
                            <button className="fluke-key" onClick={() => handleKeypad('.')}>.</button>
                            <div></div>
                            <button className="fluke-key small" onClick={() => handleKeypad('C')}>CE</button>
                            <button className="fluke-key small" onClick={() => handleKeypad('backspace')}>←</button>
                            <button className="fluke-key enter" onClick={handleEnter}>ENTER</button>
                        </div>
                    </div>

                    {/* RIGHT: Controls */}
                    <div className="fluke-right-controls">
                        {/* Arrow Buttons - Value Adjustment */}
                        <div className="fluke-softkey-row">
                            <button className="fluke-triangle-btn" onClick={() => handleAdjust(10)} title="Value +10">▲</button>
                            <button className="fluke-triangle-btn" onClick={() => handleAdjust(-10)} title="Value -10">▼</button>
                            <button className="fluke-triangle-btn" onClick={() => handleAdjust(-1)} title="Value -1">◀</button>
                            <button className="fluke-triangle-btn" onClick={() => handleAdjust(1)} title="Value +1">▶</button>
                        </div>

                        <div className="fluke-right-lower">
                            {/* Mode Selection Stack */}
                            <div className="fluke-func-stack">
                                <button
                                    className={`fluke-key small ${mode === 'DC Voltage' ? 'active' : ''}`}
                                    onClick={() => handleSetMode('DC Voltage')}
                                    style={mode === 'DC Voltage' ? { background: '#2ecc71' } : {}}
                                >DC V</button>
                                <button
                                    className={`fluke-key small ${mode === 'AC Voltage' ? 'active' : ''}`}
                                    onClick={() => handleSetMode('AC Voltage')}
                                    style={mode === 'AC Voltage' ? { background: '#2ecc71' } : {}}
                                >AC V</button>
                                <button
                                    className={`fluke-key small ${mode === 'DC Current' ? 'active' : ''}`}
                                    onClick={() => handleSetMode('DC Current')}
                                    style={mode === 'DC Current' ? { background: '#2ecc71' } : {}}
                                >DC A</button>
                                <button
                                    className={`fluke-key small ${mode === 'AC Current' ? 'active' : ''}`}
                                    onClick={() => handleSetMode('AC Current')}
                                    style={mode === 'AC Current' ? { background: '#2ecc71' } : {}}
                                >AC A</button>
                                <button
                                    className={`fluke-key small ${mode === 'Resistance' ? 'active' : ''}`}
                                    onClick={() => handleSetMode('Resistance')}
                                    style={mode === 'Resistance' ? { background: '#2ecc71' } : {}}
                                >Ω</button>
                                <button
                                    className={`fluke-key small ${mode === 'Capacitance' ? 'active' : ''}`}
                                    onClick={() => handleSetMode('Capacitance')}
                                    style={mode === 'Capacitance' ? { background: '#2ecc71' } : {}}
                                >CAP</button>
                                <button
                                    className={`fluke-key small ${mode === 'Frequency' ? 'active' : ''}`}
                                    onClick={() => handleSetMode('Frequency')}
                                    style={mode === 'Frequency' ? { background: '#2ecc71' } : {}}
                                >Hz</button>
                                <button className="fluke-key small" onClick={handleReset}>RESET</button>
                            </div>

                            {/* Frequency Control & Knob */}
                            <div className="fluke-edit-knob-stack">
                                {/* Frequency Adjust (for AC modes) */}
                                {(mode === 'AC Voltage' || mode === 'AC Current') && (
                                    <div className="fluke-edit-field-group">
                                        <button className="fluke-white-btn" onClick={() => handleFrequencyAdjust(0.1)} title="Freq /10">÷10</button>
                                        <span style={{ fontSize: '8px', padding: '2px 4px', background: '#333', color: '#0ff', borderRadius: '3px' }}>
                                            {state.frequency || 1000} Hz
                                        </span>
                                        <button className="fluke-white-btn" onClick={() => handleFrequencyAdjust(10)} title="Freq x10">×10</button>
                                    </div>
                                )}
                                <div className="fluke-edit-field-group">
                                    <button className="fluke-white-btn" onClick={() => handleAdjust(-0.1)} title="-0.1">-0.1</button>
                                    <button className="fluke-white-btn" style={{ minWidth: '50px', fontSize: '8px' }}>FINE<br />ADJ</button>
                                    <button className="fluke-white-btn" onClick={() => handleAdjust(0.1)} title="+0.1">+0.1</button>
                                </div>
                                <div className="fluke-knob">
                                    <div className="knob-label">ADJUST</div>
                                </div>
                            </div>
                        </div>

                        {/* Power Button */}
                        <div className="fluke-power-section">
                            <div className="fluke-power-label">POWER</div>
                            <button
                                className={`fluke-power-btn-real ${state.power ? 'power-on' : ''}`}
                                onClick={togglePower}
                            ></button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Connection Status */}
            <div className="connection-indicator">
                <div className={`status-led ${isConnected ? 'connected' : ''}`}></div>
            </div>
        </div>
    );
}

export default Fluke5522A;
