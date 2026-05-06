/**
 * ConnectionPoint.jsx
 * Connection point for wire connections between devices
 * Supports polarity: 'hi' (red/positive) and 'lo' (black/negative)
 */

import { useCallback } from 'react';
import { useSimulator } from '../../context/SimulatorContext';

function ConnectionPoint({ type, componentId, polarity = 'hi', style }) {
    const {
        connectionStartPoint,
        setConnectionStart,
        clearConnectionStart,
        addConnection
    } = useSimulator();

    const handleClick = useCallback((e) => {
        e.stopPropagation();

        // If clicking on output and no connection started
        if (type === 'output' && !connectionStartPoint) {
            setConnectionStart({ componentId, type, polarity });
            console.log(`🔴 Started ${polarity.toUpperCase()} connection from Component ID:`, componentId);
        }
        // If clicking on input and connection is in progress
        else if (type === 'input' && connectionStartPoint) {
            // Check polarity match
            if (connectionStartPoint.polarity !== polarity) {
                console.warn(`⚠️ Polarity mismatch! Connect ${connectionStartPoint.polarity.toUpperCase()} to ${connectionStartPoint.polarity.toUpperCase()}`);
                clearConnectionStart();
                return;
            }
            if (connectionStartPoint.componentId !== componentId) {
                addConnection(connectionStartPoint.componentId, componentId, polarity);
                console.log(`🟢 Connected ${polarity.toUpperCase()} to Component ID:`, componentId);
            } else {
                console.warn('⚠️ Cannot connect to same component');
            }
            clearConnectionStart();
        }
        // If clicking output again, cancel
        else if (type === 'output' && connectionStartPoint) {
            clearConnectionStart();
            console.log('❌ Connection cancelled');
        }
    }, [type, componentId, polarity, connectionStartPoint, setConnectionStart, clearConnectionStart, addConnection]);

    const isActive = connectionStartPoint?.componentId === componentId &&
        connectionStartPoint?.type === type &&
        connectionStartPoint?.polarity === polarity;

    // Check if this polarity should be highlighted (matching the started connection)
    const isMatchingPolarity = connectionStartPoint &&
        type === 'input' &&
        connectionStartPoint.polarity === polarity;

    return (
        <div
            className={`connection-point ${type} ${polarity} ${isActive ? 'active' : ''} ${isMatchingPolarity ? 'matching' : ''}`}
            data-component-id={componentId}
            data-type={type}
            data-polarity={polarity}
            onClick={handleClick}
            style={style}
            title={polarity === 'hi' ? 'HI (Red/+)' : 'LO (Black/-)'}
        />
    );
}

export default ConnectionPoint;

