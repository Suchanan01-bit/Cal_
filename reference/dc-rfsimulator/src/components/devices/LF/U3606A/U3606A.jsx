/**
 * U3606A.jsx
 * Keysight U3606B - 5½ Digit Multimeter + DC Power Supply
 * Realistic panel design based on reference image
 */

import { useCallback, useState } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import ComplianceBadge from '../../../common/ComplianceBadge';
import { useUncertaintyMode } from '../../../common/useUncertaintyMode';
import { config } from './index';
import './U3606A.css';
import '../../../common/ComplianceBadge.css';

// Rotary dial positions (matching physical device)
const DIAL_POSITIONS = [
    { id: 'OFF', label: 'OFF', unit: '', angle: -135 },
    { id: 'DCV', label: 'V', type: 'dc', unit: 'V', angle: -105 },
    { id: 'ACV', label: 'V~', type: 'ac', unit: 'V', angle: -75 },
    { id: 'DCI', label: 'I', type: 'dc', unit: 'A', angle: -45 },
    { id: 'ACI', label: 'I~', type: 'ac', unit: 'A', angle: -15 },
    { id: 'OHM2', label: 'Ω 2W', unit: 'Ω', angle: 15 },
    { id: 'OHM4', label: 'Ω 4W', unit: 'Ω', angle: 45 },
    { id: 'FREQ', label: 'Hz', unit: 'Hz', angle: 75 },
    { id: 'CAP', label: 'CAP', unit: 'F', angle: 105 },
    { id: 'DIODE', label: '◄|', unit: 'V', angle: 135 },
];

