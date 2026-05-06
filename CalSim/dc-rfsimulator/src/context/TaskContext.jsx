import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useSimulator } from './SimulatorContext';

const TaskContext = createContext(null);

const DEFAULT_TASKS = [
    {
        id: 't1',
        description: 'Source 5V DC using Fluke 5500A and measure with Multimeter',
        sourceDevice: 'fluke5500a',
        sourceValue: 5,
        sourceMode: 'DC Voltage',
        measureDevice: 'multimeter',
        measureMode: 'DC V',
        completed: false
    },
    {
        id: 't2',
        description: 'Source 1kΩ Resistance using Fluke 5500A and measure with Multimeter',
        sourceDevice: 'fluke5500a',
        sourceValue: 1000,
        sourceMode: 'Resistance',
        measureDevice: 'multimeter',
        measureMode: 'Ω',
        completed: false
    }
];

export function TaskProvider({ children }) {
    const { components, connections } = useSimulator();
    const [tasks, setTasks] = useState([...DEFAULT_TASKS]);
    const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);

    // Evaluate task completion
    const evaluateTask = useCallback((task, comps, conns) => {
        // 1. Find source
        const source = comps.find(c => c.type === task.sourceDevice);
        if (!source) return false;

        // Ensure source is active and has correct parameters
        if (!source.state.power) return false;
        
        // Some devices use 'output', some use 'rfOn', some have neither (always on). 
        // For standard calibrators, we check 'output'
        if ('output' in source.state && !source.state.output) return false;
        
        if (source.state.mode && source.state.mode !== task.sourceMode) return false;

        // Check value (tolerance 0.01)
        const val = source.state.value || source.state.level || 0;
        if (Math.abs(val - task.sourceValue) > 0.01) return false;

        // 2. Find target
        const target = comps.find(c => c.type === task.measureDevice);
        if (!target) return false;
        
        if (!target.state.power) return false;
        if (target.state.mode && target.state.mode !== task.measureMode) return false;

        // 3. Find connection between source and target
        // For multimeters, Current requires AUX ports, Voltage/Resistance requires normal HI/LO ports
        const isCurrent = task.measureMode.includes('A');
        const targetPolHi = isCurrent ? 'aux_hi' : 'hi';
        const targetPolLo = isCurrent ? 'aux_lo' : 'lo';

        const hiConn = conns.find(c => c.from === source.id && c.to === target.id && c.polarity === targetPolHi);
        const loConn = conns.find(c => c.from === source.id && c.to === target.id && c.polarity === targetPolLo);

        // Standard 2-wire connection
        if (hiConn && loConn) return true;

        // If not standard, check if there's any valid connection (e.g., RF single cable)
        const anyConn = conns.find(c => c.from === source.id && c.to === target.id);
        if (anyConn && !target.state.mode) { // e.g., Spectrum Analyzer has no mode selection
            return true;
        }

        return false;
    }, []);

    // Check all tasks continuously
    useEffect(() => {
        let updated = false;
        const newTasks = tasks.map(task => {
            if (task.completed) return task; // Already done
            
            const isCompleted = evaluateTask(task, components, connections);
            if (isCompleted) {
                updated = true;
                return { ...task, completed: true };
            }
            return task;
        });

        if (updated) {
            setTasks(newTasks);
        }
    }, [components, connections, tasks, evaluateTask]);

    const addTask = useCallback((newTask) => {
        setTasks(prev => [...prev, { ...newTask, id: 'task_' + Date.now(), completed: false }]);
    }, []);

    const removeTask = useCallback((id) => {
        setTasks(prev => prev.filter(t => t.id !== id));
    }, []);

    const openTaskModal = useCallback(() => setIsTaskModalOpen(true), []);
    const closeTaskModal = useCallback(() => setIsTaskModalOpen(false), []);

    const value = {
        tasks,
        addTask,
        removeTask,
        isTaskModalOpen,
        openTaskModal,
        closeTaskModal
    };

    return (
        <TaskContext.Provider value={value}>
            {children}
        </TaskContext.Provider>
    );
}

export function useTasks() {
    const context = useContext(TaskContext);
    if (!context) {
        throw new Error('useTasks must be used within a TaskProvider');
    }
    return context;
}
