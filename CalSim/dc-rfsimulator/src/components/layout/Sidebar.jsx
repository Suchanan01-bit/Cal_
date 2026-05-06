import { useState } from 'react';
import './Sidebar.css';
import { getDevicesByCategory } from '../../registry/deviceRegistry';

const deviceCategories = getDevicesByCategory();

function Sidebar() {
    // Get array of category keys (e.g. ['transmitter', 'receiver'])
    const categoryKeys = Object.keys(deviceCategories);
    const [activeTab, setActiveTab] = useState(categoryKeys[0] || '');

    const handleDragStart = (e, type) => {
        e.dataTransfer.setData('deviceType', type);
        e.target.classList.add('dragging');
    };

    const handleDragEnd = (e) => {
        e.target.classList.remove('dragging');
    };

    if (!activeTab) return null;

    const activeCategory = deviceCategories[activeTab];

    return (
        <div className="bottom-panel">
            <div className="panel-tabs">
                {categoryKeys.map(key => (
                    <button 
                        key={key}
                        className={`tab-btn ${activeTab === key ? 'active' : ''} ${key}`}
                        onClick={() => setActiveTab(key)}
                    >
                        {key === 'transmitter' ? '📤 ' : '📥 '}
                        {deviceCategories[key].label}
                    </button>
                ))}
            </div>
            
            <div className="panel-content">
                <div className="devices-container">
                    {activeCategory.devices.map((device) => (
                        <div
                            key={device.type}
                            className="component-card"
                            draggable="true"
                            onDragStart={(e) => handleDragStart(e, device.type)}
                            onDragEnd={handleDragEnd}
                            title={device.description}
                        >
                            <div className="component-card-icon">{device.icon}</div>
                            <div className="component-card-name">{device.name}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default Sidebar;
