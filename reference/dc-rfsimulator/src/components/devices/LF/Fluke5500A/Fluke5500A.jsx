/**
 * Fluke5500A.jsx
 * Fluke 5500A Multi-Product Calibrator
 * Converted from manual design (fluke5500a.js)
 */

import { useCallback, useState } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import './Fluke5500A.css';

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

function Fluke5500A({ component, onMouseDown, style }) {
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

            // SEQUENCE LOGIC:
            // If primary is locked (unit entered), and user types a NUMBER,
            // we automatically move to Line 2 (if not already there).
            if (prev.isPrimaryLocked && prev.activeLine === 1 && !isNaN(key)) {
                newState.activeLine = 2;
                newState.secondaryBuffer = key; // Start line 2 with this number
                return newState;
            }

            // Determine which line we are editing
            const isLine1 = (newState.activeLine === 1);
            const bufferKey = isLine1 ? 'primaryBuffer' : 'secondaryBuffer';

            // Special Case: Backspace behavior
            if (key === 'backspace') {
                if (newState[bufferKey].length > 0) {
                    newState[bufferKey] = newState[bufferKey].slice(0, -1);
                } else {
                    // Buffer is empty
                    if (prev.activeLine === 2) {
                        // If Line 2 empty, go back to Line 1
                        newState.activeLine = 1;
                        // Optional: Unlock primary if we want to edit it again?
                        // For now, let's keep it locked unless they backspace the unit?
                        // Actually user said: "when input unit, first line locks... when input number, second line appears"
                        // So going back should probably just clear line 2. 
                        // If they want to edit line 1, they might need to clear or backspace further.
                        // Let's allow unlocking if they backspace on Line 1.
                    } else if (prev.activeLine === 1 && prev.isPrimaryLocked) {
                        // If on Line 1 and it's locked, backspace unlocks it (removes unit effectively)
                        newState.isPrimaryLocked = false;
                        newState.primaryUnit = '';
                    }
                }
                return newState;
            }

            // If Line 1 is locked and we are still on Line 1 (and key is NOT number, handled above),
            // prevent editing Line 1 numeric value. 
            // e.g. User presses '.' or '+/-' while locked -> Ignore
            if (isLine1 && newState.isPrimaryLocked) {
                return prev;
            }

            switch (key) {
                case 'C':
                    // Clear keys
                    if (prev.activeLine === 2) {
                        // If on line 2, clear line 2 only first? Or clear all?
                        // Usually 'C' clears everything or current line.
                        // Let's output 'C' clears ALL for simplicity or reset logic.
                        return {
                            primaryBuffer: '',
                            secondaryBuffer: '',
                            primaryUnit: '',
                            secondaryUnit: '',
                            activeLine: 1,
                            isPrimaryLocked: false
                        };
                    } else {
                        return {
                            primaryBuffer: '',
                            secondaryBuffer: '',
                            primaryUnit: '',
                            secondaryUnit: '',
                            activeLine: 1,
                            isPrimaryLocked: false
                        };
                    }
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

    // Enter - confirm value
    const handleEnter = useCallback(() => {
        if (!state.power) return;

        const { primaryBuffer, primaryUnit, secondaryBuffer, secondaryUnit } = inputState;

        if (!primaryBuffer) return; // Nothing to enter

        let newMode = state.mode;
        let newValue = parseFloat(primaryBuffer);
        let newFreq = state.frequency;

        // Logic to determine mode based on units
        // Primary = Value, Secondary = Frequency (usually) for AC
        // Or Primary = Value, Secondary = nothing for DC

        if (primaryUnit === 'V') {
            if (secondaryBuffer && (secondaryUnit === 'Hz' || secondaryUnit === 'kHz' || secondaryUnit === 'MHz')) {
                newMode = 'AC Voltage';
            } else {
                newMode = 'DC Voltage';
            }
        } else if (primaryUnit === 'A') {
            if (secondaryBuffer && (secondaryUnit === 'Hz' || secondaryUnit.includes('Hz'))) {
                newMode = 'AC Current';
            } else {
                newMode = 'DC Current';
            }
        } else if (primaryUnit === 'Ω') {
            newMode = 'Resistance';
        } else if (primaryUnit === 'F' || primaryUnit.includes('F')) {
            newMode = 'Capacitance';
        } else if (primaryUnit === 'Hz') {
            newMode = 'Frequency';
        } else if (primaryUnit === '°C' || primaryUnit === '°F') {
            newMode = 'Temperature';
        }

        // Parse Frequency if present
        if (secondaryBuffer && secondaryUnit.includes('z')) {
            let fVal = parseFloat(secondaryBuffer);
            if (secondaryUnit === 'kHz') fVal *= 1000;
            if (secondaryUnit === 'MHz') fVal *= 1000000;
            newFreq = fVal;
        }

        // Update Device State
        setState({
            mode: newMode,
            value: newValue,
            unit: primaryUnit,
            frequency: newFreq,
            output: false // Usually output turns off or stays? Let's keep it checks manual behavior. Usually safety off on value change.
        });

        // Clear Input
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

    // Set mode (Arrows)
    const handleSetMode = useCallback((newMode) => {
        if (!state.power || !FLUKE_MODES[newMode]) return;
        setState({ mode: newMode, unit: FLUKE_MODES[newMode].unit });
        // Clear input on mode change
        setInputState({
            primaryBuffer: '', secondaryBuffer: '', primaryUnit: '', secondaryUnit: '', activeLine: 1, isPrimaryLocked: false
        });
    }, [state.power, setState]);

    // Set unit prefix
    const handleSetUnit = useCallback((unit) => {
        if (!state.power) return;

        setInputState(prev => {
            // Cannot set unit if no value entered on current line
            if (prev.activeLine === 1 && !prev.primaryBuffer) return prev;
            if (prev.activeLine === 2 && !prev.secondaryBuffer) return prev;

            const newState = { ...prev };

            if (prev.activeLine === 1) {
                // Set primary unit and LOCK line 1
                newState.primaryUnit = unit;
                newState.isPrimaryLocked = true;
                // We STAY on activeLine 1. 
                // The switch to line 2 happens when the user types the next NUMBER.
            } else {
                // Set secondary unit
                newState.secondaryUnit = unit;
            }
            return newState;
        });
    }, [state.power]);

    // Adjust value
    const handleAdjust = useCallback((direction) => {
        if (!state.power) return;
        const step = Math.abs(state.value || 0) < 10 ? 0.1 : 1;
        setState({ value: (state.value || 0) + step * direction });
    }, [state.power, state.value, setState]);

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

    // Construct Auxiliary Display Content
    // We want to show 1 or 2 lines depending on state
    const showLine2 = inputState.secondaryBuffer || (inputState.activeLine === 2);

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
                    <span className="device-model">5500A</span>
                </div>
                <button className="delete-btn" onClick={handleDelete}>×</button>
            </div>

            <div className="device-body">
                {/* Dual LCD Displays */}
                <div className="fluke-displays">
                    {/* Output Display */}
                    <div className="fluke-lcd">
                        <div className="fluke-lcd-inner">
                            <div className="fluke-lcd-label">OUTPUT DISPLAY</div>
                            <div className="fluke-lcd-value">
                                <span>{displayValue}</span>
                                <span className="fluke-lcd-unit">{state.unit || 'V'}</span>
                            </div>
                            {/* If AC, show freq? Use small text if needed or alternating? For now simplified. */}
                            {state.mode && state.mode.includes('AC') && state.frequency ? (
                                <div style={{ fontSize: '14px', color: '#0c0', textAlign: 'right' }}>
                                    {state.frequency} Hz
                                </div>
                            ) : null}
                            <div className="fluke-lcd-status" style={{ color: state.output ? '#0f0' : '#ff6b00' }}>
                                {state.output ? 'OPR' : 'STBY'}
                            </div>
                        </div>
                    </div>

                    {/* Auxiliary Display */}
                    <div className="fluke-lcd">
                        <div className="fluke-lcd-inner" style={{ justifyContent: 'flex-start' }}>
                            <div className="fluke-lcd-label">AUXILIARY DISPLAY</div>

                            {/* Render Line 1 */}
                            <div className="fluke-lcd-value" style={{ fontSize: '20px', minHeight: '24px' }}>
                                <span>{inputState.primaryBuffer}</span>
                                <span className="fluke-lcd-unit" style={{ fontSize: '16px' }}>{inputState.primaryUnit}</span>
                            </div>

                            {/* Render Line 2 */}
                            {showLine2 && (
                                <div className="fluke-lcd-value" style={{ fontSize: '20px', minHeight: '24px' }}>
                                    <span>{inputState.secondaryBuffer}</span>
                                    <span className="fluke-lcd-unit" style={{ fontSize: '16px' }}>{inputState.secondaryUnit}</span>
                                </div>
                            )}

                            <div className="fluke-lcd-status" style={{ marginTop: 'auto' }}>
                                Mode: <span>{state.mode || 'DC Voltage'}</span>
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
                                    <div className="jack-ring red">
                                        <div className="jack-hole">
                                            <ConnectionPoint
                                                type="output"
                                                componentId={component.id}
                                                polarity="aux_hi"
                                                style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                            />
                                        </div>
                                    </div>
                                    <span className="jack-label hi">HI</span>
                                </div>

                                {/* Spacer to align LO with Normal LO (matches warning-triangle height) */}
                                <div style={{ height: '18px', width: '100%' }}></div>

                                <div className="jack-container">
                                    <div className="jack-ring black">
                                        <div className="jack-hole">
                                            <ConnectionPoint
                                                type="output"
                                                componentId={component.id}
                                                polarity="aux_lo"
                                                style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                            />
                                        </div>
                                    </div>
                                    <span className="jack-label lo">LO</span>
                                </div>

                                {/* Spacer for GUARD jack */}
                                <div style={{ height: '18px', width: '100%' }}></div>

                                <div className="jack-container">
                                    <div className="jack-ring" style={{ background: 'radial-gradient(circle at 30% 30%, #66ff66, #22cc22 70%, #119911)', border: '2px solid #006600' }}>
                                        <div className="jack-hole">
                                            <ConnectionPoint
                                                type="output"
                                                componentId={component.id}
                                                polarity="guard"
                                                style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                            />
                                        </div>
                                    </div>
                                    <span className="jack-label" style={{ color: '#006600', right: '-14px' }}>GUARD</span>
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
                        {/* Arrow Buttons */}
                        <div className="fluke-softkey-row">
                            <button className="fluke-triangle-btn" onClick={() => handleSetMode('DC Voltage')}>▲</button>
                            <button className="fluke-triangle-btn" onClick={() => handleSetMode('AC Voltage')}>▼</button>
                            <button className="fluke-triangle-btn" onClick={() => handleSetMode('DC Current')}>◀</button>
                            <button className="fluke-triangle-btn" onClick={() => handleSetMode('AC Current')}>▶</button>
                        </div>

                        <div className="fluke-right-lower">
                            {/* Function Stack */}
                            <div className="fluke-func-stack">
                                <button className="fluke-key small">SETUP</button>
                                <button className="fluke-key small" onClick={handleReset}>RESET</button>
                                <button className="fluke-key small">NEW REF</button>
                                <button className="fluke-key small" onClick={() => handleKeypad('C')}>CE</button>
                                <button className="fluke-key small">MEAS TC</button>
                                <button className="fluke-key small">TRIG OUT</button>
                                <button className="fluke-key small">MULT X</button>
                                <button className="fluke-key small">DIV ÷</button>
                            </div>

                            {/* Edit & Knob */}
                            <div className="fluke-edit-knob-stack">
                                <div className="fluke-edit-field-group">
                                    <button className="fluke-white-btn" onClick={() => handleAdjust(-1)}>◀</button>
                                    <button className="fluke-white-btn" style={{ minWidth: '60px', fontSize: '9px' }}>EDIT<br />FIELD</button>
                                    <button className="fluke-white-btn" onClick={() => handleAdjust(1)}>▶</button>
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

export default Fluke5500A;
