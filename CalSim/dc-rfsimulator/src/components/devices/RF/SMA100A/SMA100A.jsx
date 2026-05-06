/**
 * SMA100A.jsx
 * R&S SMA100A Signal Generator Component
 * Realistic panel design matching the reference image
 */

import { useCallback } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import './SMA100A.css';

function SMA100A({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent } = useSimulator();
    const state = component.state;

    // Update device state helper
    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // Power toggle
    const togglePower = useCallback(() => {
        const newPower = !state.power;
        setState({
            power: newPower,
            rfOn: newPower ? state.rfOn : false
        });
        console.log(`🔌 SMA100A [${component.id}] Power: ${newPower ? 'ON' : 'OFF'}`);
    }, [state.power, state.rfOn, setState, component.id]);

    // RF toggle
    const toggleRF = useCallback(() => {
        if (!state.power) return;
        const newRf = !state.rfOn;
        setState({ rfOn: newRf });
        console.log(`📡 SMA100A [${component.id}] RF: ${newRf ? 'ON' : 'OFF'}`);
    }, [state.power, state.rfOn, setState, component.id]);

    // MOD toggle
    const toggleMod = useCallback(() => {
        if (!state.power) return;
        setState({ modOn: !state.modOn });
    }, [state.power, state.modOn, setState]);

    // Keypad input
    const handleKeypad = useCallback((key) => {
        if (!state.power) return;

        let newBuffer = state.inputBuffer;
        if (key === '-') {
            newBuffer = newBuffer === '-' ? '' : (newBuffer === '' ? '-' : newBuffer);
        } else if (key === '.') {
            if (!newBuffer.includes('.')) newBuffer += '.';
        } else {
            newBuffer += key;
        }
        setState({ inputBuffer: newBuffer });
    }, [state.power, state.inputBuffer, setState]);

    // Backspace
    const handleBackspace = useCallback(() => {
        if (!state.power) return;
        setState({ inputBuffer: state.inputBuffer.slice(0, -1) });
    }, [state.power, state.inputBuffer, setState]);

    // Enter with unit (frequency)
    const handleEnterUnit = useCallback((unit) => {
        if (!state.power || !state.inputBuffer) return;

        let value = parseFloat(state.inputBuffer);
        if (isNaN(value)) return;

        // Convert to GHz
        switch (unit) {
            case 'G': break; // Already GHz
            case 'M': value = value / 1000; break;
            case 'k': value = value / 1000000; break;
            case 'x1': value = value / 1000000000; break;
            default: break;
        }

        // Validate range (9 kHz - 6 GHz)
        if (value >= 0.000009 && value <= 6) {
            setState({ frequency: value, inputBuffer: '' });
            console.log(`📡 SMA100A [${component.id}] Frequency: ${value} GHz`);
        } else {
            alert('⚠️ Frequency out of range (9 kHz - 6 GHz)');
        }
    }, [state.power, state.inputBuffer, setState, component.id]);

    // Set frequency via prompt
    const setFrequency = useCallback(() => {
        if (!state.power) return;
        const input = prompt('Enter Frequency (GHz):', state.frequency);
        if (input !== null && !isNaN(input) && input !== '') {
            const freq = parseFloat(input);
            if (freq >= 0.000009 && freq <= 6) {
                setState({ frequency: freq });
            } else {
                alert('⚠️ Frequency must be between 9 kHz and 6 GHz');
            }
        }
    }, [state.power, state.frequency, setState]);

    // Set level via prompt
    const setLevel = useCallback(() => {
        if (!state.power) return;
        const input = prompt('Enter Level (dBm):', state.level);
        if (input !== null && !isNaN(input) && input !== '') {
            const level = parseFloat(input);
            if (level >= -145 && level <= 18) {
                setState({ level });
            } else {
                alert('⚠️ Level must be between -145 dBm and +18 dBm');
            }
        }
    }, [state.power, state.level, setState]);

    // Arrow key adjustment
    const handleArrow = useCallback((direction) => {
        if (!state.power) return;
        const step = 0.001; // 1 MHz
        let newFreq = state.frequency;
        if (direction === 'up') newFreq = Math.min(6, newFreq + step);
        if (direction === 'down') newFreq = Math.max(0.000009, newFreq - step);
        setState({ frequency: newFreq });
    }, [state.power, state.frequency, setState]);

    // Preset reset
    const handlePreset = useCallback(() => {
        if (!window.confirm('Reset SMA100A to default settings?')) return;
        setState({
            power: true,
            frequency: 1.000000000,
            level: -20.00,
            rfOn: false,
            modOn: false,
            inputBuffer: '',
        });
    }, [setState]);

    // Format frequency display
    const formatFrequency = (freq) => {
        const str = freq.toFixed(11);
        const parts = str.split('.');
        const dec = parts[1];
        return `${parts[0]}.${dec.substring(0, 3)} ${dec.substring(3, 6)} ${dec.substring(6, 9)} ${dec.substring(9, 11)}`;
    };

    // Delete component
    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    return (
        <div
            className={`placed-component sma-device ${!state.power ? 'power-off' : ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Delete Button */}
            <button className="sma-delete-btn" onClick={handleDelete}>×</button>

            {/* Top Bar */}
            <div className="sma-top-bar">
                <div className="sma-brand">
                    <span className="sma-brand-logo">ROHDE&SCHWARZ</span>
                    <span className="sma-brand-name">R&S®SMA</span>
                </div>
                <div className="sma-model-info">SMA 100 A - SIGNAL GENERATOR - 9 kHz ... 6 GHz</div>
                <div className="sma-serial">1400.0000.02</div>
            </div>

            {/* Main Body */}
            <div className="sma-body">
                {/* Zone 1: System & Power */}
                <div className="sma-zone1">
                    <button className="sma-preset-btn" onClick={handlePreset}>PRESET</button>
                    <button className="sma-system-btn">LOCAL</button>
                    <button className="sma-system-btn">SETUP</button>
                    <button className="sma-system-btn">INFO</button>
                    <button className="sma-help-btn">HELP</button>
                    <button
                        className={`sma-power-btn ${state.power ? 'on' : ''}`}
                        onClick={togglePower}
                    ></button>
                </div>

                {/* Zone 2: Display */}
                <div className="sma-zone2">
                    <div className="sma-screen-frame">
                        <div className="sma-screen">
                            {/* Screen Header */}
                            <div className="sma-screen-header">
                                <span>Freq</span>
                                <span>Level</span>
                                <span>ALC-Auto</span>
                            </div>

                            {/* Frequency Display */}
                            <div className="sma-freq-display" onClick={setFrequency}>
                                <div className="sma-freq-label">Frequency</div>
                                <div>
                                    <span className="sma-freq-value">{formatFrequency(state.frequency)}</span>
                                    <span className="sma-freq-unit">{state.frequencyUnit}</span>
                                </div>
                            </div>

                            {/* Level Display */}
                            <div className="sma-level-display" onClick={setLevel}>
                                <div className="sma-level-label">Level</div>
                                <div>
                                    <span className="sma-level-value">{state.level.toFixed(2)}</span>
                                    <span className="sma-level-unit">dBm</span>
                                </div>
                            </div>

                            {/* Status Row */}
                            <div className="sma-status-row">
                                <span className={`sma-status-item ${state.rfOn ? 'active' : ''}`}>
                                    RF {state.rfOn ? 'ON' : 'OFF'}
                                </span>
                                <span className={`sma-status-item ${state.modOn ? 'active' : ''}`}>
                                    MOD {state.modOn ? 'ON' : 'OFF'}
                                </span>
                                <span className="sma-status-item">REF: INT</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Zone 3: Function Keys */}
                <div className="sma-zone3">
                    <div className="sma-func-row">
                        <button className="sma-func-btn highlight" onClick={setFrequency}>FREQ</button>
                        <button className="sma-func-btn highlight" onClick={setLevel}>LEVEL</button>
                    </div>
                    <div className="sma-func-row">
                        <button
                            className={`sma-func-btn rf-on ${state.rfOn ? 'active' : ''}`}
                            onClick={toggleRF}
                        >
                            RF<br />ON/OFF
                        </button>
                        <button
                            className={`sma-func-btn ${state.modOn ? 'active' : ''}`}
                            onClick={toggleMod}
                        >
                            MOD<br />ON/OFF
                        </button>
                    </div>
                    <div className="sma-func-row">
                        <button className="sma-func-btn">REARR</button>
                        <button className="sma-func-btn">FILE</button>
                    </div>
                    <div className="sma-func-row">
                        <button className="sma-func-btn">WINBAR</button>
                        <button className="sma-func-btn" onClick={handleBackspace}>BACK<br />SPACE</button>
                    </div>
                </div>

                {/* Zone 4: Keypad & Units */}
                <div className="sma-zone4">
                    <div className="sma-keypad">
                        {['7', '8', '9', '4', '5', '6', '1', '2', '3', '-', '0', '.'].map((key) => (
                            <button
                                key={key}
                                className={`sma-key ${key === '-' ? 'sign' : ''}`}
                                onClick={() => handleKeypad(key)}
                            >
                                {key}
                            </button>
                        ))}
                    </div>

                    <div className="sma-units">
                        <button className="sma-unit-btn" onClick={() => handleEnterUnit('G')}>
                            G/n<span className="sub">dBµV</span>
                        </button>
                        <button className="sma-unit-btn" onClick={() => handleEnterUnit('M')}>
                            M/µ<span className="sub">µV</span>
                        </button>
                        <button className="sma-unit-btn" onClick={() => handleEnterUnit('k')}>
                            k/m<span className="sub">mV</span>
                        </button>
                        <button className="sma-unit-btn" onClick={() => handleEnterUnit('x1')}>
                            x1<span className="sub">dB(m)</span>
                        </button>
                    </div>
                </div>

                {/* Zone 5: Navigation & Control */}
                <div className="sma-zone5">
                    <div className="sma-knob" title="Drag to adjust value"></div>

                    <div className="sma-nav-row">
                        <button className="sma-nav-btn">ESC<br />CLOSE</button>
                        <button className="sma-nav-btn">ON/OFF<br />TOGGLE</button>
                    </div>
                    <div className="sma-nav-row">
                        <button className="sma-nav-btn">DIAGRAM</button>
                        <button className="sma-nav-btn">MENU</button>
                    </div>

                    <div className="sma-arrows">
                        <div></div>
                        <button className="sma-arrow-btn up" onClick={() => handleArrow('up')}>▲</button>
                        <div></div>
                        <button className="sma-arrow-btn left">◀</button>
                        <button className="sma-arrow-btn center">ENTER</button>
                        <button className="sma-arrow-btn right">▶</button>
                        <div></div>
                        <button className="sma-arrow-btn down" onClick={() => handleArrow('down')}>▼</button>
                        <div></div>
                    </div>
                </div>

                {/* Zone 6: Connectors */}
                <div className="sma-zone6">
                    <div className="sma-connector-group">
                        <div className="sma-connector-label">LF</div>
                        <div className="sma-bnc"><div className="sma-bnc-inner"></div></div>
                    </div>
                    <div className="sma-connector-group">
                        <div className="sma-connector-label">AM EXT</div>
                        <div className="sma-bnc"><div className="sma-bnc-inner"></div></div>
                    </div>
                    <div className="sma-connector-group">
                        <div className="sma-connector-label">FM/PM EXT</div>
                        <div className="sma-bnc"><div className="sma-bnc-inner"></div></div>
                    </div>
                    <div className="sma-connector-group">
                        <div className="sma-connector-label">SENSOR</div>
                        <div className="sma-sensor-port">
                            <div className="sma-sensor-pin"></div>
                            <div className="sma-sensor-pin"></div>
                            <div className="sma-sensor-pin"></div>
                            <div className="sma-sensor-pin"></div>
                        </div>
                    </div>
                    <div className="sma-connector-group">
                        <div className="sma-connector-label">USB</div>
                        <div className="sma-usb"></div>
                    </div>

                    {/* RF Output */}
                    <div className="sma-rf-output">
                        <div className="sma-connector-label">RF 50Ω</div>
                        <div className="sma-rf-connector">
                            <div className="sma-rf-inner"></div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Connection Point */}
            <ConnectionPoint
                type="output"
                componentId={component.id}
                style={{ right: '30px', bottom: '25px' }}
            />
        </div>
    );
}

export default SMA100A;
