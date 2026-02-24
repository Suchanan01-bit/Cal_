/**
 * ClampMeter.jsx
 * Fluke 376 True RMS Clamp Meter
 * With animated clamp jaw, iFlex, and wire measurement capability
 */

import { useCallback, useState, useEffect } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import ComplianceBadge from '../../../common/ComplianceBadge';
import { useUncertaintyMode } from '../../../common/useUncertaintyMode';
import { config } from './index';
import './ClampMeter.css';
import '../../../common/ComplianceBadge.css';

// Rotary dial positions matching Fluke 376
const DIAL_POSITIONS = [
    { id: 'OFF', label: 'OFF', type: null, unit: '', icon: '' },
    { id: 'AC_AMP', label: 'A AC', type: 'clamp', unit: 'A', icon: 'A~' },
    { id: 'DC_AMP', label: 'A DC', type: 'clamp', unit: 'A', icon: 'A⎓' },
    { id: 'ACDC_AMP', label: 'A AC+DC', type: 'clamp', unit: 'A', icon: 'A~⎓' },
    { id: 'IFLEX', label: 'iFlex', type: 'iflex', unit: 'A', icon: '⟲' },
    { id: 'AC_VOLT', label: 'V AC', type: 'probe', unit: 'V', icon: 'V~' },
    { id: 'DC_VOLT', label: 'V DC', type: 'probe', unit: 'V', icon: 'V⎓' },
    { id: 'MV_DC', label: 'mV DC', type: 'probe', unit: 'mV', icon: 'mV' },
    { id: 'OHM', label: 'Ω', type: 'probe', unit: 'Ω', icon: 'Ω' },
    { id: 'CONTINUITY', label: '))))', type: 'probe', unit: 'Ω', icon: ')))' },
    { id: 'DIODE', label: '◄|', type: 'probe', unit: 'V', icon: '◄|' },
    { id: 'HZ', label: 'Hz', type: 'probe', unit: 'Hz', icon: 'Hz' },
];

