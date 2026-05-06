/**
 * OscilloscopeCalibrator.jsx
 * Precision Oscilloscope Calibrator
 * Generates precise signals for calibrating oscilloscopes
 */

import { useCallback, useState } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import './OscilloscopeCalibrator.css';

// Waveform types
const WAVEFORMS = ['Square', 'Sine', 'Triangle', 'Pulse'];

// Frequency presets (Hz)
const FREQUENCY_PRESETS = [1, 10, 100, 1000, 10000, 100000, 1000000];

// Amplitude presets (Vpp)
const AMPLITUDE_PRESETS = [0.001, 0.01, 0.1, 1, 10];

function OscilloscopeCalibrator({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, isComponentConnected } = useSimulator();
    const state = component.state || {};
    const isConnected = isComponentConnected(component.id);

    const [inputBuffer, setInputBuffer] = useState('');
    const [editingField, setEditingField] = useState(null); // 'frequency', 'amplitude', 'offset'

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

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

    // Set waveform
    const setWaveform = useCallback((waveform) => {
        if (!state.power) return;
        setState({ waveform });
    }, [state.power, setState]);

    // Set frequency preset
    const setFrequencyPreset = useCallback((freq) => {
        if (!state.power) return;
        setState({ frequency: freq });
    }, [state.power, setState]);

    // Set amplitude preset
    const setAmplitudePreset = useCallback((amp) => {
        if (!state.power) return;
        setState({ amplitude: amp });
    }, [state.power, setState]);

    // Adjust value
    const adjustValue = useCallback((field, direction) => {
        if (!state.power) return;
        const multiplier = direction > 0 ? 1.1 : 0.9;
        const newValue = (state[field] || 1) * multiplier;
        setState({ [field]: parseFloat(newValue.toPrecision(3)) });
    }, [state, setState]);

    // Set impedance
    const setImpedance = useCallback((impedance) => {
        if (!state.power) return;
        setState({ impedance });
    }, [state.power, setState]);

    // Toggle marker
    const toggleMarker = useCallback(() => {
        if (!state.power) return;
        setState({ marker: !state.marker });
    }, [state.power, state.marker, setState]);

    // Adjust duty cycle
    const adjustDutyCycle = useCallback((direction) => {
        if (!state.power) return;
        const newDuty = Math.max(10, Math.min(90, (state.dutyCycle || 50) + direction * 5));
        setState({ dutyCycle: newDuty });
    }, [state.power, state.dutyCycle, setState]);

    // Keypad input
    const handleKeypad = useCallback((key) => {
        if (!state.power || !editingField) return;

        if (key === 'C') {
            setInputBuffer('');
        } else if (key === 'ENTER') {
            const value = parseFloat(inputBuffer);
            if (!isNaN(value) && value > 0) {
                setState({ [editingField]: value });
            }
            setInputBuffer('');
            setEditingField(null);
        } else if (key === '.') {
            if (!inputBuffer.includes('.')) {
                setInputBuffer(prev => prev + '.');
            }
        } else if (!isNaN(key)) {
            setInputBuffer(prev => prev + key);
        }
    }, [state.power, editingField, inputBuffer, setState]);

    // Start editing field
    const startEditing = useCallback((field) => {
        if (!state.power) return;
        setEditingField(field);
        setInputBuffer('');
    }, [state.power]);

    // Delete device
    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    // Format frequency display
    const formatFrequency = (freq) => {
        if (freq >= 1000000) return `${(freq / 1000000).toFixed(3)} MHz`;
        if (freq >= 1000) return `${(freq / 1000).toFixed(3)} kHz`;
        return `${freq.toFixed(3)} Hz`;
    };

    // Format amplitude display
    const formatAmplitude = (amp) => {
        if (amp >= 1) return `${amp.toFixed(3)} Vpp`;
        return `${(amp * 1000).toFixed(1)} mVpp`;
    };

    return (
        <div
            className={`placed-component osc-calibrator-device ${!state.power ? 'power-off' : ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Header */}
            <div className="device-header">
                <div className="device-brand">
                    <span className="cal-logo">FLUKE</span>
                    <span className="device-model">9500B</span>
                </div>
                <button className="delete-btn" onClick={handleDelete}>×</button>
            </div>

            <div className="device-body">
                {/* Main Display */}
                <div className="cal-display">
                    <div className="cal-lcd">
                        <div className="cal-lcd-inner">
                            {/* Waveform indicator */}
                            <div className="waveform-indicator">
                                <span className="waveform-icon">
                                    {state.waveform === 'Square' && '⊓⊔'}
                                    {state.waveform === 'Sine' && '∿'}
                                    {state.waveform === 'Triangle' && '△'}
                                    {state.waveform === 'Pulse' && '⊓_'}
                                </span>
                                <span className="waveform-name">{state.waveform || 'Square'}</span>
                            </div>

                            {/* Main values */}
                            <div className="cal-main-display">
                                <div className="display-row">
                                    <span className="label">FREQ:</span>
                                    <span className={`value ${editingField === 'frequency' ? 'editing' : ''}`}>
                                        {editingField === 'frequency' ? inputBuffer || '_' : formatFrequency(state.frequency || 1000)}
                                    </span>
                                </div>
                                <div className="display-row">
                                    <span className="label">AMPL:</span>
                                    <span className={`value ${editingField === 'amplitude' ? 'editing' : ''}`}>
                                        {editingField === 'amplitude' ? inputBuffer || '_' : formatAmplitude(state.amplitude || 1)}
                                    </span>
                                </div>
                                <div className="display-row small">
                                    <span className="label">OFFSET:</span>
                                    <span className="value">{(state.offset || 0).toFixed(3)} V</span>
                                </div>
                            </div>

                            {/* Status row */}
                            <div className="cal-status-row">
                                <span className={`status-item ${state.output ? 'active' : ''}`}>
                                    {state.output ? 'OUTPUT ON' : 'STANDBY'}
                                </span>
                                <span className="status-item">{state.impedance || '50Ω'}</span>
                                <span className={`status-item ${state.marker ? 'active' : ''}`}>
                                    {state.marker ? 'MKR' : ''}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Control Panel */}
                <div className="cal-controls">
                    {/* Left: Output Connectors */}
                    <div className="cal-output-section">
                        <div className="output-connector">
                            <div className="connector-label">MAIN OUTPUT</div>
                            <div className="bnc-connector">
                                <div className={`bnc-body ${state.output ? 'active' : ''}`}>
                                    <div className="bnc-center">
                                        <ConnectionPoint
                                            type="output"
                                            componentId={component.id}
                                            polarity="main"
                                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="output-connector">
                            <div className="connector-label">MARKER</div>
                            <div className="bnc-connector small">
                                <div className={`bnc-body ${state.marker ? 'active' : ''}`}>
                                    <div className="bnc-center">
                                        <ConnectionPoint
                                            type="output"
                                            componentId={component.id}
                                            polarity="marker"
                                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <button
                            className={`marker-btn ${state.marker ? 'active' : ''}`}
                            onClick={toggleMarker}
                            disabled={!state.power}
                        >
                            MARKER
                        </button>
                    </div>

                    {/* Center: Waveform & Parameters */}
                    <div className="cal-main-controls">
                        {/* Waveform Selection */}
                        <div className="control-section">
                            <div className="section-label">WAVEFORM</div>
                            <div className="waveform-buttons">
                                {WAVEFORMS.map((wf) => (
                                    <button
                                        key={wf}
                                        className={`wf-btn ${state.waveform === wf ? 'selected' : ''}`}
                                        onClick={() => setWaveform(wf)}
                                        disabled={!state.power}
                                    >
                                        {wf}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Frequency Presets */}
                        <div className="control-section">
                            <div className="section-label">FREQUENCY</div>
                            <div className="preset-buttons">
                                {FREQUENCY_PRESETS.map((freq) => (
                                    <button
                                        key={freq}
                                        className={`preset-btn ${state.frequency === freq ? 'selected' : ''}`}
                                        onClick={() => setFrequencyPreset(freq)}
                                        disabled={!state.power}
                                    >
                                        {freq >= 1000000 ? `${freq / 1000000}M` : freq >= 1000 ? `${freq / 1000}k` : freq}
                                    </button>
                                ))}
                            </div>
                            <div className="adjust-row">
                                <button onClick={() => adjustValue('frequency', -1)} disabled={!state.power}>−</button>
                                <button onClick={() => startEditing('frequency')} disabled={!state.power}>EDIT</button>
                                <button onClick={() => adjustValue('frequency', 1)} disabled={!state.power}>+</button>
                            </div>
                        </div>

                        {/* Amplitude Presets */}
                        <div className="control-section">
                            <div className="section-label">AMPLITUDE</div>
                            <div className="preset-buttons">
                                {AMPLITUDE_PRESETS.map((amp) => (
                                    <button
                                        key={amp}
                                        className={`preset-btn ${state.amplitude === amp ? 'selected' : ''}`}
                                        onClick={() => setAmplitudePreset(amp)}
                                        disabled={!state.power}
                                    >
                                        {amp >= 1 ? `${amp}V` : `${amp * 1000}mV`}
                                    </button>
                                ))}
                            </div>
                            <div className="adjust-row">
                                <button onClick={() => adjustValue('amplitude', -1)} disabled={!state.power}>−</button>
                                <button onClick={() => startEditing('amplitude')} disabled={!state.power}>EDIT</button>
                                <button onClick={() => adjustValue('amplitude', 1)} disabled={!state.power}>+</button>
                            </div>
                        </div>

                        {/* Duty Cycle (for Square/Pulse) */}
                        {(state.waveform === 'Square' || state.waveform === 'Pulse') && (
                            <div className="control-section">
                                <div className="section-label">DUTY CYCLE</div>
                                <div className="duty-control">
                                    <button onClick={() => adjustDutyCycle(-1)} disabled={!state.power}>−</button>
                                    <span className="duty-value">{state.dutyCycle || 50}%</span>
                                    <button onClick={() => adjustDutyCycle(1)} disabled={!state.power}>+</button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right: Output & Power */}
                    <div className="cal-power-section">
                        {/* Impedance Selection */}
                        <div className="impedance-section">
                            <div className="section-label">IMPEDANCE</div>
                            <div className="impedance-buttons">
                                <button
                                    className={`imp-btn ${state.impedance === '50Ω' ? 'selected' : ''}`}
                                    onClick={() => setImpedance('50Ω')}
                                    disabled={!state.power}
                                >
                                    50Ω
                                </button>
                                <button
                                    className={`imp-btn ${state.impedance === '1MΩ' ? 'selected' : ''}`}
                                    onClick={() => setImpedance('1MΩ')}
                                    disabled={!state.power}
                                >
                                    1MΩ
                                </button>
                            </div>
                        </div>

                        {/* Keypad for editing */}
                        {editingField && (
                            <div className="mini-keypad">
                                <div className="keypad-row">
                                    <button onClick={() => handleKeypad('7')}>7</button>
                                    <button onClick={() => handleKeypad('8')}>8</button>
                                    <button onClick={() => handleKeypad('9')}>9</button>
                                </div>
                                <div className="keypad-row">
                                    <button onClick={() => handleKeypad('4')}>4</button>
                                    <button onClick={() => handleKeypad('5')}>5</button>
                                    <button onClick={() => handleKeypad('6')}>6</button>
                                </div>
                                <div className="keypad-row">
                                    <button onClick={() => handleKeypad('1')}>1</button>
                                    <button onClick={() => handleKeypad('2')}>2</button>
                                    <button onClick={() => handleKeypad('3')}>3</button>
                                </div>
                                <div className="keypad-row">
                                    <button onClick={() => handleKeypad('C')}>C</button>
                                    <button onClick={() => handleKeypad('0')}>0</button>
                                    <button onClick={() => handleKeypad('.')}>.</button>
                                </div>
                                <button className="enter-btn" onClick={() => handleKeypad('ENTER')}>ENTER</button>
                            </div>
                        )}

                        {/* Output Button */}
                        <button
                            className={`output-btn ${state.output ? 'active' : ''}`}
                            onClick={toggleOutput}
                            disabled={!state.power}
                        >
                            {state.output ? 'OUTPUT ON' : 'OUTPUT OFF'}
                        </button>

                        {/* Power Button */}
                        <div className="power-button-section">
                            <div className="power-label">POWER</div>
                            <button
                                className={`power-btn ${state.power ? 'power-on' : ''}`}
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

export default OscilloscopeCalibrator;
