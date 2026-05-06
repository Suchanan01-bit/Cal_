/**
 * FPC1500.jsx
 * R&S FPC1500 Spectrum Analyzer Component
 */

import { useCallback, useState, useEffect } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import ComplianceBadge from '../../../common/ComplianceBadge';
import './FPC1500.css';
import '../../../common/ComplianceBadge.css';


function FPC1500({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, uncertaintyMode } = useSimulator();
    // Default state if not present
    const state = component.state || {
        power: false,
        centerFreq: 1.0, // GHz
        span: 0.5,      // GHz
        refLevel: 0,    // dBm
        inputBuffer: '',
    };

    // Helper to update state
    const setState = useCallback((newState) => {
        updateDeviceState(component.id, { ...state, ...newState });
    }, [component.id, state, updateDeviceState]);

    const togglePower = useCallback(() => {
        setState({ power: !state.power });
    }, [state.power, setState]);

    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    const handleKeypad = useCallback((key) => {
        if (!state.power) return;
        let newBuffer = state.inputBuffer;

        if (key === 'bksp') {
            newBuffer = newBuffer.slice(0, -1);
        } else if (key === '.') {
            if (!newBuffer.includes('.')) newBuffer += '.';
        } else if (key === '-') {
            newBuffer = newBuffer.startsWith('-') ? newBuffer.slice(1) : '-' + newBuffer;
        } else {
            newBuffer += key;
        }
        setState({ inputBuffer: newBuffer });
    }, [state.power, state.inputBuffer, setState]);

    const handleEnter = useCallback((unit = 'G') => {
        if (!state.power || !state.inputBuffer) return;
        const val = parseFloat(state.inputBuffer);
        if (isNaN(val)) return;

        // Apply to Center Freq for now as default action
        let freq = val;
        // Simple unit conversion logic for demo
        if (unit === 'M') freq /= 1000;

        setState({ centerFreq: freq, inputBuffer: '' });
    }, [state.power, state.inputBuffer, setState]);

    // Simulated spectrum trace
    const generateTracePath = () => {
        if (!state.power) return '';
        const width = 100;
        const height = 100;
        let path = `M 0,${height / 2} `;

        // Use a stable random based on component ID or something so it doesn't jitter too wildly
        // But for "live" feel we might want jitter.
        // Let's just make a simple bump in the middle
        for (let i = 0; i <= width; i += 2) {
            let y = height - 10; // Noise floor
            // Signal at center
            const center = width / 2;
            const dist = Math.abs(i - center);
            if (dist < 10) {
                y -= (80 * Math.exp(-dist * dist / 20)); // Gaussian peak
            }
            // Add noise
            y += (Math.random() * 5 - 2.5);
            path += `L ${i},${y} `;
        }
        return path;
    };

    const [tracePath, setTracePath] = useState('');

    useEffect(() => {
        if (state.power) {
            const interval = setInterval(() => {
                setTracePath(generateTracePath());
            }, 100);
            return () => clearInterval(interval);
        } else {
            setTracePath('');
        }
    }, [state.power]);

    // Get compliance info
    const complianceInfo = state.complianceStatus ? {
        compliance: { className: 'compliance' },
        non_compliance: { className: 'non-compliance' },
        out_of_tolerance: { className: 'out-of-tolerance' }
    }[state.complianceStatus] : null;

    return (
        <div
            className={`placed-component fpc-device ${!state.power ? 'power-off' : ''} ${complianceInfo?.className || ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Compliance Badge */}
            <ComplianceBadge status={state.complianceStatus} visible={uncertaintyMode} />

            <button className="fpc-delete-btn" onClick={handleDelete}>×</button>

            {/* Top Bar */}
            <div className="fpc-top-bar">
                <div className="fpc-brand">
                    <span className="fpc-brand-logo">ROHDE&SCHWARZ</span>
                    <span className="fpc-model">FPC1500 · Spectrum Analyzer</span>
                </div>
            </div>

            <div className="fpc-main">
                {/* Screen Area */}
                <div className="fpc-screen-area">
                    <div className="fpc-screen-content">
                        <div className="fpc-screen-header">
                            <span style={{ flex: 1 }}>Center: {state.centerFreq.toFixed(3)} GHz</span>
                            <span style={{ flex: 1 }}>Span: {state.span} GHz</span>
                            <span>Ref: {state.refLevel} dBm</span>
                        </div>
                        {state.inputBuffer && (
                            <div style={{ position: 'absolute', top: '50px', left: '20px', background: 'white', color: 'black', padding: '5px', zIndex: 10 }}>
                                Input: {state.inputBuffer}
                            </div>
                        )}
                        <div className="fpc-grid">
                            {/* Grid Lines */}
                            {Array.from({ length: 100 }).map((_, i) => (
                                <div key={i} className="fpc-grid-line"></div>
                            ))}
                            {/* Trace */}
                            <svg className="fpc-trace-path" viewBox="0 0 100 100" preserveAspectRatio="none">
                                <path d={tracePath} fill="none" stroke="#ffff00" strokeWidth="0.5" />
                            </svg>
                        </div>
                    </div>

                    {/* Soft Keys - vertical right side of screen */}
                    <div className="fpc-soft-keys">
                        <div className="fpc-soft-key">Freq</div>
                        <div className="fpc-soft-key">Span</div>
                        <div className="fpc-soft-key">Ampt</div>
                        <div className="fpc-soft-key">Mkr</div>
                        <div className="fpc-soft-key">Mkr{'->'}</div>
                        <div className="fpc-soft-key">BW</div>
                        <div className="fpc-soft-key">Sweep</div>
                        <div className="fpc-soft-key">Trace</div>
                    </div>
                </div>

                {/* Right Control Panel */}
                <div className="fpc-controls">
                    {/* Function Block */}
                    <div className="fpc-func-block">
                        <button className="fpc-btn-rect">Freq</button>
                        <button className="fpc-btn-rect">Span</button>
                        <button className="fpc-btn-rect">Ampt</button>
                        <button className="fpc-btn-rect">Mkr</button>
                        <button className="fpc-btn-rect">Mkr ▶</button>

                        <button className="fpc-btn-rect">BW</button>
                        <button className="fpc-btn-rect">Sweep</button>
                        <button className="fpc-btn-rect">Trace</button>
                        <button className="fpc-btn-rect">Lines</button>
                        <button className="fpc-btn-rect">📷</button>

                        <button className="fpc-btn-rect">Meas</button>
                        <button className="fpc-btn-rect">Mode</button>
                        <button className="fpc-btn-rect">Setup</button>
                        <button className="fpc-btn-rect">Save</button>
                        <button className="fpc-btn-rect green">Preset</button>
                    </div>

                    {/* Keypad and Knob */}
                    <div className="fpc-input-area">
                        <div className="fpc-keypad">
                            {['7', '8', '9', '4', '5', '6', '1', '2', '3', '-', '0', '.'].map(k => (
                                <button key={k} className="fpc-keypad-btn" onClick={() => handleKeypad(k)}>{k}</button>
                            ))}
                            <button className="fpc-keypad-btn dark" onClick={() => handleKeypad('bksp')}>⌫</button>
                            <button className="fpc-keypad-btn dark">Esc</button>
                            <button className="fpc-keypad-btn dark" onClick={() => handleEnter()}>✓</button>
                        </div>

                        <div className="fpc-knob-area">
                            <div className="fpc-knob-label">GHz</div>
                            <div className="fpc-knob"></div>
                            <div className="fpc-nav-keys">
                                <div></div><button className="fpc-nav-btn">▲</button><div></div>
                                <button className="fpc-nav-btn">◀</button><div></div><button className="fpc-nav-btn">▶</button>
                                <div></div><button className="fpc-nav-btn">▼</button><div></div>
                            </div>
                        </div>
                    </div>

                    {/* Bottom Area: Power and Connectors */}
                    <div className="fpc-bottom-panel">
                        <div className="fpc-ports">
                            <div className="fpc-usb"></div>
                            <div className="fpc-usb"></div>
                            <div className="fpc-audio"></div>
                        </div>

                        <div className="fpc-power-btn icon" onClick={togglePower}>
                            ⏻
                        </div>

                        <div className="fpc-connector">
                            <div className="fpc-connector-label">RF Output</div>
                            <div className="fpc-n-type"></div>
                            {/* Tracking Generator Output */}
                            <ConnectionPoint
                                type="output"
                                componentId={component.id}
                                style={{ bottom: '15px', right: '115px' }}
                            />
                        </div>

                        <div className="fpc-connector">
                            <div className="fpc-connector-label">RF Input</div>
                            <div className="fpc-n-type"></div>
                            {/* RF Input */}
                            <ConnectionPoint
                                type="input"
                                componentId={component.id}
                                style={{ bottom: '15px', right: '35px' }}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default FPC1500;
