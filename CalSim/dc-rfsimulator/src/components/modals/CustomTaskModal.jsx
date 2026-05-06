import { useState } from 'react';
import { useTasks } from '../../context/TaskContext';
import './CustomTaskModal.css';

function CustomTaskModal() {
    const { isTaskModalOpen, closeTaskModal, addTask } = useTasks();
    const [description, setDescription] = useState('');
    const [sourceDevice, setSourceDevice] = useState('fluke5500a');
    const [sourceMode, setSourceMode] = useState('DC Voltage');
    const [sourceValue, setSourceValue] = useState(5);
    const [measureDevice, setMeasureDevice] = useState('multimeter');
    const [measureMode, setMeasureMode] = useState('DC V');

    if (!isTaskModalOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        
        if (!description.trim()) {
            alert('Please enter a task description.');
            return;
        }

        addTask({
            description,
            sourceDevice,
            sourceMode,
            sourceValue: parseFloat(sourceValue),
            measureDevice,
            measureMode
        });

        // Reset and close
        setDescription('');
        setSourceValue(5);
        closeTaskModal();
    };

    return (
        <div className="task-modal-overlay">
            <div className="task-modal-content">
                <div className="task-modal-header">
                    <h2>Create Custom Task</h2>
                    <button className="task-modal-close" onClick={closeTaskModal}>×</button>
                </div>
                
                <form onSubmit={handleSubmit} className="task-modal-form">
                    <div className="form-group full-width">
                        <label>Task Description</label>
                        <input 
                            type="text" 
                            value={description} 
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="e.g., Measure 10V DC from Calibrator"
                            required
                        />
                    </div>

                    <h3 className="section-title">Source Settings</h3>
                    <div className="form-row">
                        <div className="form-group">
                            <label>Source Device</label>
                            <select value={sourceDevice} onChange={(e) => setSourceDevice(e.target.value)}>
                                <option value="fluke5500a">Fluke 5500A (LF)</option>
                                <option value="fluke5522a">Fluke 5522A (LF)</option>
                                <option value="sma100a">R&S SMA100A (RF)</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Output Mode</label>
                            <select value={sourceMode} onChange={(e) => setSourceMode(e.target.value)}>
                                <option value="DC Voltage">DC Voltage</option>
                                <option value="AC Voltage">AC Voltage</option>
                                <option value="DC Current">DC Current</option>
                                <option value="AC Current">AC Current</option>
                                <option value="Resistance">Resistance</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Target Value</label>
                            <input 
                                type="number" 
                                step="any"
                                value={sourceValue} 
                                onChange={(e) => setSourceValue(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <h3 className="section-title">Measurement Settings</h3>
                    <div className="form-row">
                        <div className="form-group">
                            <label>Measure Device</label>
                            <select value={measureDevice} onChange={(e) => setMeasureDevice(e.target.value)}>
                                <option value="multimeter">Digital Multimeter</option>
                                <option value="oscilloscope">Oscilloscope</option>
                                <option value="fpc1500">Spectrum Analyzer</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Measure Mode</label>
                            <select value={measureMode} onChange={(e) => setMeasureMode(e.target.value)}>
                                <option value="DC V">DC V</option>
                                <option value="AC V">AC V</option>
                                <option value="DC A">DC A</option>
                                <option value="AC A">AC A</option>
                                <option value="Ω">Ω</option>
                            </select>
                        </div>
                    </div>

                    <div className="task-modal-actions">
                        <button type="button" className="btn-cancel" onClick={closeTaskModal}>Cancel</button>
                        <button type="submit" className="btn-submit">Create Task</button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default CustomTaskModal;
