/**
 * Oscilloscope.jsx
 * Digital Storage Oscilloscope
 * For measuring and displaying electrical signals
 */

import { useCallback, useEffect, useRef } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import ComplianceBadge from '../../../common/ComplianceBadge';
import './Oscilloscope.css';
import '../../../common/ComplianceBadge.css';

// Time base options (ms/div)
const TIMEBASE_OPTIONS = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100];

// Volts/div options
const VOLTS_DIV_OPTIONS = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50];

// Trigger modes
const TRIGGER_MODES = ['AUTO', 'NORMAL', 'SINGLE'];

function Oscilloscope({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, isComponentConnected, getConnectedSignal, uncertaintyMode } = useSimulator();
    const state = component.state || {};
    const isConnected = isComponentConnected(component.id);
    const canvasRef = useRef(null);

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // Get connected signal for display
    const signal = getConnectedSignal ? getConnectedSignal(component.id) : null;

    // Draw waveform on canvas
    useEffect(() => {
        if (!state.power || !canvasRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // Clear canvas
        ctx.fillStyle = '#001100';
        ctx.fillRect(0, 0, width, height);

        // Draw grid
        ctx.strokeStyle = '#003300';
        ctx.lineWidth = 1;

        // Vertical lines (10 divisions)
        for (let i = 0; i <= 10; i++) {
            ctx.beginPath();
            ctx.moveTo(i * (width / 10), 0);
            ctx.lineTo(i * (width / 10), height);
            ctx.stroke();
        }

        // Horizontal lines (8 divisions)
        for (let i = 0; i <= 8; i++) {
            ctx.beginPath();
            ctx.moveTo(0, i * (height / 8));
            ctx.lineTo(width, i * (height / 8));
            ctx.stroke();
        }

        // Draw center lines (brighter)
        ctx.strokeStyle = '#005500';
        ctx.beginPath();
        ctx.moveTo(width / 2, 0);
        ctx.lineTo(width / 2, height);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();

        // Draw waveform if running and signal available
        if (state.running && signal) {
            const frequency = signal.frequency || 1000;
            const amplitude = signal.value || 1;
            const vDiv = state.voltsDiv1 || 1;
            const tDiv = state.timebase || 1;

            // Calculate pixels per division
            const pxPerVDiv = height / 8;
            const pxPerTDiv = width / 10;

            // Scale amplitude to pixels
            const amplitudePx = (amplitude / vDiv) * pxPerVDiv;

            // Draw CH1 waveform (yellow/green)
            if (state.channel1) {
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 2;
                ctx.beginPath();

                for (let x = 0; x < width; x++) {
                    // Time in ms
                    const t = (x / pxPerTDiv) * tDiv;
                    // Calculate y based on frequency
                    const omega = 2 * Math.PI * frequency / 1000; // rad/ms
                    const y = height / 2 - amplitudePx * Math.sin(omega * t);

                    if (x === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
                ctx.stroke();
            }

            // Update measurements
            if (signal) {
                setState({
                    measuredFrequency: frequency,
                    measuredVpp: amplitude * 2,
                    measuredVrms: amplitude * 0.707
                });
            }
        } else if (state.running) {
            // No signal - draw flat line
            if (state.channel1) {
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(0, height / 2);
                ctx.lineTo(width, height / 2);
                ctx.stroke();
            }
        }

    }, [state.power, state.running, state.channel1, state.timebase, state.voltsDiv1, signal, setState]);

    // Toggle power
    const togglePower = useCallback(() => {
        setState({ power: !state.power });
    }, [state.power, setState]);

    // Toggle channel
    const toggleChannel = useCallback((channel) => {
        if (!state.power) return;
        setState({ [channel]: !state[channel] });
    }, [state, setState]);

    // Adjust timebase
    const adjustTimebase = useCallback((direction) => {
        if (!state.power) return;
        const currentIndex = TIMEBASE_OPTIONS.indexOf(state.timebase);
        const newIndex = Math.max(0, Math.min(TIMEBASE_OPTIONS.length - 1, currentIndex + direction));
        setState({ timebase: TIMEBASE_OPTIONS[newIndex] });
    }, [state.power, state.timebase, setState]);

    // Adjust volts/div
    const adjustVoltsDiv = useCallback((channel, direction) => {
        if (!state.power) return;
        const key = `voltsDiv${channel}`;
        const currentIndex = VOLTS_DIV_OPTIONS.indexOf(state[key]);
        const newIndex = Math.max(0, Math.min(VOLTS_DIV_OPTIONS.length - 1, currentIndex + direction));
        setState({ [key]: VOLTS_DIV_OPTIONS[newIndex] });
    }, [state, setState]);

    // Set trigger mode
    const setTriggerMode = useCallback((mode) => {
        if (!state.power) return;
        setState({ triggerMode: mode });
    }, [state.power, setState]);

    // Toggle run/stop
    const toggleRunStop = useCallback(() => {
        if (!state.power) return;
        setState({ running: !state.running });
    }, [state.power, state.running, setState]);

    // Delete device
    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    // Format display values
    const formatTimebase = (val) => {
        if (val >= 1) return `${val} ms`;
        if (val >= 0.001) return `${val * 1000} μs`;
        return `${val * 1000000} ns`;
    };

    const formatVolts = (val) => {
        if (val >= 1) return `${val} V`;
        return `${val * 1000} mV`;
    };

    // Get compliance info
    const complianceInfo = state.complianceStatus ? {
        compliance: { className: 'compliance' },
        non_compliance: { className: 'non-compliance' },
        out_of_tolerance: { className: 'out-of-tolerance' }
    }[state.complianceStatus] : null;

    return (
        <div
            className={`placed-component oscilloscope-device ${!state.power ? 'power-off' : ''} ${complianceInfo?.className || ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Compliance Badge */}
            <ComplianceBadge status={state.complianceStatus} visible={uncertaintyMode} />

            {/* Header */}
            <div className="device-header">
                <div className="device-brand">
                    <span className="osc-logo">DSO</span>
                    <span className="device-model">DS-2100</span>
                </div>
                <button className="delete-btn" onClick={handleDelete}>×</button>
            </div>

            <div className="device-body">
                {/* Display Screen */}
                <div className="osc-display">
                    <canvas
                        ref={canvasRef}
                        width={300}
                        height={200}
                        className="osc-screen"
                    />

                    {/* On-screen info */}
                    <div className="osc-overlay">
                        <div className="osc-info-top">
                            <span className={`ch-indicator ${state.channel1 ? 'active' : ''}`}>CH1</span>
                            <span className="timebase-info">{formatTimebase(state.timebase || 1)}/div</span>
                            <span className={`run-indicator ${state.running ? 'running' : 'stopped'}`}>
                                {state.running ? 'RUN' : 'STOP'}
                            </span>
                        </div>
                        <div className="osc-info-bottom">
                            <span className="ch1-scale">{formatVolts(state.voltsDiv1 || 1)}/div</span>
                            <span className="trigger-info">Trig: {state.triggerMode}</span>
                        </div>
                    </div>
                </div>

                {/* Measurements Display */}
                <div className="osc-measurements">
                    <div className="measurement">
                        <span className="meas-label">Freq:</span>
                        <span className="meas-value">{(state.measuredFrequency || 0).toFixed(0)} Hz</span>
                    </div>
                    <div className="measurement">
                        <span className="meas-label">Vpp:</span>
                        <span className="meas-value">{(state.measuredVpp || 0).toFixed(3)} V</span>
                    </div>
                    <div className="measurement">
                        <span className="meas-label">Vrms:</span>
                        <span className="meas-value">{(state.measuredVrms || 0).toFixed(3)} V</span>
                    </div>
                </div>

                {/* Control Panel */}
                <div className="osc-controls">
                    {/* Left: Input Connectors */}
                    <div className="osc-input-section">
                        <div className="bnc-connector">
                            <div className="connector-label">CH1</div>
                            <div className="bnc-body">
                                <div className="bnc-center">
                                    <ConnectionPoint
                                        type="input"
                                        componentId={component.id}
                                        polarity="ch1"
                                        style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                    />
                                </div>
                            </div>
                        </div>
                        <div className="bnc-connector">
                            <div className="connector-label">CH2</div>
                            <div className="bnc-body">
                                <div className="bnc-center">
                                    <ConnectionPoint
                                        type="input"
                                        componentId={component.id}
                                        polarity="ch2"
                                        style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Center: Vertical & Horizontal Controls */}
                    <div className="osc-main-controls">
                        {/* Channel 1 Controls */}
                        <div className="control-group">
                            <div className="group-label">CH1</div>
                            <button
                                className={`ch-btn ${state.channel1 ? 'active' : ''}`}
                                onClick={() => toggleChannel('channel1')}
                                disabled={!state.power}
                            >
                                {state.channel1 ? 'ON' : 'OFF'}
                            </button>
                            <div className="adjust-controls">
                                <button onClick={() => adjustVoltsDiv(1, -1)} disabled={!state.power}>−</button>
                                <span>{formatVolts(state.voltsDiv1 || 1)}</span>
                                <button onClick={() => adjustVoltsDiv(1, 1)} disabled={!state.power}>+</button>
                            </div>
                        </div>

                        {/* Timebase Controls */}
                        <div className="control-group">
                            <div className="group-label">TIME/DIV</div>
                            <div className="adjust-controls horizontal">
                                <button onClick={() => adjustTimebase(-1)} disabled={!state.power}>◀</button>
                                <span>{formatTimebase(state.timebase || 1)}</span>
                                <button onClick={() => adjustTimebase(1)} disabled={!state.power}>▶</button>
                            </div>
                        </div>

                        {/* Trigger Controls */}
                        <div className="control-group">
                            <div className="group-label">TRIGGER</div>
                            <div className="trigger-buttons">
                                {TRIGGER_MODES.map(mode => (
                                    <button
                                        key={mode}
                                        className={`trig-btn ${state.triggerMode === mode ? 'active' : ''}`}
                                        onClick={() => setTriggerMode(mode)}
                                        disabled={!state.power}
                                    >
                                        {mode}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Right: Run/Stop & Power */}
                    <div className="osc-power-section">
                        <button
                            className={`run-stop-btn ${state.running ? 'running' : ''}`}
                            onClick={toggleRunStop}
                            disabled={!state.power}
                        >
                            {state.running ? 'STOP' : 'RUN'}
                        </button>

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

export default Oscilloscope;
