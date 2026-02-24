import { useState } from 'react';
import { useSimulator } from '../../context/SimulatorContext';
import './Toolbar.css';

function Toolbar({ onClear, onSave, onLoad, onGuide, onBack }) {
    const { uncertaintyMode, toggleUncertaintyMode, errorSimulation, toggleErrorSimulation } = useSimulator();
    const [showSettings, setShowSettings] = useState(false);

    return (
        <div className="toolbar">
            <button className="btn btn-secondary" onClick={onBack}>
                ← Back
            </button>

            {/* Advanced Settings Button & Dropdown */}
            <div className="settings-wrapper">
                <button
                    className="btn btn-advanced"
                    onClick={() => setShowSettings(!showSettings)}
                >
                    ⚙️ Advanced Settings
                </button>

                <div className={`settings-dropdown ${showSettings ? 'open' : ''}`}>
                    <div className="settings-group">
                        <div className="settings-group-title">Error Simulation</div>

                        <label className="setting-item">
                            <input
                                type="checkbox"
                                className="setting-checkbox"
                                checked={uncertaintyMode}
                                onChange={toggleUncertaintyMode}
                            />
                            Uncertainty Mode (Global)
                        </label>

                        <label className="setting-item">
                            <input
                                type="checkbox"
                                className="setting-checkbox"
                                checked={errorSimulation?.loadingError || false}
                                onChange={() => toggleErrorSimulation('loadingError')}
                            />
                            Loading Error
                        </label>

                        <label className="setting-item">
                            <input
                                type="checkbox"
                                className="setting-checkbox"
                                checked={errorSimulation?.resolutionUncertainty || false}
                                onChange={() => toggleErrorSimulation('resolutionUncertainty')}
                            />
                            Resolution Uncertainty
                        </label>

                        <label className="setting-item">
                            <input
                                type="checkbox"
                                className="setting-checkbox"
                                checked={errorSimulation?.instrumentError || false}
                                onChange={() => toggleErrorSimulation('instrumentError')}
                            />
                            Instrument Error
                        </label>
                    </div>
                </div>
            </div>

            <button className="btn btn-danger" onClick={onClear}>
                🗑️ Clear All
            </button>
            <button className="btn btn-success" onClick={onSave}>
                💾 Save
            </button>
            <button className="btn btn-warning" onClick={onLoad}>
                📂 Load
            </button>
            <button className="btn btn-info" onClick={onGuide}>
                📖 Guide
            </button>
        </div>
    );
}

export default Toolbar;
