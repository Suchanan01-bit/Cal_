/**
 * Canvas.jsx
 * Main canvas area for placing and connecting devices
 * With zoom (Ctrl+Scroll) and pan (Middle-mouse drag) support
 */

import { forwardRef, useCallback, useRef, useEffect, useState } from 'react';
import { useSimulator } from '../../context/SimulatorContext';
import { getDeviceComponent } from '../../registry/deviceRegistry';
import PlaceholderDevice from '../devices/PlaceholderDevice';
import WireConnection from '../common/WireConnection';
import ConnectionAlert from '../common/ConnectionAlert';
import './Canvas.css';

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 2.0;
const ZOOM_STEP = 0.1;

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
    const [zoom, setZoom] = useState(1);

    // Pan state
    const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
    const [isPanning, setIsPanning] = useState(false);
    const panStartRef = useRef({ x: 0, y: 0 });
    const panOffsetStartRef = useRef({ x: 0, y: 0 });

    // Force wire redraw on component position change, zoom, or pan change
    useEffect(() => {
        setWireUpdateTrigger(prev => prev + 1);
    }, [components, zoom, panOffset]);

    // Ctrl+Scroll zoom handler
    useEffect(() => {
        const container = canvasRef.current?.parentElement;
        if (!container) return;

        const handleWheel = (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                setZoom(prev => {
                    const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
                    const newZoom = Math.round((prev + delta) * 100) / 100;
                    return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom));
                });
            }
        };

        container.addEventListener('wheel', handleWheel, { passive: false });
        return () => container.removeEventListener('wheel', handleWheel);
    }, []);

    // Middle-mouse pan handler
    useEffect(() => {
        const container = canvasRef.current?.parentElement;
        if (!container) return;

        const handleMouseDown = (e) => {
            // Middle mouse button = button 1
            if (e.button === 1) {
                e.preventDefault();
                setIsPanning(true);
                panStartRef.current = { x: e.clientX, y: e.clientY };
                panOffsetStartRef.current = { ...panOffset };
                container.style.cursor = 'grabbing';
            }
        };

        const handleMouseMove = (e) => {
            if (!isPanning) return;
            const dx = e.clientX - panStartRef.current.x;
            const dy = e.clientY - panStartRef.current.y;
            setPanOffset({
                x: panOffsetStartRef.current.x + dx,
                y: panOffsetStartRef.current.y + dy,
            });
        };

        const handleMouseUp = (e) => {
            if (e.button === 1 && isPanning) {
                setIsPanning(false);
                container.style.cursor = '';
            }
        };

        // Prevent default middle-click scroll behavior
        const handleAuxClick = (e) => {
            if (e.button === 1) e.preventDefault();
        };

        container.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        container.addEventListener('auxclick', handleAuxClick);

        return () => {
            container.removeEventListener('mousedown', handleMouseDown);
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            container.removeEventListener('auxclick', handleAuxClick);
        };
    }, [isPanning, panOffset]);

    // Zoom controls
    const zoomIn = useCallback(() => {
        setZoom(prev => Math.min(MAX_ZOOM, Math.round((prev + ZOOM_STEP) * 100) / 100));
    }, []);
    const zoomOut = useCallback(() => {
        setZoom(prev => Math.max(MIN_ZOOM, Math.round((prev - ZOOM_STEP) * 100) / 100));
    }, []);
    const resetView = useCallback(() => {
        setZoom(1);
        setPanOffset({ x: 0, y: 0 });
    }, []);

    // Handle drop from sidebar (adjust for zoom + pan)
    const handleDrop = useCallback((e) => {
        e.preventDefault();
        const canvasRect = canvasRef.current.getBoundingClientRect();
        const type = e.dataTransfer.getData('deviceType');

        if (type) {
            const x = (e.clientX - canvasRect.left) / zoom - 100;
            const y = (e.clientY - canvasRect.top) / zoom - 50;
            addComponent(type, x, y);
            console.log(`➕ Created ${type}`);
        }
    }, [addComponent, zoom]);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        canvasRef.current.classList.add('drag-over');
    }, []);

    const handleDragLeave = useCallback(() => {
        canvasRef.current.classList.remove('drag-over');
    }, []);

    // Handle device dragging within canvas (adjust for zoom)
    const handleDeviceMouseDown = useCallback((e, component) => {
        if (e.target.closest('button, input, select, .connection-point')) {
            return;
        }
        // Only left mouse button for device drag
        if (e.button !== 0) return;
        e.preventDefault();

        const rect = e.currentTarget.getBoundingClientRect();
        setDragOffset({
            x: (e.clientX - rect.left),
            y: (e.clientY - rect.top)
        });
        setDraggingDevice(component);
    }, []);

    const handleMouseMove = useCallback((e) => {
        if (draggingDevice) {
            const canvasRect = canvasRef.current.getBoundingClientRect();
            const newX = (e.clientX - canvasRect.left) / zoom - dragOffset.x / zoom;
            const newY = (e.clientY - canvasRect.top) / zoom - dragOffset.y / zoom;

            updateComponentPosition(
                draggingDevice.id,
                newX,
                newY
            );
        }
    }, [draggingDevice, dragOffset, updateComponentPosition, zoom]);

    const handleMouseUp = useCallback(() => {
        setDraggingDevice(null);
    }, []);

    // Add global mouse event listeners for device dragging
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

    // Render device based on type
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

        const DeviceComponent = getDeviceComponent(component.type);
        return <DeviceComponent key={component.id} {...commonProps} />;
    };

    // Handle wire click
    const handleWireClick = useCallback((index) => {
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
                    x1: (fromRect.left + 7 - svgRect.left) / zoom,
                    y1: (fromRect.top + 7 - svgRect.top) / zoom,
                    x2: (toRect.left + 7 - svgRect.left) / zoom,
                    y2: (toRect.top + 7 - svgRect.top) / zoom,
                    active: isOutputActive(conn.from),
                    valid: true,
                    polarity: polarity,
                    wireType: conn.wireProperties?.type || 'standard',
                });
            }
        });

        return points;
    }, [connections, isOutputActive, wireUpdateTrigger, zoom]);

    const wirePoints = getConnectionPoints();
    const zoomPercent = Math.round(zoom * 100);
    const canvasTransform = `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`;

    return (
        <>
            {/* SVG for wires */}
            <svg ref={svgRef} className="wire-canvas" style={{
                transform: canvasTransform,
                transformOrigin: '0 0',
            }}>
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
                className={`canvas ${isPanning ? 'panning' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                style={{
                    transform: canvasTransform,
                    transformOrigin: '0 0',
                }}
            >
                {components.map(renderDevice)}
            </div>

            {/* Zoom & Pan Controls */}
            <div className="zoom-controls">
                <button className="zoom-btn" onClick={zoomOut} title="Zoom Out (Ctrl+Scroll Down)">−</button>
                <button className="zoom-percent" onClick={resetView} title="Reset View (Zoom & Pan)">
                    🔍 {zoomPercent}%
                </button>
                <button className="zoom-btn" onClick={zoomIn} title="Zoom In (Ctrl+Scroll Up)">+</button>
            </div>

            {/* Connection Alerts */}
            <ConnectionAlert alerts={alerts} onDismiss={dismissAlert} />
        </>
    );
});

Canvas.displayName = 'Canvas';

export default Canvas;
