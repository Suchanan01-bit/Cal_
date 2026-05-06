/**
 * LightSource.jsx
 * Fiber Optic Light Source for Calibration
 * Used for testing and calibrating optical fiber equipment
 */

import { useCallback } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import ConnectionPoint from '../../../common/ConnectionPoint';
import './LightSource.css';

// Available wavelengths (nm)
const WAVELENGTHS = [850, 1310, 1490, 1550, 1625];

// Modulation modes
const MODULATION_MODES = ['CW', '270Hz', '1kHz', '2kHz'];

function LightSource({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, isComponentConnected } = useSimulator();
    const state = component.state || {};
    const isConnected = isComponentConnected(component.id);

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // Toggle power
    const togglePower = useCallback(() => {
        const newPower = !state.power;
        setState({ power: newPower, output: false });
    }, [state.power, setState]);

    // Toggle laser output
    const toggleOutput = useCallback(() => {
        if (state.power) {
            setState({ output: !state.output });
        }
    }, [state.power, state.output, setState]);

    // Set wavelength
    const handleWavelengthChange = useCallback((wavelength) => {
        if (!state.power) return;
        setState({ wavelength, output: false }); // Turn off output when changing wavelength
    }, [state.power, setState]);

    // Set modulation mode
    const handleModulationChange = useCallback((mode) => {
        if (!state.power) return;
        setState({ modulationMode: mode });
    }, [state.power, setState]);

    // Adjust output power
    const handlePowerAdjust = useCallback((direction) => {
        if (!state.power) return;
        const newPower = Math.max(-30, Math.min(0, (state.outputPower || -10) + direction));
        setState({ outputPower: newPower });
    }, [state.power, state.outputPower, setState]);

    // Toggle stabilized mode
    const toggleStabilized = useCallback(() => {
        if (!state.power) return;
        setState({ stabilized: !state.stabilized });
    }, [state.power, state.stabilized, setState]);

    // Delete device
    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    return (
        <div
            className={`placed-component lightsource-device ${!state.power ? 'power-off' : ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Header */}
            <div className="device-header">
                <div className="device-brand">
                    <span className="lightsource-logo">OPTICAL</span>
                    <span className="device-model">LS-2000</span>
                </div>
                <button className="delete-btn" onClick={handleDelete}>×</button>
            </div>

            <div className="device-body">
                {/* Main Display */}
                <div className="lightsource-display">
                    <div className="lightsource-lcd">
                        <div className="lightsource-lcd-inner">
                            {/* Wavelength Display */}
                            <div className="lightsource-wavelength-display">
                                <span className="display-label">λ</span>
                                <span className="display-value">{state.wavelength || 1310}</span>
                                <span className="display-unit">nm</span>
                            </div>

                            {/* Power Display */}
                            <div className="lightsource-power-display">
                                <span className="display-label">P</span>
                                <span className="display-value">{(state.outputPower || -10).toFixed(1)}</span>
                                <span className="display-unit">dBm</span>
                            </div>

                            {/* Status Indicators */}
                            <div className="lightsource-status-row">
                                <span className={`status-indicator ${state.output ? 'active laser' : ''}`}>
                                    {state.output ? 'LASER ON' : 'STANDBY'}
                                </span>
                                <span className={`status-indicator ${state.stabilized ? 'active' : ''}`}>
                                    {state.stabilized ? 'STAB' : ''}
                                </span>
                                <span className="modulation-indicator">
                                    {state.modulationMode || 'CW'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Control Panel */}
                <div className="lightsource-controls">
                    {/* Left: Optical Output */}
                    <div className="lightsource-output-section">
                        <div className="optical-connector">
                            <div className="connector-label">OPTICAL OUTPUT</div>
                            <div className="fc-connector">
                                <div className={`connector-body ${state.output ? 'laser-active' : ''}`}>
                                    <div className="connector-ferrule">
                                        <ConnectionPoint
                                            type="output"
                                            componentId={component.id}
                                            polarity="fiber"
                                            style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}
                                        />
                                    </div>
                                </div>
                            </div>
                            <div className="connector-type">FC/PC</div>
                        </div>

                        {/* Laser Warning */}
                        <div className={`laser-warning ${state.output ? 'active' : ''}`}>
                            <div className="warning-symbol">⚠</div>
                            <div className="warning-text">CLASS 1 LASER</div>
                        </div>
                    </div>

                    {/* Center: Wavelength Selection */}
                    <div className="lightsource-wavelength-section">
                        <div className="section-title">WAVELENGTH (nm)</div>
                        <div className="wavelength-buttons">
                            {WAVELENGTHS.map((wl) => (
                                <button
                                    key={wl}
                                    className={`wavelength-btn ${state.wavelength === wl ? 'selected' : ''}`}
                                    onClick={() => handleWavelengthChange(wl)}
                                    disabled={!state.power}
                                >
                                    {wl}
                                </button>
                            ))}
                        </div>

                        {/* Modulation Selection */}
                        <div className="section-title">MODULATION</div>
                        <div className="modulation-buttons">
                            {MODULATION_MODES.map((mode) => (
                                <button
                                    key={mode}
                                    className={`modulation-btn ${state.modulationMode === mode ? 'selected' : ''}`}
                                    onClick={() => handleModulationChange(mode)}
                                    disabled={!state.power}
                                >
                                    {mode}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Right: Power Control & Output */}
                    <div className="lightsource-power-section">
                        <div className="section-title">OUTPUT POWER</div>
                        <div className="power-adjust">
                            <button
                                className="adjust-btn"
                                onClick={() => handlePowerAdjust(-1)}
                                disabled={!state.power}
                            >
                                −
                            </button>
                            <div className="power-value">{(state.outputPower || -10).toFixed(1)} dBm</div>
                            <button
                                className="adjust-btn"
                                onClick={() => handlePowerAdjust(1)}
                                disabled={!state.power}
                            >
                                +
                            </button>
                        </div>

                        {/* Stabilized Mode */}
                        <button
                            className={`stab-btn ${state.stabilized ? 'active' : ''}`}
                            onClick={toggleStabilized}
                            disabled={!state.power}
                        >
                            STABILIZED
                        </button>

                        {/* Output Button */}
                        <button
                            className={`output-btn ${state.output ? 'active' : ''}`}
                            onClick={toggleOutput}
                            disabled={!state.power}
                        >
                            {state.output ? 'LASER ON' : 'LASER OFF'}
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

export default LightSource;
