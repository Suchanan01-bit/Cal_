/**
 * PlaceholderDevice.jsx
 * Placeholder component for devices not yet implemented
 */

import { useCallback } from 'react';
import { useSimulator } from '../../context/SimulatorContext';
import './PlaceholderDevice.css';

function PlaceholderDevice({ component, onMouseDown, style }) {
    const { removeComponent } = useSimulator();

    const handleDelete = useCallback(() => {
        removeComponent(component.id);
    }, [component.id, removeComponent]);

    const getDeviceName = (type) => {
        const names = {
            'smb100b': 'R&S SMB100B',
            'fsmr': 'R&S FSMR',
        };
        return names[type] || type;
    };

    return (
        <div
            className="placed-component placeholder-device"
            data-component-id={component.id}
            onMouseDown={onMouseDown}
            style={style}
        >
            <div className="placeholder-header">
                <span className="placeholder-logo">R&S®</span>
                <span className="placeholder-model">{getDeviceName(component.type)}</span>
                <button className="placeholder-delete" onClick={handleDelete}>×</button>
            </div>
            <div className="placeholder-body">
                <div className="placeholder-screen">
                    <div className="placeholder-value">1.000 000 00 GHz</div>
                    <div className="placeholder-level">-10.00 dBm</div>
                </div>
                <div className="placeholder-note">
                    [Placeholder - จะพัฒนาเพิ่มในอนาคต]
                </div>
            </div>
        </div>
    );
}

export default PlaceholderDevice;