function U3606A({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, connections, components, isComponentConnected, uncertaintyMode } = useSimulator();
    const state = component.state;
    const isConnected = isComponentConnected(component.id);
    const [dialIndex, setDialIndex] = useState(1); // Default to DCV

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // Power is controlled by dial position (OFF = power off)
    const isPowerOn = dialIndex !== 0;

    // Rotate dial
    const rotateDial = useCallback((direction) => {
        const newIndex = direction === 'cw'
            ? Math.min(dialIndex + 1, DIAL_POSITIONS.length - 1)
            : Math.max(dialIndex - 1, 0);
        setDialIndex(newIndex);
        const pos = DIAL_POSITIONS[newIndex];
        setState({
            power: newIndex !== 0,
            mode: pos.id,
            unit: pos.unit,
            value: 0
        });
    }, [dialIndex, setState]);

    // Get connected value from source device
    const getConnectedValue = useCallback(() => {
        const hiConn = connections.find(c => c.to === component.id && c.polarity === 'hi');
        const loConn = connections.find(c => c.to === component.id && c.polarity === 'lo');
        const auxHiConn = connections.find(c => c.to === component.id && c.polarity === 'aux_hi');
        const auxLoConn = connections.find(c => c.to === component.id && c.polarity === 'aux_lo');

        let sourceId = null;
        let isAuxConnection = false;

        if (hiConn && loConn && hiConn.from === loConn.from) {
            sourceId = hiConn.from;
        } else if (auxHiConn && auxLoConn && auxHiConn.from === auxLoConn.from) {
            sourceId = auxHiConn.from;
            isAuxConnection = true;
        } else {
            return null;
        }

        const source = components.find(c => c.id === sourceId);
        if (!source || !source.state.power) return null;

        if (source.type === 'fluke5500a' && source.state.output) {
            return {
                value: source.state.value,
                unit: isAuxConnection ? 'A' : source.state.unit,
                active: true
            };
        }
        if (source.type === 'sma100a' && source.state.rfOn) {
            return { value: source.state.level, unit: 'dBm', active: true };
        }
        return null;
    }, [connections, components, component.id]);

    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    const connectedValue = getConnectedValue();
    const baseValue = connectedValue?.active ? connectedValue.value : state.value;
    const currentPos = DIAL_POSITIONS[dialIndex];
    const displayUnit = connectedValue?.active ? connectedValue.unit : currentPos.unit;

    // Use uncertainty mode hook
    const tolerance = config.tolerance?.[currentPos.id] || 0.01;
    const { displayValue, uncertaintyMode: isUncertainty, complianceInfo } = useUncertaintyMode(
        baseValue,
        tolerance,
        state.complianceStatus,
        connectedValue?.active && isPowerOn
    );

    // Format 5.5 digit display
    const formatValue = (val) => {
        if (typeof val !== 'number') return '0.00000';
        if (Math.abs(val) >= 100000) return val.toExponential(4);
        return val.toFixed(5).slice(0, 7);
    };

    return (
        <div
            className={`placed-component u3606a-device ${!isPowerOn ? 'power-off' : ''} ${complianceInfo?.className || ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Compliance Badge */}
            <ComplianceBadge status={state.complianceStatus} visible={isUncertainty} />

            {/* Delete Button */}
            <button className="u3606a-delete" onClick={handleDelete}>×</button>

            {/* Connection Status */}
            <div className="u3606a-connection-status">
                <div className={`status-led ${isConnected ? 'connected' : ''}`}></div>
                <span>{isConnected ? 'LINK' : 'N/C'}</span>
            </div>

            {/* Top Header Bar */}
            <div className="u3606a-header">
                <div className="header-left">
                    <span className="brand-warning">⚠ Source</span>
                </div>
                <div className="header-center">
                    <span className="keysight-logo">KEYSIGHT</span>
                    <span className="model-name">U3606B</span>
                    <span className="model-desc">Multimeter | DC Power Supply</span>
                </div>
                <div className="header-right">
                    <span className="out-label">OUT</span>
                </div>
            </div>

            {/* Main Panel */}
            <div className="u3606a-main-panel">
                {/* LEFT SECTION - Multimeter */}
                <div className="u3606a-multimeter-section">
                    {/* Source Terminals (Top) */}
                    <div className="source-terminals">
                        <span className="source-label">⚠ Source</span>
                        <div className="source-jacks">
                            <div className="terminal-group force">
                                <span className="term-label">+ FORCE -</span>
                                <div className="jacks-row">
                                    <div className="jack green small">
                                        <ConnectionPoint type="input" componentId={component.id} polarity="force_hi"
                                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }} />
                                    </div>
                                    <div className="jack green small">
                                        <ConnectionPoint type="input" componentId={component.id} polarity="force_lo"
                                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }} />
                                    </div>
                                </div>
                            </div>
                            <div className="terminal-group sense">
                                <span className="term-label">+SNS-</span>
                                <div className="jacks-row">
                                    <div className="jack yellow small"></div>
                                    <div className="jack yellow small"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Rotary Dial Section */}
                    <div className="dial-section">
                        <div className="dial-labels-container">
                            {DIAL_POSITIONS.map((pos, idx) => (
                                <span
                                    key={pos.id}
                                    className={`dial-label ${idx === dialIndex ? 'active' : ''}`}
                                    style={{
                                        transform: `rotate(${pos.angle}deg) translateY(-48px) rotate(${-pos.angle}deg)`
                                    }}
                                >
                                    {pos.label}
                                </span>
                            ))}
                        </div>
                        <div
                            className="rotary-dial"
                            onClick={() => rotateDial('cw')}
                            onContextMenu={(e) => { e.preventDefault(); rotateDial('ccw'); }}
                        >
                            <div className="dial-center">
                                <div
                                    className="dial-pointer"
                                    style={{ transform: `rotate(${currentPos.angle}deg)` }}
                                ></div>
                            </div>
                        </div>
                    </div>

                    {/* Input Terminals (Bottom) */}
                    <div className="input-terminals">
                        <div className="terminal-row main-inputs">
                            <div className="terminal-item">
                                <div className="jack red large">
                                    <ConnectionPoint type="input" componentId={component.id} polarity="hi"
                                        style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }} />
                                </div>
                                <span className="jack-label">V Ω</span>
                            </div>
                            <div className="terminal-item">
                                <div className="jack black large">
                                    <ConnectionPoint type="input" componentId={component.id} polarity="lo"
                                        style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }} />
                                </div>
                                <span className="jack-label">LO</span>
                            </div>
                            <div className="terminal-item">
                                <div className="jack red large">
                                    <ConnectionPoint type="input" componentId={component.id} polarity="aux_hi"
                                        style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }} />
                                </div>
                                <span className="jack-label">3A MAX</span>
                            </div>
                            <div className="terminal-item">
                                <div className="jack black large">
                                    <ConnectionPoint type="input" componentId={component.id} polarity="aux_lo"
                                        style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }} />
                                </div>
                                <span className="jack-label">I</span>
                            </div>
                        </div>
                        <div className="multimeter-label">▲ Multimeter</div>
                    </div>
                </div>

                {/* CENTER - Displays */}
                <div className="u3606a-display-section">
                    {/* Main Display */}
                    <div className="main-display">
                        <div className="display-indicators">
                            <span className={state.autoRange ? 'ind active' : 'ind'}>AUTO</span>
                            <span className="ind">*</span>
                        </div>
                        <div className="display-value primary">
                            {isPowerOn ? formatValue(displayValue) : '------'}
                            <span className="unit">{isPowerOn ? displayUnit : ''}</span>
                        </div>
                    </div>

                    {/* Secondary Display (DC Supply) */}
                    <div className="secondary-display">
                        <div className="dc-readings">
                            <div className="dc-row">
                                <span className="dc-label">CV</span>
                                <span className="dc-value">{isPowerOn ? '00.000' : '-----'}</span>
                                <span className="dc-unit">V</span>
                            </div>
                            <div className="dc-row">
                                <span className="dc-label">CC</span>
                                <span className="dc-value">{isPowerOn ? '0.0000' : '-----'}</span>
                                <span className="dc-unit">A</span>
                            </div>
                        </div>
                        <div className="dc-controls-indicators">
                            <div className="range-box">
                                <span className="range-title">Range</span>
                                <div className="range-options">
                                    <span className="opt">31½V</span>
                                    <span className="opt active">Auto</span>
                                </div>
                            </div>
                            <div className="source-box">
                                <span className="src-label">S1</span>
                                <span className="src-val">30V 1A</span>
                                <span className="src-label">S2</span>
                                <span className="src-val">30V 3A</span>
                            </div>
                        </div>
                    </div>

                    {/* Button Rows */}
                    <div className="button-section">
                        {/* Row 1 - Main function buttons */}
                        <div className="btn-row">
                            <button className="fn-btn blue">Shift</button>
                            <button className="fn-btn">▽ V</button>
                            <button className="fn-btn">▽ I</button>
                            <button className="fn-btn">Save</button>
                            <button className="fn-btn">▲ V</button>
                            <button className="fn-btn">Limit</button>
                            <button className="fn-btn yellow">Auto Range</button>
                            <button className="fn-btn blue">Trigger</button>
                            <button className="fn-btn blue">(Menu)</button>
                            <button className="fn-btn">Local</button>
                        </div>
                        {/* Row 2 */}
                        <div className="btn-row">
                            <button className="fn-btn">Ω ◄|</button>
                            <button className="fn-btn">4½ 5½</button>
                            <button className="fn-btn">Recall</button>
                            <button className="fn-btn">Trig</button>
                            <button className="fn-btn">Min/Max</button>
                            <button className="fn-btn">Range</button>
                            <button className="fn-btn yellow">Voltage</button>
                            <button className="fn-btn yellow">Current</button>
                            <button className="fn-btn blue">Shift</button>
                            <button className="fn-btn power" onClick={() => rotateDial(isPowerOn ? 'ccw' : 'cw')}>
                                <span>Power</span>
                                <span className={`pwr-ind ${isPowerOn ? 'on' : ''}`}>{isPowerOn ? 'ON' : 'SBY'}</span>
                            </button>
                        </div>
                        {/* Row 3 */}
                        <div className="btn-row">
                            <button className="fn-btn">Hz mΩ</button>
                            <button className="fn-btn">◄ ►</button>
                            <button className="fn-btn">Hold</button>
                            <button className="fn-btn">Null</button>
                            <button className="fn-btn">∇ ch1 ◁</button>
                            <button className="fn-btn">Sweep Exit</button>
                            <button className="fn-btn yellow">Ramp Scan</button>
                            <button className="fn-btn yellow">⊙⊙⊙</button>
                            <button className="fn-btn blue">EXT</button>
                            <button className="fn-btn out-btn">OUT<br />SBY</button>
                        </div>
                    </div>
                </div>

                {/* RIGHT SECTION - DC Power Supply Terminals */}
                <div className="u3606a-supply-section">
                    <div className="supply-terminals">
                        <span className="supply-title">Source</span>
                        <div className="supply-jacks">
                            <div className="terminal-item">
                                <div className="jack red large binding">+</div>
                            </div>
                            <div className="terminal-item">
                                <div className="jack black large binding">−</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Label */}
            <div className="u3606a-footer">
                <span className="footer-label">▲ Stackable Direction ▲</span>
            </div>
        </div>
    );
}

export default U3606A;
