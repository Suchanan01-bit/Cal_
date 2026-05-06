/**
 * Multimeter.jsx
 * Digital Multimeter Component with Uncertainty Mode support
 */

import { useCallback, useState, useEffect, useRef } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import { config } from './index';
import ConnectionPoint from '../../../common/ConnectionPoint';
import './Multimeter.css';

const MODES = ['DC V', 'AC V', 'DC A', 'AC A', 'Ω', 'F', 'Hz'];

// Compliance status display config
const COMPLIANCE_CONFIG = {
    compliance: { label: '✅ PASS', className: 'compliance' },
    non_compliance: { label: '⚠️ FAIL', className: 'non-compliance' },
    out_of_tolerance: { label: '❌ OOT', className: 'out-of-tolerance' }
};

function Multimeter({ component, onMouseDown, style }) {
    const { updateDeviceState, removeComponent, connections, components, isComponentConnected, uncertaintyMode, errorSimulation } = useSimulator();
    const state = component.state;
    const isConnected = isComponentConnected(component.id);
    const loadingError = errorSimulation?.loadingError;

    // State for fluctuating value display
    const [fluctuatingValue, setFluctuatingValue] = useState(null);
    const fluctuationIntervalRef = useRef(null);

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // Power toggle
    const togglePower = useCallback(() => {
        setState({ power: !state.power });
    }, [state.power, setState]);

    // Mode change
    const handleModeChange = useCallback((mode) => {
        if (!state.power) return;
        setState({ mode, value: 0 });
    }, [state.power, setState]);

    // Get connected value from source device - requires COMPLETE CIRCUIT (both HI and LO or AUX_HI and AUX_LO)
    const getConnectedValue = useCallback(() => {
        // Check NORMAL circuit first (HI + LO)
        const hiConn = connections.find(c => c.to === component.id && c.polarity === 'hi');
        const loConn = connections.find(c => c.to === component.id && c.polarity === 'lo');

        // Check AUX circuit (AUX_HI + AUX_LO) for current measurement
        const auxHiConn = connections.find(c => c.to === component.id && c.polarity === 'aux_hi');
        const auxLoConn = connections.find(c => c.to === component.id && c.polarity === 'aux_lo');

        let sourceId = null;
        let isAuxConnection = false;

        // Determine which circuit is complete
        if (hiConn && loConn && hiConn.from === loConn.from) {
            sourceId = hiConn.from;
        } else if (auxHiConn && auxLoConn && auxHiConn.from === auxLoConn.from) {
            sourceId = auxHiConn.from;
            isAuxConnection = true;
        } else {
            return null; // No complete circuit
        }

        // Find source component
        const source = components.find(c => c.id === sourceId);
        if (!source || !source.state.power) return null;

        // Get value based on source type - circuit is complete!
        // Support both Fluke 5500A and Fluke 5522A calibrators
        // Calculate total wire resistance
        let wireResistance = 0.0;
        if (loadingError) {
            const hiWire = isAuxConnection ? auxHiConn : hiConn;
            const loWire = isAuxConnection ? auxLoConn : loConn;

            // Default small resistance if undefined, or specific resistance from wire
            const rHi = hiWire?.wireProperties?.resistance || 0.05;
            const rLo = loWire?.wireProperties?.resistance || 0.05;
            wireResistance = rHi + rLo;
        }

        // Apply loading error physics
        let measuredValue = source.state.value;

        if (loadingError && source.state.output) {
            const mode = source.state.mode;

            // Voltage Loading Error (Input Impedance typically 10 MOhm)
            if (mode.includes('Voltage')) {
                const rMeter = 10000000; // 10 MOhm
                // V_measured = V_source * (R_meter / (R_meter + R_wire))
                measuredValue = measuredValue * (rMeter / (rMeter + wireResistance));
            }
            // Resistance Loading Error (2-wire measurement adds wire resistance)
            else if (mode === 'Resistance') {
                measuredValue = measuredValue + wireResistance;
            }
            // Current Loading Error (Burden Voltage / Noise)
            else if (mode.includes('Current')) {
                // Minimal impact normally, but adding slight degradation for "Bad" wires
                if (wireResistance > 1.0) {
                    measuredValue = measuredValue * 0.9995; // Slight loss
                }
            }
        }

        // Get active status (considering remote sense if implemented later, for now just output)
        if ((source.type === 'fluke5500a' || source.type === 'fluke5522a') && source.state.output) {
            // Map calibrator mode to multimeter mode
            const modeMapping = {
                'DC Voltage': 'DC V',
                'AC Voltage': 'AC V',
                'DC Current': 'DC A',
                'AC Current': 'AC A',
                'Resistance': 'Ω',
                'Capacitance': 'F',
                'Frequency': 'Hz',
                'Temperature': '°C'
            };

            return {
                value: measuredValue,
                unit: isAuxConnection ? 'A' : source.state.unit,
                mode: source.state.mode,
                mappedMode: modeMapping[source.state.mode] || 'DC V',
                frequency: source.state.frequency || 1000,
                active: true,
                wireResistance // Pass for debug/display if needed
            };
        }
        if (source.type === 'sma100a' && source.state.rfOn) {
            return {
                value: source.state.level,
                unit: 'dBm',
                active: true
            };
        }

        return null;
    }, [connections, components, component.id, loadingError]);

    // Delete component
    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    const connectedValue = getConnectedValue();

    // Determine base value - for Hz mode, use frequency from AC sources
    let baseValue;
    if (state.mode === 'Hz' && connectedValue?.active) {
        // In Hz mode, show frequency from AC sources
        if (connectedValue.mode === 'AC Voltage' || connectedValue.mode === 'AC Current') {
            baseValue = connectedValue.frequency;
        } else {
            baseValue = 0; // No frequency for DC sources
        }
    } else {
        baseValue = connectedValue?.active ? connectedValue.value : state.value;
    }

    const displayUnit = state.mode === 'Hz' ? 'Hz' :
        (connectedValue?.active ? connectedValue.unit :
            (state.mode === 'DC V' || state.mode === 'AC V' ? 'V' :
                state.mode === 'DC A' || state.mode === 'AC A' ? 'A' :
                    state.mode === 'Ω' ? 'Ω' : 'F'));

    // Get tolerance for current mode
    const getTolerance = useCallback(() => {
        // Start with selected mode
        let effectiveMode = state.mode;

        // If measuring from a valid source, use the source's signal type for tolerance lookup
        // This is critical for AUX connections (Amps) where the user might not have switched the dial
        if (connectedValue?.active && connectedValue.mappedMode) {
            effectiveMode = connectedValue.mappedMode;
        }

        const tolerance = config.tolerance?.[effectiveMode] || 0.01;
        // Adjust tolerance based on compliance status
        if (state.complianceStatus === 'out_of_tolerance') {
            return tolerance * 10; // Much larger fluctuation for OOT
        } else if (state.complianceStatus === 'non_compliance') {
            return tolerance * 3; // Larger fluctuation for non-compliance
        }
        return tolerance;
    }, [state.mode, state.complianceStatus, connectedValue]);

    // Uncertainty mode value fluctuation
    const isResolutionUncertaintyActive = errorSimulation?.resolutionUncertainty;
    const activeConnection = connectedValue?.active;

    // Use ref to store latest values for the interval closure without resetting the timer
    const simulationStateRef = useRef({ baseValue, getTolerance });

    // Update ref on every render
    useEffect(() => {
        simulationStateRef.current = { baseValue, getTolerance };
    }, [baseValue, getTolerance]);

    useEffect(() => {
        // Fluctuation should occur if "Resolution Uncertainty" is enabled OR "Global Uncertainty Mode" is enabled
        const shouldFluctuate = (uncertaintyMode || isResolutionUncertaintyActive) && activeConnection && state.power;

        if (shouldFluctuate) {
            // Start fluctuation with recursive timeout for variable interval
            const updateFluctuation = () => {
                const { baseValue: currentBase, getTolerance: currentGetTolerance } = simulationStateRef.current;

                const tolerance = currentGetTolerance();
                const maxVariation = Math.abs(currentBase) * (tolerance / 100);
                const randomOffset = (Math.random() - 0.5) * 2 * maxVariation;
                setFluctuatingValue(currentBase + randomOffset);

                // Schedule next update with random delay between 3000ms and 5000ms
                const nextDelay = 1000 + Math.random() * 1000;
                fluctuationIntervalRef.current = setTimeout(updateFluctuation, nextDelay);
            };

            // Initial update
            updateFluctuation();

            return () => {
                if (fluctuationIntervalRef.current) {
                    clearTimeout(fluctuationIntervalRef.current);
                }
            };
        } else {
            // Clear fluctuation when uncertainty mode is off
            setFluctuatingValue(null);
            if (fluctuationIntervalRef.current) {
                clearTimeout(fluctuationIntervalRef.current);
            }
        }
        // Dependencies: Only restart loop if activation state changes. 
        // Changing baseValue or Tolerance WON'T restart the loop (handled by ref)
    }, [uncertaintyMode, isResolutionUncertaintyActive, activeConnection, state.power]);

    // Determine display value - use fluctuating value if uncertainty mode (any type) is active
    const displayValue = ((uncertaintyMode || isResolutionUncertaintyActive) && fluctuatingValue !== null) ? fluctuatingValue : baseValue;

    // Get compliance status config
    const complianceInfo = state.complianceStatus ? COMPLIANCE_CONFIG[state.complianceStatus] : null;

    return (
        <div
            className={`placed-component multimeter-device ${!state.power ? 'power-off' : ''} ${complianceInfo?.className || ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Compliance Status Badge - Controlled by Global Uncertainty Mode */}
            {uncertaintyMode && complianceInfo && (
                <div className={`compliance-badge ${complianceInfo.className}`}>
                    {complianceInfo.label}
                </div>
            )}

            {/* Connection Status LED */}
            <div className="meter-connection-status">
                <div className={`meter-status-led ${isConnected ? 'connected' : 'disconnected'}`}></div>
                <span className={`meter-status-text ${isConnected ? 'connected' : 'disconnected'}`}>
                    {isConnected ? 'LINK' : 'N/C'}
                </span>
            </div>

            {/* Header */}
            <div className="meter-header">
                <span className="meter-title">Digital Multimeter</span>
                <button className="meter-delete" onClick={handleDelete}>×</button>
            </div>

            {/* Body */}
            <div className="meter-body">
                {/* Mode Selector */}
                <div className="meter-mode-selector">
                    {MODES.map((mode) => (
                        <button
                            key={mode}
                            className={`mode-btn ${state.mode === mode ? 'active' : ''}`}
                            onClick={() => handleModeChange(mode)}
                        >
                            {mode}
                        </button>
                    ))}
                </div>

                {/* Display */}
                <div className={`meter-display ${isResolutionUncertaintyActive ? 'uncertainty-active' : ''}`}>
                    <div className="meter-value">
                        {state.power
                            ? `${typeof displayValue === 'number' ? displayValue.toFixed(3) : '0.000'}`
                            : '----'}
                    </div>
                    <div className="meter-unit">{displayUnit}</div>
                    {isResolutionUncertaintyActive && connectedValue?.active && (
                        <div className="uncertainty-indicator">📊</div>
                    )}
                </div>

                {/* Power Button */}
                <button
                    className={`meter-power-btn ${state.power ? 'on' : ''}`}
                    onClick={togglePower}
                >
                    ⏻ {state.power ? 'ON' : 'OFF'}
                </button>
            </div>

            {/* Terminal Panel - Visual banana jacks */}
            <div className="meter-terminal-panel">
                <div className="meter-terminal-title">INPUT TERMINALS</div>
                <div className="meter-terminals">
                    <div className="meter-terminal hi">
                        <div className="terminal-jack red">
                            <div className="jack-inner"></div>
                        </div>
                        <span className="terminal-label">HI</span>
                        {/* HI (Red/Positive) Connection Point */}
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="hi"
                            style={{ left: '-5px', top: '50%', transform: 'translateY(-50%)' }}
                        />
                    </div>
                    <div className="meter-terminal lo">
                        <div className="terminal-jack black">
                            <div className="jack-inner"></div>
                        </div>
                        <span className="terminal-label">LO</span>
                        {/* LO (Black/Negative) Connection Point */}
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="lo"
                            style={{ left: '-5px', top: '50%', transform: 'translateY(-50%)' }}
                        />
                    </div>
                </div>

                {/* AUX Terminals for Current (Amps) */}
                <div className="meter-terminal-title aux">AUX (AMPS)</div>
                <div className="meter-terminals">
                    <div className="meter-terminal aux_hi">
                        <div className="terminal-jack orange">
                            <div className="jack-inner"></div>
                        </div>
                        <span className="terminal-label">A+</span>
                        {/* AUX HI for current input */}
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="aux_hi"
                            style={{ left: '-5px', top: '50%', transform: 'translateY(-50%)' }}
                        />
                    </div>
                    <div className="meter-terminal aux_lo">
                        <div className="terminal-jack blue">
                            <div className="jack-inner"></div>
                        </div>
                        <span className="terminal-label">A-</span>
                        {/* AUX LO for current input */}
                        <ConnectionPoint
                            type="input"
                            componentId={component.id}
                            polarity="aux_lo"
                            style={{ left: '-5px', top: '50%', transform: 'translateY(-50%)' }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Multimeter;
