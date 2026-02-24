/**
 * Sidebar.jsx
 * Component library sidebar with draggable devices
 */

import './Sidebar.css';
import { getDevicesByCategory } from '../../registry/deviceRegistry';

// Get device definitions from registry
const deviceCategories = getDevicesByCategory();

function Sidebar() {
    // Handle drag start
    const handleDragStart = (e, type) => {
        e.dataTransfer.setData('deviceType', type);
        e.target.classList.add('dragging');
    };

    // Handle drag end
    const handleDragEnd = (e) => {
        e.target.classList.remove('dragging');
    };

    return (
        <div className="sidebar">
            <div className="sidebar-header">
                <div className="sidebar-title">🔬 Component Library</div>
                <div className="sidebar-subtitle">Drag components to canvas</div>
            </div>

            {/* Transmitter Category */}
            {deviceCategories.transmitter && (
                <div className="category transmitter">
                    <div className="category-title">📤 {deviceCategories.transmitter.label}</div>

                    {deviceCategories.transmitter.devices.map((device) => (
                        <div
                            key={device.type}
                            className="component"
                            draggable="true"
                            onDragStart={(e) => handleDragStart(e, device.type)}
                            onDragEnd={handleDragEnd}
                        >
                            <div className="component-icon">{device.icon}</div>
                            <div className="component-info">
                                <div className="component-name">{device.name}</div>
                                <div className="component-desc">{device.description}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Receiver Category */}
            {deviceCategories.receiver && (
                <div className="category receiver">
                    <div className="category-title">📥 {deviceCategories.receiver.label}</div>

                    {deviceCategories.receiver.devices.map((device) => (
                        <div
                            key={device.type}
                            className="component"
                            draggable="true"
                            onDragStart={(e) => handleDragStart(e, device.type)}
                            onDragEnd={handleDragEnd}
                        >
                            <div className="component-icon">{device.icon}</div>
                            <div className="component-info">
                                <div className="component-name">{device.name}</div>
                                <div className="component-desc">{device.description}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default Sidebar;
