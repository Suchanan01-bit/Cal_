/**
 * SimulatorPage.jsx
 * Main simulator canvas page with sidebar and toolbar
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { useSimulator } from '../context/SimulatorContext';
import Sidebar from '../components/layout/Sidebar';
import Canvas from '../components/layout/Canvas';
import GuideModal from '../components/modals/GuideModal';
import TaskBox from '../components/layout/TaskBox';
import CustomTaskModal from '../components/modals/CustomTaskModal';
import './SimulatorPage.css';

function SimulatorPage({ onNavigate }) {
    const [showGuide, setShowGuide] = useState(false);
    const canvasRef = useRef(null);
    const { clearAll, components, connections, loadProject, toggleErrorSimulation, toggleUncertaintyMode } = useSimulator();
    
    // Expose API for PyQt
    useEffect(() => {
        window.simulatorAPI = {
            clearAll: () => {
                if (window.confirm('Clear all components?')) {
                    clearAll();
                    console.log('🗑️ Canvas cleared via PyQt');
                }
            },
            toggleError: (type) => toggleErrorSimulation(type),
            toggleUncertainty: () => toggleUncertaintyMode()
        };
        return () => { delete window.simulatorAPI; };
    }, [clearAll, toggleErrorSimulation, toggleUncertaintyMode]);

    // Save project to JSON file
    const handleSaveProject = useCallback(() => {
        const projectData = {
            version: '2.0',
            timestamp: new Date().toISOString(),
            components: components,
            connections: connections,
        };

        const json = JSON.stringify(projectData, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `rf-lf-project-${Date.now()}.json`;
        a.click();

        URL.revokeObjectURL(url);
        console.log('💾 Project saved');
    }, [components, connections]);

    // Load project from JSON file
    const handleLoadProject = useCallback(() => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';

        input.onchange = (e) => {
            const file = e.target.files[0];
            const reader = new FileReader();

            reader.onload = (event) => {
                try {
                    const projectData = JSON.parse(event.target.result);
                    loadProject({
                        components: projectData.components || [],
                        connections: projectData.connections || [],
                    });
                    console.log('📂 Project loaded');
                } catch (err) {
                    alert('Error loading project: ' + err.message);
                }
            };

            reader.readAsText(file);
        };

        input.click();
    }, [loadProject]);

    // Clear all components
    const handleClearAll = useCallback(() => {
        if (window.confirm('Clear all components?')) {
            clearAll();
            console.log('🗑️ Canvas cleared');
        }
    }, [clearAll]);

    return (
        <div className="simulator-container">
            <div className="canvas-area">
                <TaskBox />
                <Canvas ref={canvasRef} />
            </div>
            <Sidebar />

            {showGuide && <GuideModal onClose={() => setShowGuide(false)} />}
            <CustomTaskModal />
        </div>
    );
}

export default SimulatorPage;
