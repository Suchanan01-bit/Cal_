/**
 * Fluke117.jsx
 * Fluke 117 True RMS Digital Multimeter
 * Redesigned: real rotary knob with radial mode labels around it
 */

import { useCallback, useState, useEffect, useRef } from 'react';
import { useSimulator } from '../../../../context/SimulatorContext';
import { config } from './index';
import ConnectionPoint from '../../../common/ConnectionPoint';
import './Fluke117.css';

/**
 * Dial positions arranged clockwise, matching the real Fluke 117.
 * angle = degrees from 12 o'clock (top), clockwise positive.
 * The label appears on the dial ring at that angle.
 * The knob marker rotates to = angle - 135  (offset so OFF is at top-left).
 */
const DIAL_POSITIONS = [
    { key: 'OFF', label: 'OFF', unit: '', angle: -135 },  // top-left
    { key: '~V', label: 'LoZ', unit: 'V', angle: -90 },  // top
    { key: 'AC V', label: 'ACV', unit: 'V', angle: -45 },  // top-right
    { key: 'DC V', label: 'DCV', unit: 'V', angle: 0 },  // right
    { key: 'DC mA', label: 'mADC', unit: 'mA', angle: 45 },  // bottom-right
    { key: 'AC mA', label: 'mAAC', unit: 'mA', angle: 90 },  // bottom
    { key: 'Diode', label: '⫠', unit: 'V', angle: 135 },  // bottom-left
    { key: 'Ω', label: 'Ω', unit: 'Ω', angle: 180 },  // left-bottom
    { key: 'Hz', label: 'Hz', unit: 'Hz', angle: -180 },  // left
];

const COMPLIANCE_CONFIG = {
    compliance: { label: '✅ PASS', className: 'compliance' },
    non_compliance: { label: '⚠️ FAIL', className: 'non-compliance' },
    out_of_tolerance: { label: '❌ OOT', className: 'out-of-tolerance' },
};

const MODE_MAPPING = {
    'DC Voltage': 'DC V',
    'AC Voltage': 'AC V',
    'DC Current': 'DC mA',
    'AC Current': 'AC mA',
    'Resistance': 'Ω',
    'Frequency': 'Hz',
};

// Radius (px) of the label ring around the knob
const RING_R = 72;
const KNOB_R = 44; // half of knob width=88

