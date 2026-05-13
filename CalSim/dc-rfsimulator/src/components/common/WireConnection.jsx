/**
 * WireConnection.jsx
 * Realistic wire connection component with Bezier curves
 * Supports polarity: 'hi' (red) and 'lo' (black) wire colors
 * Tooltip follows cursor while hovering anywhere on wire
 */

import { useMemo, useState, useCallback, useRef } from 'react';
import './WireConnection.css';

function WireConnection({ x1, y1, x2, y2, isActive, isValid, polarity = 'hi', onClick, wireType, instrumentName, flowStatus }) {
    const [isHovered, setIsHovered] = useState(false);
    const tooltipRef = useRef(null);

    // Convert mouse event to SVG coordinates and update tooltip position directly (no state re-render needed)
    const updateTooltipPosition = useCallback((e) => {
        const svg = e.target.closest('svg');
        if (svg && tooltipRef.current) {
            const pt = svg.createSVGPoint();
            pt.x = e.clientX;
            pt.y = e.clientY;
            const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());
            tooltipRef.current.setAttribute('x', svgP.x + 18);
            tooltipRef.current.setAttribute('y', svgP.y - 70);
        }
    }, []);

    const handleMouseEnter = useCallback((e) => {
        setIsHovered(true);
        // Pre-position on enter so it shows at cursor immediately
        setTimeout(() => updateTooltipPosition(e), 0);
    }, [updateTooltipPosition]);

    const handleMouseLeave = useCallback(() => {
        setIsHovered(false);
    }, []);

    const handleMouseMove = useCallback((e) => {
        updateTooltipPosition(e);
    }, [updateTooltipPosition]);

    // Calculate catenary/sagging wire path using Bezier curves
    const pathData = useMemo(() => {
        const dx = x2 - x1;
        const dy = y2 - y1;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Calculate sag amount based on distance
        const sagAmount = Math.min(distance * 0.3, 80);

        // Control points for realistic cable droop
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2 + sagAmount;

        // First control point (from start)
        const cp1x = x1 + dx * 0.25;
        const cp1y = y1 + sagAmount * 0.8;

        // Second control point (to end)
        const cp2x = x1 + dx * 0.75;
        const cp2y = y2 + sagAmount * 0.8;

        return `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${x2} ${y2}`;
    }, [x1, y1, x2, y2]);

    // Wire plug positions
    const plugStartPath = useMemo(() => {
        return `M ${x1 - 4} ${y1 - 4} L ${x1 + 4} ${y1 - 4} L ${x1 + 4} ${y1 + 4} L ${x1 - 4} ${y1 + 4} Z`;
    }, [x1, y1]);

    const plugEndPath = useMemo(() => {
        return `M ${x2 - 4} ${y2 - 4} L ${x2 + 4} ${y2 - 4} L ${x2 + 4} ${y2 + 4} L ${x2 - 4} ${y2 + 4} Z`;
    }, [x2, y2]);

    const wireClass = `realistic-wire ${isActive ? 'active' : ''} ${isValid ? 'valid' : 'invalid'} ${polarity} ${wireType === 'bad' ? 'bad-wire' : ''}`;

    return (
        <g 
            className={`wire-connection-group ${polarity} ${isHovered ? 'hovered' : ''}`} 
            onClick={onClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            onMouseMove={handleMouseMove}
        >
            {/* Invisible wide hit-area for easier hovering */}
            <path
                d={pathData}
                className="wire-hit-area"
            />

            {/* Shadow effect */}
            <path
                d={pathData}
                className={`wire-shadow ${polarity}`}
            />

            {/* Main wire outer (darker) */}
            <path
                d={pathData}
                className={`wire-outer ${wireClass}`}
            />

            {/* Main wire inner (lighter) */}
            <path
                d={pathData}
                className={`wire-inner ${wireClass}`}
            />

            {/* Highlight for 3D effect */}
            <path
                d={pathData}
                className="wire-highlight"
            />

            {/* Energy flow animation */}
            {isActive && isValid && (
                <path
                    d={pathData}
                    className={`wire-flow-animation ${polarity}`}
                />
            )}

            {/* Connection plugs */}
            <circle cx={x1} cy={y1} r="6" className={`wire-plug start ${wireClass}`} />
            <circle cx={x2} cy={y2} r="6" className={`wire-plug end ${wireClass}`} />

            {/* Plug metal ring effect */}
            <circle cx={x1} cy={y1} r="4" className="plug-ring" />
            <circle cx={x2} cy={y2} r="4" className="plug-ring" />

            {/* Tooltip - follows cursor via ref, no re-render on move */}
            {isHovered && (
                <foreignObject
                    ref={tooltipRef}
                    x={0}
                    y={0}
                    width="260"
                    height="90"
                    style={{ pointerEvents: 'none', overflow: 'visible' }}
                >
                    <div className="wire-tooltip">
                        <div className="tooltip-header">
                            <span className={`tooltip-indicator ${isActive ? 'active' : 'inactive'}`}></span>
                            <span className="tooltip-title">{instrumentName || 'Unknown'}</span>
                        </div>
                        <div className="tooltip-row">
                            <span className="tooltip-label">สถานะ:</span>
                            <span className={`tooltip-value ${isActive ? 'active' : ''}`}>
                                {isActive ? flowStatus : 'No Output (Off)'}
                            </span>
                        </div>
                        <div className="tooltip-row">
                            <span className="tooltip-label">สาย:</span>
                            <span className="tooltip-value">{polarity === 'hi' ? 'HI (+)' : 'LO (−)'} • {wireType === 'bad' ? '⚠ Bad Wire' : 'Standard'}</span>
                        </div>
                    </div>
                </foreignObject>
            )}
        </g>
    );
}

export default WireConnection;

