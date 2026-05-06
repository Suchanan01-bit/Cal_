/**
 * AnalogMultimeter.jsx
 * Simpson 260 Analog VOM (Volt-Ohm-Milliammeter)
 * Full realistic functionality with animated needle
 */

import { useCallback, useState, useEffect, useMemo } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import ComplianceBadge from '../../../common/ComplianceBadge';
import { useUncertaintyMode } from '../../../common/useUncertaintyMode';
import { config } from './index';
import './AnalogMultimeter.css';
import '../../../common/ComplianceBadge.css';

// Simpson 260 Range/Function positions (matching rotary knob)
const KNOB_POSITIONS = [
    // OFF position
    { id: 'OFF', label: 'OFF', type: null, range: 0, unit: '', scaleMax: 0 },

    // DC Voltage ranges
    { id: 'DC_250mV', label: '250mV', type: 'DCV', range: 0.25, unit: 'V', scaleMax: 250 },
    { id: 'DC_1V', label: '1V', type: 'DCV', range: 1, unit: 'V', scaleMax: 10 },
    { id: 'DC_2.5V', label: '2.5V', type: 'DCV', range: 2.5, unit: 'V', scaleMax: 250 },
    { id: 'DC_10V', label: '10V', type: 'DCV', range: 10, unit: 'V', scaleMax: 10 },
    { id: 'DC_50V', label: '50V', type: 'DCV', range: 50, unit: 'V', scaleMax: 50 },
    { id: 'DC_250V', label: '250V', type: 'DCV', range: 250, unit: 'V', scaleMax: 250 },
    { id: 'DC_500V', label: '500V', type: 'DCV', range: 500, unit: 'V', scaleMax: 50 },
    { id: 'DC_1000V', label: '1000V', type: 'DCV', range: 1000, unit: 'V', scaleMax: 10 },

    // AC Voltage ranges
    { id: 'AC_2.5V', label: 'AC 2.5V', type: 'ACV', range: 2.5, unit: 'V', scaleMax: 250 },
    { id: 'AC_10V', label: 'AC 10V', type: 'ACV', range: 10, unit: 'V', scaleMax: 10 },
    { id: 'AC_50V', label: 'AC 50V', type: 'ACV', range: 50, unit: 'V', scaleMax: 50 },
    { id: 'AC_250V', label: 'AC 250V', type: 'ACV', range: 250, unit: 'V', scaleMax: 250 },
    { id: 'AC_500V', label: 'AC 500V', type: 'ACV', range: 500, unit: 'V', scaleMax: 50 },
    { id: 'AC_1000V', label: 'AC 1000V', type: 'ACV', range: 1000, unit: 'V', scaleMax: 10 },

    // DC Current ranges
    { id: 'DC_50uA', label: '50μA', type: 'DCA', range: 0.00005, unit: 'μA', scaleMax: 50 },
    { id: 'DC_1mA', label: '1mA', type: 'DCA', range: 0.001, unit: 'mA', scaleMax: 10 },
    { id: 'DC_10mA', label: '10mA', type: 'DCA', range: 0.01, unit: 'mA', scaleMax: 10 },
    { id: 'DC_100mA', label: '100mA', type: 'DCA', range: 0.1, unit: 'mA', scaleMax: 10 },
    { id: 'DC_500mA', label: '500mA', type: 'DCA', range: 0.5, unit: 'mA', scaleMax: 50 },
    { id: 'DC_10A', label: '10A', type: 'DCA', range: 10, unit: 'A', scaleMax: 10 },

    // Resistance ranges
    { id: 'Rx1', label: 'Rx1', type: 'OHM', range: 1, unit: 'Ω', scaleMax: 2000 },
    { id: 'Rx10', label: 'Rx10', type: 'OHM', range: 10, unit: 'Ω', scaleMax: 20000 },
    { id: 'Rx100', label: 'Rx100', type: 'OHM', range: 100, unit: 'Ω', scaleMax: 200000 },
    { id: 'Rx1K', label: 'Rx1K', type: 'OHM', range: 1000, unit: 'Ω', scaleMax: 2000000 },
    { id: 'Rx10K', label: 'Rx10K', type: 'OHM', range: 10000, unit: 'Ω', scaleMax: 20000000 },
];