function ClampMeter({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, connections, components, isComponentConnected, uncertaintyMode } = useSimulator();
    const state = component.state;
    const isConnected = isComponentConnected(component.id);

    const [dialIndex, setDialIndex] = useState(1); // Default to AC Amp
    const [clampOpen, setClampOpen] = useState(false);
    const [iFlexConnected, setIFlexConnected] = useState(false);
    const [hold, setHold] = useState(false);
    const [minMax, setMinMax] = useState(false);
    const [inrush, setInrush] = useState(false);

    const currentPosition = DIAL_POSITIONS[dialIndex];
    const isPowerOn = currentPosition.type !== null;

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // Toggle clamp jaw open/close
    const toggleClamp = useCallback(() => {
        setClampOpen(prev => !prev);
        setState({ clampOpen: !clampOpen });
    }, [clampOpen, setState]);

    // Toggle iFlex connection
    const toggleIFlex = useCallback(() => {
        setIFlexConnected(prev => !prev);
        setState({ iFlexConnected: !iFlexConnected });
    }, [iFlexConnected, setState]);

    // Get value from connections (clamp measures current passing through)
    const getConnectedValue = useCallback(() => {
        // For clamp measurement - check if clamped around a wire
        if (currentPosition.type === 'clamp' || currentPosition.type === 'iflex') {
            // Find any connection that passes through the clamp
            const clampConn = connections.find(c => c.to === component.id && c.polarity === 'clamp');
            if (clampConn) {
                const source = components.find(c => c.id === clampConn.from);
                if (source && source.state.power && source.state.output) {
                    // Return current value
                    return {
                        value: source.state.value || 0,
                        unit: source.state.unit === 'A' ? 'A' : 'A',
                        active: true
                    };
                }
            }
        }

        // For probe measurements (V, Ohm, etc.)
        const hiConn = connections.find(c => c.to === component.id && c.polarity === 'hi');
        const loConn = connections.find(c => c.to === component.id && c.polarity === 'lo');

        if (hiConn && loConn && hiConn.from === loConn.from) {
            const source = components.find(c => c.id === hiConn.from);
            if (source && source.state.power) {
                if (source.type === 'fluke5500a' && source.state.output) {
                    return {
                        value: source.state.value,
                        unit: source.state.unit,
                        active: true
                    };
                }
            }
        }

        return null;
    }, [connections, components, component.id, currentPosition.type]);

    // Update display based on connected value
    useEffect(() => {
        if (!hold) {
            const connectedValue = getConnectedValue();
            if (connectedValue?.active && isPowerOn) {
                let displayValue = connectedValue.value;
                // Convert based on mode
                if (currentPosition.id === 'MV_DC') {
                    displayValue = connectedValue.value * 1000;
                }
                setState({ value: displayValue });
            } else {
                setState({ value: 0 });
            }
        }
    }, [getConnectedValue, isPowerOn, currentPosition, hold, setState]);

    // Rotate dial
    const rotateDial = useCallback((direction) => {
        const newIndex = direction === 'cw'
            ? Math.min(dialIndex + 1, DIAL_POSITIONS.length - 1)
            : Math.max(dialIndex - 1, 0);
        setDialIndex(newIndex);
        const pos = DIAL_POSITIONS[newIndex];
        setState({
            mode: pos.id,
            unit: pos.unit
        });
    }, [dialIndex, setState]);

    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    // Format display value
    const formatValue = (val) => {
        if (!isPowerOn) return '----';
        if (typeof val !== 'number') return '0.000';
        if (Math.abs(val) >= 1000) return val.toFixed(1);
        if (Math.abs(val) >= 100) return val.toFixed(2);
        if (Math.abs(val) >= 10) return val.toFixed(3);
        return val.toFixed(4);
    };

    const connectedValue = getConnectedValue();
    const baseValue = hold ? state.value : (connectedValue?.active ? connectedValue.value : 0);

    // Use uncertainty mode hook
    const tolerance = config.tolerance?.[currentPosition.id] || 0.02;
    const { displayValue, uncertaintyMode: isUncertainty, complianceInfo } = useUncertaintyMode(
        baseValue,
        tolerance,
        state.complianceStatus,
        connectedValue?.active && isPowerOn && !hold
    );

    // Calculate dial rotation
    const dialRotation = (dialIndex / (DIAL_POSITIONS.length - 1)) * 330 - 165;

    return (
        <div
            className={`placed-component clamp-meter-device ${!isPowerOn ? 'power-off' : ''} ${complianceInfo?.className || ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Compliance Badge */}
            <ComplianceBadge status={state.complianceStatus} visible={isUncertainty} />

            {/* Delete Button */}
            <button className="clamp-delete" onClick={handleDelete}>×</button>

            {/* Connection Status */}
            <div className="clamp-connection-status">
                <div className={`status-led ${isConnected ? 'connected' : ''}`}></div>
            </div>

            {/* Clamp Jaw - Pincer Style (ปากคีบ) */}
            <div className={`clamp-jaw-container ${clampOpen ? 'open' : 'closed'}`}>
                <div className="clamp-jaw-upper" onClick={toggleClamp}>
                    <div className="jaw-inner"></div>
                    <span className="jaw-label">1000A</span>
                </div>
                <div className="clamp-jaw-lower">
                    <div className="jaw-inner"></div>
                    <span className="jaw-label">CAT III</span>
                </div>
                <div className="clamp-opening">
                    {/* Connection point for clamping around wire */}
                    <ConnectionPoint
                        type="input"
                        componentId={component.id}
                        polarity="clamp"
                        style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                    />
                </div>
                <div className="clamp-trigger" onClick={toggleClamp} title={clampOpen ? 'Close Clamp' : 'Open Clamp'}>
                    <span>{clampOpen ? '▲' : '▼'}</span>
                </div>
            </div>

            {/* Main Body */}
            <div className="clamp-body">
                {/* Brand Header */}
                <div className="clamp-header">
                    <span className="brand-fluke">FLUKE</span>
                    <span className="model-number">376</span>
                    <span className="model-desc">TRUE RMS<br />CLAMP METER</span>
                </div>

                {/* Function Labels */}
                <div className="function-labels">
                    <div className="label-row">
                        <span className="func-label">Hz</span>
                        <span className="func-label">A~</span>
                        <span className="func-label">A</span>
                        <span className="func-label iflex">⟲ iFlex</span>
                    </div>
                    <div className="label-row">
                        <span className="func-label">◄| Ω</span>
                        <span className="func-label">))))</span>
                        <span className="func-label">A</span>
                    </div>
                    <div className="label-row">
                        <span className="func-label">mV V</span>
                        <span className="func-label">~V</span>
                    </div>
                    <div className="label-row">
                        <span className="func-label zero">ZERO</span>
                        <span className="func-label off">OFF</span>
                    </div>
                </div>

                {/* Rotary Dial */}
                <div className="dial-section">
                    <div
                        className="rotary-dial"
                        onClick={() => rotateDial('cw')}
                        onContextMenu={(e) => { e.preventDefault(); rotateDial('ccw'); }}
                        title="Click: CW | Right-click: CCW"
                    >
                        <div className="dial-body">
                            <div
                                className="dial-pointer"
                                style={{ transform: `rotate(${dialRotation}deg)` }}
                            ></div>
                        </div>
                    </div>
                    <span className="dial-current">{currentPosition.label}</span>
                </div>

                {/* LCD Display */}
                <div className="clamp-display">
                    <div className="display-indicators">
                        <span className={`indicator ${currentPosition.type === 'clamp' ? 'active' : ''}`}>Amps</span>
                        <span className={`indicator ${currentPosition.id.includes('AC') ? 'active' : ''}`}>AC</span>
                        <span className={`indicator ${currentPosition.id.includes('DC') ? 'active' : ''}`}>DC</span>
                        <span className={`indicator ${hold ? 'active' : ''}`}>HOLD</span>
                        <span className={`indicator ${iFlexConnected ? 'active' : ''}`}>iFlex</span>
                    </div>
                    <div className="display-main">
                        <span className="display-value">{formatValue(displayValue)}</span>
                        <span className="display-unit">{currentPosition.unit}</span>
                    </div>
                    <div className="display-range">
                        <span className={inrush ? 'active' : ''}>INRUSH</span>
                        <span className={minMax ? 'active' : ''}>MIN/MAX</span>
                    </div>
                </div>

                {/* Button Row */}
                <div className="clamp-buttons">
                    <button
                        className={`clamp-btn ${inrush ? 'active' : ''}`}
                        onClick={() => setInrush(!inrush)}
                    >
                        INRUSH
                    </button>
                    <button
                        className={`clamp-btn ${minMax ? 'active' : ''}`}
                        onClick={() => setMinMax(!minMax)}
                    >
                        MIN<br />MAX
                    </button>
                    <button
                        className={`clamp-btn ${hold ? 'active' : ''}`}
                        onClick={() => setHold(!hold)}
                    >
                        HOLD
                    </button>
                    <button
                        className="clamp-btn backlight"
                        title="Backlight"
                    >
                        ☀
                    </button>
                </div>

                {/* Terminal Panel */}
                <div className="clamp-terminals">
                    <div className="terminal-group">
                        <span className="terminal-cat">CAT III 1000V</span>
                        <span className="terminal-cat">CAT IV 600V</span>
                    </div>
                    <div className="terminal-row">
                        <div className="terminal-item">
                            <span className="terminal-label">COM</span>
                            <div className="banana-jack black">
                                <ConnectionPoint
                                    type="input"
                                    componentId={component.id}
                                    polarity="lo"
                                    style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                />
                            </div>
                        </div>
                        <div className="terminal-item">
                            <span className="terminal-label">⏚</span>
                            <div className="banana-jack gray">
                                <ConnectionPoint
                                    type="input"
                                    componentId={component.id}
                                    polarity="ground"
                                    style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                />
                            </div>
                        </div>
                        <div className="terminal-item">
                            <span className="terminal-label">VΩ</span>
                            <div className="banana-jack red">
                                <ConnectionPoint
                                    type="input"
                                    componentId={component.id}
                                    polarity="hi"
                                    style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* iFlex Connector */}
                <div className="iflex-connector" onClick={toggleIFlex}>
                    <div className={`iflex-port ${iFlexConnected ? 'connected' : ''}`}>
                        <span>iFlex</span>
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="iflex"
                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ClampMeter;
