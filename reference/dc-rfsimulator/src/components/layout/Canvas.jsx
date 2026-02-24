/**
 * Canvas.jsx
 * Main canvas area for placing and connecting devices
 */

import { forwardRef, useCallback, useRef, useEffect, useState } from 'react';
import { useSimulator } from '../../context/SimulatorContext';
import { getDeviceComponent } from '../../registry/deviceRegistry';
import PlaceholderDevice from '../devices/PlaceholderDevice';
import WireConnection from '../common/WireConnection';
import ConnectionAlert from '../common/ConnectionAlert';
import './Canvas.css';

const Canvas = forwardRef((props, ref) => {
    const {
        components,
        connections,
        addComponent,
        updateComponentPosition,
        isOutputActive,
        connectionStartPoint,
        clearConnectionStart,
        removeConnection,
        alerts,
        dismissAlert,
        errorSimulation,
        toggleConnectionWireType,
    } = useSimulator();

    const canvasRef = useRef(null);
    const svgRef = useRef(null);
    const [draggingDevice, setDraggingDevice] = useState(null);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const [wireUpdateTrigger, setWireUpdateTrigger] = useState(0);

    // Force wire redraw on component position change
    useEffect(() => {
        setWireUpdateTrigger(prev => prev + 1);
    }, [components]);

    // Handle drop from sidebar
    const handleDrop = useCallback((e) => {
        e.preventDefault();
        const canvasRect = canvasRef.current.getBoundingClientRect();
        const type = e.dataTransfer.getData('deviceType');

        if (type) {
            const x = e.clientX - canvasRect.left - 100;
            const y = e.clientY - canvasRect.top - 50;
            addComponent(type, Math.max(0, x), Math.max(0, y));
            console.log(`➕ Created ${type}`);
        }
    }, [addComponent]);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        canvasRef.current.classList.add('drag-over');
    }, []);

    const handleDragLeave = useCallback(() => {
        canvasRef.current.classList.remove('drag-over');
    }, []);

    // Handle device dragging within canvas
    const handleDeviceMouseDown = useCallback((e, component) => {
        if (e.target.closest('button, input, select, .connection-point')) {
            return;
        }
        e.preventDefault();

        const rect = e.currentTarget.getBoundingClientRect();
        setDragOffset({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        });
        setDraggingDevice(component);
    }, []);

    const handleMouseMove = useCallback((e) => {
        if (draggingDevice) {
            const canvasRect = canvasRef.current.getBoundingClientRect();
            const newX = e.clientX - canvasRect.left - dragOffset.x;
            const newY = e.clientY - canvasRect.top - dragOffset.y;

            updateComponentPosition(
                draggingDevice.id,
                Math.max(0, newX),
                Math.max(0, newY)
            );
        }
    }, [draggingDevice, dragOffset, updateComponentPosition]);

    const handleMouseUp = useCallback(() => {
        setDraggingDevice(null);
    }, []);

    // Add global mouse event listeners
    useEffect(() => {
        if (draggingDevice) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            return () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
            };
        }
    }, [draggingDevice, handleMouseMove, handleMouseUp]);

    // Handle Escape to cancel connection
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && connectionStartPoint) {
                clearConnectionStart();
                console.log('❌ Connection cancelled');
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [connectionStartPoint, clearConnectionStart]);

    // Render device based on type - uses registry for dynamic component lookup
    const renderDevice = (component) => {
        const commonProps = {
            component,
            onMouseDown: (e) => handleDeviceMouseDown(e, component),
            style: {
                left: component.x,
                top: component.y,
                cursor: draggingDevice?.id === component.id ? 'grabbing' : 'grab',
                zIndex: draggingDevice?.id === component.id ? 100 : 1,
            }
        };

        // Get component from registry dynamically
        const DeviceComponent = getDeviceComponent(component.type);
        return <DeviceComponent key={component.id} {...commonProps} />;
    };

    // Handle wire click to remove connection
    // Handle wire click to remove connection OR toggle wire type
    const handleWireClick = useCallback((index) => {
        // If Loading Error simulation is ON, click toggles wire type instead of deleting
        if (errorSimulation?.loadingError) {
            toggleConnectionWireType(index);
            return;
        }

        if (window.confirm('ต้องการลบการเชื่อมต่อนี้หรือไม่?')) {
            removeConnection(index);
            console.log('🔌 Connection removed');
        }
    }, [removeConnection, errorSimulation, toggleConnectionWireType]);

    // Get connection points for drawing wires
    const getConnectionPoints = useCallback(() => {
        const points = [];

        connections.forEach((conn, index) => {
            const polarity = conn.polarity || 'hi';
            const fromEl = document.querySelector(`[data-component-id="${conn.from}"] .connection-point.output.${polarity}`);
            const toEl = document.querySelector(`[data-component-id="${conn.to}"] .connection-point.input.${polarity}`);

            if (fromEl && toEl && svgRef.current) {
                const svgRect = svgRef.current.getBoundingClientRect();
                const fromRect = fromEl.getBoundingClientRect();
                const toRect = toEl.getBoundingClientRect();

                points.push({
                    index,
                    x1: fromRect.left + 7 - svgRect.left,
                    y1: fromRect.top + 7 - svgRect.top,
                    x2: toRect.left + 7 - svgRect.left,
                    y2: toRect.top + 7 - svgRect.top,
                    active: isOutputActive(conn.from),
                    valid: true, // Connection was validated on creation
                    polarity: polarity,
                    wireType: conn.wireProperties?.type || 'standard',
                });
            }
        });

        return points;
    }, [connections, isOutputActive, wireUpdateTrigger]);

    const wirePoints = getConnectionPoints();

    return (
        <>
            {/* SVG for wires */}
            <svg ref={svgRef} className="wire-canvas">
                {wirePoints.map((wire) => (
                    <WireConnection
                        key={`${wire.index}-${wire.polarity}`}
                        x1={wire.x1}
                        y1={wire.y1}
                        x2={wire.x2}
                        y2={wire.y2}
                        isActive={wire.active}
                        isValid={wire.valid}
                        polarity={wire.polarity}
                        wireType={wire.wireType}
                        onClick={() => handleWireClick(wire.index)}
                    />
                ))}
            </svg>

            {/* Canvas area */}
            <div
                ref={canvasRef}
                className="canvas"
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
            >
                {components.map(renderDevice)}
            </div>

            {/* Connection Alerts */}
            <ConnectionAlert alerts={alerts} onDismiss={dismissAlert} />
        </>
    );
});

Canvas.displayName = 'Canvas';

export default Canvas;
