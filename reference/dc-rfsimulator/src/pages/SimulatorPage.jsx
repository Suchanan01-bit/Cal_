/**
 * SimulatorPage.jsx
 * Main simulator canvas page with sidebar and toolbar
 */

import { useState, useRef, useCallback } from 'react';
import { useSimulator } from '../context/SimulatorContext';
import Sidebar from '../components/layout/Sidebar';
import Canvas from '../components/layout/Canvas';
import Toolbar from '../components/layout/Toolbar';
import GuideModal from '../components/modals/GuideModal';
import './SimulatorPage.css';

function SimulatorPage({ onNavigate }) {
    const [showGuide, setShowGuide] = useState(false);
    const canvasRef = useRef(null);
    const { clearAll, components, connections, loadProject } = useSimulator();

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
            <Sidebar />

            <div className="canvas-area">
                <Canvas ref={canvasRef} />

                <Toolbar
                    onClear={handleClearAll}
                    onSave={handleSaveProject}
                    onLoad={handleLoadProject}
                    onGuide={() => setShowGuide(true)}
                    onBack={onNavigate}
                />
            </div>

            {showGuide && <GuideModal onClose={() => setShowGuide(false)} />}
        </div>
    );
}

export default SimulatorPage;