function AnalogMultimeter({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, connections, components, isComponentConnected, uncertaintyMode } = useSimulator();
    const state = component.state;
    const isConnected = isComponentConnected(component.id);

    const [knobIndex, setKnobIndex] = useState(4); // Default to 10V DC
    const [zeroOffset, setZeroOffset] = useState(0); // Zero adjust offset
    const [needleAngle, setNeedleAngle] = useState(-45);

    const currentPosition = KNOB_POSITIONS[knobIndex];
    const isPowerOn = currentPosition.type !== null;

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // Get connected value from source device
    const getConnectedValue = useCallback(() => {
        const hiConn = connections.find(c => c.to === component.id && c.polarity === 'hi');
        const loConn = connections.find(c => c.to === component.id && c.polarity === 'lo');

        if (!hiConn || !loConn || hiConn.from !== loConn.from) {
            return null;
        }

        const source = components.find(c => c.id === hiConn.from);
        if (!source || !source.state.power) return null;

        if (source.type === 'fluke5500a' && source.state.output) {
            return {
                value: source.state.value,
                unit: source.state.unit,
                mode: source.state.mode,
                active: true
            };
        }
        return null;
    }, [connections, components, component.id]);

    // Calculate needle deflection (0-90 degrees from left to right)
    const calculateNeedleAngle = useCallback((value, position) => {
        if (!position || position.type === null) return -45;

        const range = position.range;
        let percentage = 0;

        if (position.type === 'OHM') {
            // Ohm scale is logarithmic/non-linear, reversed (0 on right, ∞ on left)
            if (value === 0) return 45; // Infinite resistance = full right
            const logValue = Math.log10(value / range);
            percentage = Math.max(0, Math.min(100, 100 - (logValue * 30)));
        } else {
            // Linear scale for V and A
            percentage = Math.min((Math.abs(value) / range) * 100, 100);
        }

        // Convert percentage to angle (-45 to +45 degrees)
        return -45 + (percentage * 0.9) + zeroOffset;
    }, [zeroOffset]);

    // Update needle based on connected value
    useEffect(() => {
        const connectedValue = getConnectedValue();
        if (connectedValue?.active && isPowerOn) {
            const angle = calculateNeedleAngle(connectedValue.value, currentPosition);
            setNeedleAngle(angle);
            setState({ value: connectedValue.value, needlePosition: angle });
        } else {
            setNeedleAngle(-45 + zeroOffset);
            setState({ value: 0, needlePosition: -45 + zeroOffset });
        }
    }, [getConnectedValue, calculateNeedleAngle, currentPosition, isPowerOn, zeroOffset, setState]);

    // Rotate main function knob
    const rotateKnob = useCallback((direction) => {
        const newIndex = direction === 'cw'
            ? Math.min(knobIndex + 1, KNOB_POSITIONS.length - 1)
            : Math.max(knobIndex - 1, 0);
        setKnobIndex(newIndex);
        const pos = KNOB_POSITIONS[newIndex];
        setState({
            mode: pos.type || 'OFF',
            range: pos.label,
            unit: pos.unit
        });
    }, [knobIndex, setState]);

    // Adjust zero
    const adjustZero = useCallback((direction) => {
        const newOffset = direction === 'cw'
            ? Math.min(zeroOffset + 1, 10)
            : Math.max(zeroOffset - 1, -10);
        setZeroOffset(newOffset);
    }, [zeroOffset]);

    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    const connectedValue = getConnectedValue();
    const baseValue = connectedValue?.active ? connectedValue.value : 0;

    // Use uncertainty mode hook
    const tolerance = config.tolerance?.[currentPosition.type] || 0.5;
    const { displayValue, uncertaintyMode: isUncertainty, complianceInfo } = useUncertaintyMode(
        baseValue,
        tolerance,
        state.complianceStatus,
        connectedValue?.active && isPowerOn
    );

    // Calculate knob rotation angle
    const knobRotation = useMemo(() => {
        return (knobIndex / (KNOB_POSITIONS.length - 1)) * 300 - 150;
    }, [knobIndex]);

    return (
        <div
            className={`placed-component simpson260-device ${complianceInfo?.className || ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Compliance Badge */}
            <ComplianceBadge status={state.complianceStatus} visible={isUncertainty} />

            {/* Delete Button */}
            <button className="simpson-delete" onClick={handleDelete}>×</button>

            {/* Connection Status */}
            <div className="simpson-connection-status">
                <div className={`status-led ${isConnected ? 'connected' : ''}`}></div>
            </div>

            {/* Meter Face */}
            <div className="simpson-meter-face">
                {/* Scale Markings - Multiple arcs */}
                <svg className="meter-scales" viewBox="0 0 240 140">
                    {/* OHMS scale (top, red) - reversed */}
                    <path d="M 20 120 A 100 100 0 0 1 220 120" fill="none" stroke="#8B0000" strokeWidth="1" />
                    <text x="30" y="90" className="scale-label ohms">∞</text>
                    <text x="60" y="60" className="scale-label ohms">100</text>
                    <text x="100" y="45" className="scale-label ohms">20</text>
                    <text x="140" y="45" className="scale-label ohms">5</text>
                    <text x="180" y="60" className="scale-label ohms">1</text>
                    <text x="205" y="90" className="scale-label ohms">0</text>

                    {/* DC/AC Voltage scale (middle, black) */}
                    <path d="M 30 115 A 90 90 0 0 1 210 115" fill="none" stroke="#000" strokeWidth="1.5" />
                    <text x="35" y="100" className="scale-label dc">0</text>
                    <text x="70" y="70" className="scale-label dc">2</text>
                    <text x="100" y="55" className="scale-label dc">4</text>
                    <text x="120" y="50" className="scale-label dc">5</text>
                    <text x="145" y="55" className="scale-label dc">6</text>
                    <text x="175" y="70" className="scale-label dc">8</text>
                    <text x="200" y="100" className="scale-label dc">10</text>

                    {/* Additional scale markings */}
                    <text x="35" y="115" className="scale-label small">0</text>
                    <text x="120" y="62" className="scale-label small">50</text>
                    <text x="200" y="115" className="scale-label small">250</text>

                    {/* Tick marks */}
                    {[...Array(51)].map((_, i) => {
                        const angle = -45 + (i * 1.8);
                        const rad = (angle * Math.PI) / 180;
                        const r1 = 85;
                        const r2 = i % 10 === 0 ? 70 : (i % 5 === 0 ? 75 : 80);
                        const x1 = 120 + r1 * Math.sin(rad);
                        const y1 = 120 - r1 * Math.cos(rad);
                        const x2 = 120 + r2 * Math.sin(rad);
                        const y2 = 120 - r2 * Math.cos(rad);
                        return (
                            <line
                                key={i}
                                x1={x1} y1={y1} x2={x2} y2={y2}
                                stroke="#333"
                                strokeWidth={i % 10 === 0 ? 2 : 1}
                            />
                        );
                    })}

                    {/* OHMS label */}
                    <text x="120" y="30" className="scale-title ohms">OHMS</text>
                    {/* DC label */}
                    <text x="50" y="125" className="scale-title dc">DC</text>
                    {/* AC label */}
                    <text x="180" y="125" className="scale-title ac">AC</text>
                </svg>

                {/* Animated Needle */}
                <div
                    className="meter-needle"
                    style={{ transform: `rotate(${needleAngle}deg)` }}
                >
                    <div className="needle-body"></div>
                </div>
                <div className="needle-pivot"></div>

                {/* Simpson Logo */}
                <div className="simpson-logo">Simpson</div>
            </div>

            {/* Control Panel */}
            <div className="simpson-control-panel">
                {/* Current reading display */}
                <div className="reading-display">
                    <span className="reading-mode">{currentPosition.label}</span>
                    <span className="reading-value">
                        {isPowerOn ? displayValue.toFixed(4) : '---'} {currentPosition.unit}
                    </span>
                </div>

                {/* Main Rotary Selector Knob */}
                <div className="main-knob-section">
                    <div className="knob-labels">
                        {/* Position labels around the knob */}
                        {KNOB_POSITIONS.filter((_, i) => i % 3 === 0).map((pos, idx) => (
                            <span
                                key={pos.id}
                                className={`knob-label ${knobIndex === idx * 3 ? 'active' : ''}`}
                                style={{
                                    transform: `rotate(${(idx / 8) * 300 - 150}deg) translateY(-70px) rotate(${-((idx / 8) * 300 - 150)}deg)`
                                }}
                            >
                                {pos.label}
                            </span>
                        ))}
                    </div>
                    <div
                        className="main-rotary-knob"
                        onClick={() => rotateKnob('cw')}
                        onContextMenu={(e) => { e.preventDefault(); rotateKnob('ccw'); }}
                        title="Click: CW | Right-click: CCW"
                    >
                        <div className="knob-body">
                            <div
                                className="knob-pointer"
                                style={{ transform: `rotate(${knobRotation}deg)` }}
                            ></div>
                        </div>
                    </div>
                    <span className="knob-hint">Function/Range</span>
                </div>

                {/* Zero Adjust Knob */}
                <div className="zero-adjust-section">
                    <span className="zero-label">ZERO<br />OHMS</span>
                    <div
                        className="zero-knob"
                        onClick={() => adjustZero('cw')}
                        onContextMenu={(e) => { e.preventDefault(); adjustZero('ccw'); }}
                    >
                        <div className="zero-knob-inner">
                            <div
                                className="zero-pointer"
                                style={{ transform: `rotate(${zeroOffset * 18}deg)` }}
                            ></div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Terminal Panel - Matching Simpson 260 layout */}
            <div className="simpson-terminal-panel">
                {/* COMMON (-) Terminal */}
                <div className="terminal-group">
                    <span className="terminal-title">COMMON</span>
                    <div className="banana-jack black large">
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="lo"
                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                        />
                    </div>
                    <span className="terminal-subtitle">−</span>
                </div>

                {/* +DC / -AC Terminal */}
                <div className="terminal-group">
                    <span className="terminal-title">+DC</span>
                    <div className="banana-jack red large">
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="hi"
                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                        />
                    </div>
                    <span className="terminal-subtitle">−AC</span>
                </div>

                {/* OUTPUT Terminal */}
                <div className="terminal-group">
                    <span className="terminal-title">OUTPUT</span>
                    <div className="banana-jack red medium">
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="output"
                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                        />
                    </div>
                    <span className="terminal-subtitle">250V AC</span>
                </div>

                {/* 10A Terminal */}
                <div className="terminal-group">
                    <span className="terminal-title">10A</span>
                    <div className="banana-jack red medium">
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="10a"
                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                        />
                    </div>
                    <span className="terminal-subtitle">D.C.</span>
                </div>

                {/* 1000V DC Terminal */}
                <div className="terminal-group">
                    <span className="terminal-title">1000V</span>
                    <div className="banana-jack red medium">
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="1000v"
                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                        />
                    </div>
                    <span className="terminal-subtitle">D.C.</span>
                </div>
            </div>

            {/* Model Badge */}
            <div className="model-badge">260</div>
        </div>
    );
}

export default AnalogMultimeter;