function Fluke117({ component, onMouseDown, style }) {
    const {
        updateDeviceState,
        removeComponent,
        connections,
        components,
        isComponentConnected,
        uncertaintyMode,
        errorSimulation,
    } = useSimulator();

    const state = component.state;
    const isConnected = isComponentConnected(component.id);
    const loadingError = errorSimulation?.loadingError;

    const [fluctuatingValue, setFluctuatingValue] = useState(null);
    const fluctuationRef = useRef(null);

    const setState = useCallback((newState) => {
        updateDeviceState(component.id, newState);
    }, [component.id, updateDeviceState]);

    // ── Find current dial index ──
    const dialIdx = Math.max(0, DIAL_POSITIONS.findIndex(p => p.key === state.mode));

    // ── Rotate one step CW / CCW ──
    const rotateDial = useCallback((dir) => {
        const next = (dialIdx + dir + DIAL_POSITIONS.length) % DIAL_POSITIONS.length;
        const pos = DIAL_POSITIONS[next];
        setState({
            mode: pos.key,
            power: pos.key !== 'OFF',
            value: 0,
            unit: pos.unit,
        });
    }, [dialIdx, setState]);

    // ── Click a label on the ring ──
    const handleLabelClick = useCallback((posKey, e) => {
        e.stopPropagation();
        const pos = DIAL_POSITIONS.find(p => p.key === posKey);
        if (!pos) return;
        setState({
            mode: pos.key,
            power: pos.key !== 'OFF',
            value: 0,
            unit: pos.unit,
        });
    }, [setState]);

    // ── Top 4 buttons ──
    const toggleHold = useCallback(() => { if (state.power) setState({ hold: !state.hold }); }, [state.power, state.hold, setState]);
    const toggleRange = useCallback(() => { if (state.power) setState({ autoRange: !(state.autoRange !== false) }); }, [state.power, state.autoRange, setState]);
    const toggleMinMax = useCallback(() => { if (state.power) setState({ minMax: !state.minMax }); }, [state.power, state.minMax, setState]);
    const toggleRel = useCallback(() => { if (state.power) setState({ relMode: !state.relMode }); }, [state.power, state.relMode, setState]);

    const handleDelete = useCallback(() => removeComponent(component.id), [component.id, removeComponent]);

    // ── Read connected calibrator value ──
    const getConnectedValue = useCallback(() => {
        const hiConn = connections.find(c => c.to === component.id && c.polarity === 'hi');
        const loConn = connections.find(c => c.to === component.id && c.polarity === 'lo');
        const auxHiConn = connections.find(c => c.to === component.id && c.polarity === 'aux_hi');
        const auxLoConn = connections.find(c => c.to === component.id && c.polarity === 'aux_lo');

        let sourceId = null, isAux = false;

        if (hiConn && loConn && hiConn.from === loConn.from) {
            sourceId = hiConn.from;
        } else if (auxHiConn && auxLoConn && auxHiConn.from === auxLoConn.from) {
            sourceId = auxHiConn.from; isAux = true;
        } else return null;

        const source = components.find(c => c.id === sourceId);
        if (!source || !source.state.power) return null;

        let wireResistance = 0;
        if (loadingError) {
            const hiW = isAux ? auxHiConn : hiConn;
            const loW = isAux ? auxLoConn : loConn;
            wireResistance = (hiW?.wireProperties?.resistance || 0.05) +
                (loW?.wireProperties?.resistance || 0.05);
        }

        let measuredValue = source.state.value;
        if (loadingError && source.state.output) {
            const mode = source.state.mode;
            if (mode?.includes('Voltage')) {
                measuredValue *= (10_000_000 / (10_000_000 + wireResistance));
            } else if (mode === 'Resistance') {
                measuredValue += wireResistance;
            }
        }

        if ((source.type === 'fluke5500a' || source.type === 'fluke5522a') && source.state.output) {
            return {
                value: measuredValue,
                unit: isAux ? 'mA' : source.state.unit,
                mode: source.state.mode,
                mappedMode: MODE_MAPPING[source.state.mode] || 'DC V',
                frequency: source.state.frequency || 1000,
                active: true,
            };
        }
        return null;
    }, [connections, components, component.id, loadingError]);

    const connectedValue = getConnectedValue();

    // ── Display value ──
    let baseValue =
        state.mode === 'Hz' && connectedValue?.active
            ? (['AC Voltage', 'AC Current'].includes(connectedValue.mode) ? connectedValue.frequency : 0)
            : (connectedValue?.active ? connectedValue.value : state.value);

    const currentPos = DIAL_POSITIONS.find(p => p.key === state.mode);
    const displayUnit =
        state.mode === 'Hz' ? 'Hz' :
            (connectedValue?.active ? connectedValue.unit : (currentPos?.unit || 'V'));

    const getTolerance = useCallback(() => {
        let effectiveMode = state.mode;
        if (connectedValue?.active && connectedValue.mappedMode) effectiveMode = connectedValue.mappedMode;
        const tol = config.tolerance?.[effectiveMode] || 0.5;
        if (state.complianceStatus === 'out_of_tolerance') return tol * 10;
        if (state.complianceStatus === 'non_compliance') return tol * 3;
        return tol;
    }, [state.mode, state.complianceStatus, connectedValue]);

    const isResolutionUncertaintyActive = errorSimulation?.resolutionUncertainty;
    const activeConnection = connectedValue?.active;

    const simStateRef = useRef({ baseValue, getTolerance });
    useEffect(() => { simStateRef.current = { baseValue, getTolerance }; }, [baseValue, getTolerance]);

    useEffect(() => {
        const shouldFluctuate = (uncertaintyMode || isResolutionUncertaintyActive) && activeConnection && state.power;
        if (shouldFluctuate) {
            const tick = () => {
                const { baseValue: bv, getTolerance: gt } = simStateRef.current;
                const tol = gt();
                const maxVar = Math.abs(bv) * (tol / 100);
                const offset = (Math.random() - 0.5) * 2 * maxVar;
                setFluctuatingValue(bv + offset);
                fluctuationRef.current = setTimeout(tick, 1000 + Math.random() * 1000);
            };
            tick();
            return () => { if (fluctuationRef.current) clearTimeout(fluctuationRef.current); };
        } else {
            setFluctuatingValue(null);
            if (fluctuationRef.current) clearTimeout(fluctuationRef.current);
        }
    }, [uncertaintyMode, isResolutionUncertaintyActive, activeConnection, state.power]);

    const displayValue =
        ((uncertaintyMode || isResolutionUncertaintyActive) && fluctuatingValue !== null)
            ? fluctuatingValue : baseValue;

    const formatValue = (v) => {
        if (!state.power) return '----';
        if (typeof v !== 'number') return '0.000';
        if (state.mode === 'Hz') return v.toFixed(2);
        if (state.mode === 'Diode') return v.toFixed(3);
        return v.toFixed(3);
    };

    const complianceInfo = state.complianceStatus ? COMPLIANCE_CONFIG[state.complianceStatus] : null;

    // Knob rotation: marker points in direction of current mode
    const knobAngle = DIAL_POSITIONS[dialIdx].angle;

    // Build radial label positions
    // Center of knob ring = 0,0 offset. We use CSS absolute positioning inside .f117-dial-ring
    const labelNodes = DIAL_POSITIONS.map((pos) => {
        const rad = (pos.angle - 90) * (Math.PI / 180); // -90 so 0deg = top
        const x = RING_R * Math.cos(rad); // relative to center
        const y = RING_R * Math.sin(rad);
        return { ...pos, x, y };
    });

    return (
        <div
            className={`placed-component fluke117-device ${!state.power ? 'power-off' : ''} ${complianceInfo?.className || ''}`}
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            {/* Compliance Badge */}
            {uncertaintyMode && complianceInfo && (
                <div className={`f117-compliance-badge ${complianceInfo.className}`}>{complianceInfo.label}</div>
            )}

            {/* ── HEADER ── */}
            <div className="f117-header">
                <div className="f117-brand">
                    <span className="f117-brand-name">fluke</span>
                    <span className="f117-model-sub">117 · TRUE RMS MULTIMETER</span>
                </div>
                <div className="f117-header-right">
                    <div className="f117-connection-status">
                        <div className={`f117-status-led ${isConnected ? 'connected' : 'disconnected'}`} />
                        <span className={`f117-status-text ${isConnected ? 'connected' : 'disconnected'}`}>
                            {isConnected ? 'LINK' : 'N/C'}
                        </span>
                    </div>
                    <button className="f117-delete" onClick={handleDelete}>×</button>
                </div>
            </div>

            {/* ── 4 TOP BUTTONS ── */}
            <div className="f117-top-buttons">
                <button className={`f117-top-btn ${state.hold ? 'active' : ''}`} onClick={toggleHold} disabled={!state.power}>
                    HOLD
                </button>
                <button className={`f117-top-btn ${state.minMax ? 'active' : ''}`} onClick={toggleMinMax} disabled={!state.power}>
                    MIN MAX
                </button>
                <button className={`f117-top-btn range-btn ${state.autoRange !== false ? 'active' : ''}`} onClick={toggleRange} disabled={!state.power}>
                    RANGE
                </button>
                <button className={`f117-top-btn ${state.relMode ? 'active' : ''}`} onClick={toggleRel} disabled={!state.power}>
                    REL
                </button>
            </div>

            {/* ── LCD DISPLAY ── */}
            <div className={`f117-display ${isResolutionUncertaintyActive ? 'uncertainty-active' : ''}`}>
                <div className="f117-display-top">
                    <div className="f117-display-flags">
                        <span className={`f117-flag ${state.mode === '~V' ? 'flag-on' : ''}`}>LoZ</span>
                        <span className="f117-flag volt-alert">VoltAlert</span>
                        {state.hold && <span className="f117-flag flag-hold">HOLD</span>}
                        {state.minMax && <span className="f117-flag flag-minmax">MAX</span>}
                        {state.relMode && <span className="f117-flag flag-rel">REL</span>}
                    </div>
                    <span className="f117-display-mode">{state.mode !== 'OFF' ? state.mode : ''}</span>
                </div>
                <div className={`f117-main-value ${!state.power ? 'power-off' : ''}`}>
                    {formatValue(displayValue)}
                </div>
                <div className="f117-unit-row">
                    <span className="f117-sub-left">{state.power ? (state.autoRange !== false ? 'AUTO' : 'MANUAL') : ''}</span>
                    <span className="f117-unit">{state.power ? displayUnit : ''}</span>
                </div>
            </div>

            {/* ── DIAL AREA: rotary knob + radial labels ── */}
            <div className="f117-dial-area">

                {/* Radial label ring + knob — positioned relative to a square container */}
                <div className="f117-dial-ring-wrap">

                    {/* Radial mode labels */}
                    {labelNodes.map((pos) => (
                        <button
                            key={pos.key}
                            className={`f117-ring-label ${state.mode === pos.key ? 'ring-active' : ''}`}
                            style={{
                                left: `calc(50% + ${pos.x}px)`,
                                top: `calc(50% + ${pos.y}px)`,
                                transform: 'translate(-50%, -50%)',
                            }}
                            onClick={(e) => handleLabelClick(pos.key, e)}
                            title={pos.key}
                        >
                            {pos.label}
                        </button>
                    ))}

                    {/* Knob */}
                    <div
                        className="f117-knob"
                        style={{ transform: `translate(-50%, -50%) rotate(${knobAngle}deg)` }}
                    >
                        {/* Outer ring */}
                        <div className="f117-knob-outer" />
                        {/* Inner disc */}
                        <div className="f117-knob-inner">
                            {/* Pointer */}
                            <div className="f117-knob-ptr" />
                        </div>
                        {/* Grip serrations - decorative */}
                        <div className="f117-knob-serrations" />
                    </div>

                    {/* CCW / CW arrow buttons */}
                    <button
                        className="f117-arrow-btn ccw"
                        onClick={() => rotateDial(-1)}
                        title="Rotate counter-clockwise"
                    >‹</button>
                    <button
                        className="f117-arrow-btn cw"
                        onClick={() => rotateDial(1)}
                        title="Rotate clockwise"
                    >›</button>
                </div>

                {/* AUTO-V / LoZ label */}
                <div className="f117-dial-footer">
                    <span className="f117-autov-text">AUTO-V / LoZ</span>
                    <span className="f117-catrating">CAT III 600V</span>
                </div>
            </div>

            {/* ── TERMINAL PANEL ── */}
            <div className="f117-terminal-panel">
                <div className="f117-terminals">
                    <div className="f117-terminal mA">
                        <div className="f117-jack yellow"><div className="f117-jack-inner" /></div>
                        <span className="f117-terminal-label">mA</span>
                        <ConnectionPoint type="input" componentId={component.id} polarity="aux_hi"
                            style={{ left: '-5px', top: '50%', transform: 'translateY(-50%)' }} />
                    </div>
                    <div className="f117-terminal lo">
                        <div className="f117-jack black"><div className="f117-jack-inner" /></div>
                        <span className="f117-terminal-label">COM</span>
                        <ConnectionPoint type="input" componentId={component.id} polarity="lo"
                            style={{ left: '-5px', top: '50%', transform: 'translateY(-50%)' }} />
                    </div>
                    <div className="f117-terminal hi">
                        <div className="f117-jack red"><div className="f117-jack-inner" /></div>
                        <span className="f117-terminal-label">V·Ω</span>
                        <ConnectionPoint type="input" componentId={component.id} polarity="hi"
                            style={{ left: '-5px', top: '50%', transform: 'translateY(-50%)' }} />
                    </div>
                </div>
                <div className="f117-safety-row">
                    <span>10A FUSED</span>
                    <span>600V CAT III 300V CAT IV</span>
                </div>
            </div>
        </div>
    );
}

export default Fluke117;
