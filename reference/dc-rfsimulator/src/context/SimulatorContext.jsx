/**
 * SimulatorContext.jsx
 * React Context for global state management
 */

import { createContext, useContext, useReducer, useCallback } from 'react';
import { getInitialState, getCalibratorTypes, getUUCTypes } from '../registry/deviceRegistry';

// Compliance status types for uncertainty mode
const COMPLIANCE_STATUSES = ['compliance', 'non_compliance', 'out_of_tolerance'];

// Initial state
const initialState = {
    components: [],          // All devices on canvas
    connections: [],         // Wire connections between devices
    componentIdCounter: 0,   // Counter for unique IDs
    connectionStartPoint: null, // Point when creating connection
    alerts: [],              // Connection alerts/notifications
    alertIdCounter: 0,       // Counter for alert IDs
    uncertaintyMode: false,  // Deprecated in favor of errorSimulation.resolutionUncertainty but kept for backward compatibility if needed
    errorSimulation: {
        loadingError: false,
        resolutionUncertainty: false,
        instrumentError: false
    }
};

// Action types
const ActionTypes = {
    ADD_COMPONENT: 'ADD_COMPONENT',
    REMOVE_COMPONENT: 'REMOVE_COMPONENT',
    UPDATE_COMPONENT_POSITION: 'UPDATE_COMPONENT_POSITION',
    UPDATE_DEVICE_STATE: 'UPDATE_DEVICE_STATE',
    ADD_CONNECTION: 'ADD_CONNECTION',
    REMOVE_CONNECTION: 'REMOVE_CONNECTION',
    REMOVE_CONNECTIONS_FOR_COMPONENT: 'REMOVE_CONNECTIONS_FOR_COMPONENT',
    SET_CONNECTION_START: 'SET_CONNECTION_START',
    CLEAR_CONNECTION_START: 'CLEAR_CONNECTION_START',
    CLEAR_ALL: 'CLEAR_ALL',
    LOAD_PROJECT: 'LOAD_PROJECT',
    ADD_ALERT: 'ADD_ALERT',
    DISMISS_ALERT: 'DISMISS_ALERT',
    TOGGLE_UNCERTAINTY_MODE: 'TOGGLE_UNCERTAINTY_MODE',
    TOGGLE_ERROR_SIMULATION: 'TOGGLE_ERROR_SIMULATION',
    TOGGLE_CONNECTION_WIRE_TYPE: 'TOGGLE_CONNECTION_WIRE_TYPE',
};

// Reducer
function simulatorReducer(state, action) {
    switch (action.type) {
        case ActionTypes.ADD_COMPONENT: {
            const newId = state.componentIdCounter;
            const deviceType = action.payload.type;
            const isUUC = getUUCTypes().includes(deviceType);

            // Random compliance status for UUC when uncertainty mode is ON
            let complianceStatus = null;
            if (state.uncertaintyMode && isUUC) {
                const randomIndex = Math.floor(Math.random() * COMPLIANCE_STATUSES.length);
                complianceStatus = COMPLIANCE_STATUSES[randomIndex];
            }

            const newComponent = {
                id: newId,
                type: deviceType,
                x: action.payload.x,
                y: action.payload.y,
                state: {
                    ...getInitialDeviceState(deviceType),
                    complianceStatus: complianceStatus,
                },
            };
            return {
                ...state,
                components: [...state.components, newComponent],
                componentIdCounter: newId + 1,
            };
        }

        case ActionTypes.REMOVE_COMPONENT:
            return {
                ...state,
                components: state.components.filter(c => c.id !== action.payload.id),
                connections: state.connections.filter(
                    conn => conn.from !== action.payload.id && conn.to !== action.payload.id
                ),
            };

        case ActionTypes.UPDATE_COMPONENT_POSITION:
            return {
                ...state,
                components: state.components.map(c =>
                    c.id === action.payload.id
                        ? { ...c, x: action.payload.x, y: action.payload.y }
                        : c
                ),
            };

        case ActionTypes.UPDATE_DEVICE_STATE:
            return {
                ...state,
                components: state.components.map(c =>
                    c.id === action.payload.id
                        ? { ...c, state: { ...c.state, ...action.payload.state } }
                        : c
                ),
            };

        case ActionTypes.ADD_CONNECTION:
            return {
                ...state,
                connections: [...state.connections, {
                    from: action.payload.from,
                    to: action.payload.to,
                    polarity: action.payload.polarity || 'hi',
                    wireProperties: { type: 'standard', resistance: 0.05 }
                }],
                connectionStartPoint: null,
            };

        case ActionTypes.REMOVE_CONNECTION:
            return {
                ...state,
                connections: state.connections.filter(
                    (_, index) => index !== action.payload.index
                ),
            };

        case ActionTypes.REMOVE_CONNECTIONS_FOR_COMPONENT:
            return {
                ...state,
                connections: state.connections.filter(
                    conn => conn.from !== action.payload.id && conn.to !== action.payload.id
                ),
            };

        case ActionTypes.SET_CONNECTION_START:
            return {
                ...state,
                connectionStartPoint: action.payload,
            };

        case ActionTypes.CLEAR_CONNECTION_START:
            return {
                ...state,
                connectionStartPoint: null,
            };

        case ActionTypes.CLEAR_ALL:
            return {
                ...initialState,
            };

        case ActionTypes.LOAD_PROJECT:
            return {
                ...state,
                components: action.payload.components,
                connections: action.payload.connections,
                componentIdCounter: Math.max(...action.payload.components.map(c => c.id), 0) + 1,
            };

        case ActionTypes.ADD_ALERT: {
            const alertId = state.alertIdCounter;
            return {
                ...state,
                alerts: [...state.alerts, { ...action.payload, id: alertId }],
                alertIdCounter: alertId + 1,
            };
        }

        case ActionTypes.DISMISS_ALERT:
            return {
                ...state,
                alerts: state.alerts.filter(a => a.id !== action.payload.id),
            };

        case ActionTypes.TOGGLE_UNCERTAINTY_MODE: {
            const newMode = !state.uncertaintyMode;
            return {
                ...state,
                uncertaintyMode: newMode,
                components: state.components.map(c => {
                    const isUUC = getUUCTypes().includes(c.type);
                    if (isUUC && newMode) {
                        // Assign random compliance status when mode is enabled
                        const randomIndex = Math.floor(Math.random() * COMPLIANCE_STATUSES.length);
                        return {
                            ...c,
                            state: {
                                ...c.state,
                                complianceStatus: COMPLIANCE_STATUSES[randomIndex]
                            }
                        };
                    }
                    return c;
                })
            };
        }

        case ActionTypes.TOGGLE_ERROR_SIMULATION:
            return {
                ...state,
                errorSimulation: {
                    ...state.errorSimulation,
                    [action.payload.errorType]: !state.errorSimulation[action.payload.errorType]
                },
            };

        case ActionTypes.TOGGLE_CONNECTION_WIRE_TYPE:
            return {
                ...state,
                connections: state.connections.map((conn, index) => {
                    if (index !== action.payload.index) return conn;

                    const isStandard = conn.wireProperties?.type === 'standard';
                    return {
                        ...conn,
                        wireProperties: {
                            type: isStandard ? 'bad' : 'standard',
                            // Standard: 0.05 Ohm, Bad: 5.0 Ohm (simulating very poor contact/long wire)
                            resistance: isStandard ? 5.0 : 0.05
                        }
                    };
                })
            };

        default:
            return state;
    }
}

// Get initial state for each device type - now uses registry
function getInitialDeviceState(type) {
    return getInitialState(type);
}

// Create context
const SimulatorContext = createContext(null);

// Provider component
export function SimulatorProvider({ children }) {
    const [state, dispatch] = useReducer(simulatorReducer, initialState);

    // Actions
    const addComponent = useCallback((type, x, y) => {
        dispatch({ type: ActionTypes.ADD_COMPONENT, payload: { type, x, y } });
    }, []);

    const removeComponent = useCallback((id) => {
        dispatch({ type: ActionTypes.REMOVE_COMPONENT, payload: { id } });
    }, []);

    const updateComponentPosition = useCallback((id, x, y) => {
        dispatch({ type: ActionTypes.UPDATE_COMPONENT_POSITION, payload: { id, x, y } });
    }, []);

    const updateDeviceState = useCallback((id, newState) => {
        dispatch({ type: ActionTypes.UPDATE_DEVICE_STATE, payload: { id, state: newState } });
    }, []);

    // Add alert notification
    const addAlert = useCallback((type, title, message) => {
        dispatch({ type: ActionTypes.ADD_ALERT, payload: { type, title, message } });
    }, []);

    // Dismiss alert
    const dismissAlert = useCallback((id) => {
        dispatch({ type: ActionTypes.DISMISS_ALERT, payload: { id } });
    }, []);

    // Check if devices are compatible for connection - uses registry
    const checkConnectionCompatibility = useCallback((fromId, toId, polarity = 'hi') => {
        const fromComp = state.components.find(c => c.id === fromId);
        const toComp = state.components.find(c => c.id === toId);

        if (!fromComp || !toComp) return { valid: false, message: 'อุปกรณ์ไม่พบ' };

        // Get device roles from registry
        const calibrators = getCalibratorTypes();
        const uucs = getUUCTypes();

        const isFromCalibrator = calibrators.includes(fromComp.type);
        const isToUUC = uucs.includes(toComp.type);

        if (!isFromCalibrator) {
            return { valid: false, message: 'ต้องเชื่อมต่อจาก Calibrator' };
        }

        if (!isToUUC) {
            return { valid: false, message: 'ต้องเชื่อมต่อไปยัง UUC' };
        }

        // Check if already connected WITH SAME POLARITY (allow HI + LO separately)
        const existingConnection = state.connections.find(
            c => c.from === fromId && c.to === toId && c.polarity === polarity
        );
        if (existingConnection) {
            const polarityLabel = polarity === 'hi' ? 'HI' : 'LO';
            return { valid: false, message: `สาย ${polarityLabel} เชื่อมต่อกันอยู่แล้ว` };
        }

        return { valid: true, message: 'เชื่อมต่อสำเร็จ' };
    }, [state.components, state.connections]);

    // Add connection with validation
    const addConnection = useCallback((from, to, polarity = 'hi') => {
        const compatibility = checkConnectionCompatibility(from, to, polarity);

        if (compatibility.valid) {
            dispatch({ type: ActionTypes.ADD_CONNECTION, payload: { from, to, polarity } });
            const polarityLabel = polarity === 'hi' ? 'HI (ขั้วบวก)' : 'LO (ขั้วลบ)';
            addAlert('success', 'เชื่อมต่อสำเร็จ', `สาย ${polarityLabel} เชื่อมต่อระหว่าง Calibrator และ UUC เรียบร้อยแล้ว`);
        } else {
            addAlert('error', 'เชื่อมต่อไม่สำเร็จ', compatibility.message);
        }

        return compatibility;
    }, [checkConnectionCompatibility, addAlert]);

    const removeConnection = useCallback((index) => {
        dispatch({ type: ActionTypes.REMOVE_CONNECTION, payload: { index } });
    }, []);

    const setConnectionStart = useCallback((point) => {
        dispatch({ type: ActionTypes.SET_CONNECTION_START, payload: point });
    }, []);

    const clearConnectionStart = useCallback(() => {
        dispatch({ type: ActionTypes.CLEAR_CONNECTION_START });
    }, []);

    const clearAll = useCallback(() => {
        dispatch({ type: ActionTypes.CLEAR_ALL });
    }, []);

    const loadProject = useCallback((projectData) => {
        dispatch({ type: ActionTypes.LOAD_PROJECT, payload: projectData });
    }, []);

    // Get component by ID
    const getComponent = useCallback((id) => {
        return state.components.find(c => c.id === id);
    }, [state.components]);

    // Check if output is active
    const isOutputActive = useCallback((componentId) => {
        const comp = state.components.find(c => c.id === componentId);
        if (!comp) return false;

        if (comp.type === 'sma100a') {
            return comp.state.power && comp.state.rfOn;
        }
        if (comp.type === 'fluke5500a') {
            return comp.state.power && comp.state.output;
        }
        return false;
    }, [state.components]);

    // Check if component is connected
    const isComponentConnected = useCallback((componentId) => {
        return state.connections.some(
            conn => conn.from === componentId || conn.to === componentId
        );
    }, [state.connections]);

    // Toggle uncertainty mode
    const toggleUncertaintyMode = useCallback(() => {
        dispatch({ type: ActionTypes.TOGGLE_UNCERTAINTY_MODE });
    }, []);

    // Toggle specific error simulation
    const toggleErrorSimulation = useCallback((errorType) => {
        dispatch({ type: ActionTypes.TOGGLE_ERROR_SIMULATION, payload: { errorType } });
    }, []);

    // Toggle wire type (Standard <-> Bad)
    const toggleConnectionWireType = useCallback((index) => {
        dispatch({ type: ActionTypes.TOGGLE_CONNECTION_WIRE_TYPE, payload: { index } });
    }, []);

    const value = {
        ...state,
        addComponent,
        removeComponent,
        updateComponentPosition,
        updateDeviceState,
        addConnection,
        removeConnection,
        setConnectionStart,
        clearConnectionStart,
        clearAll,
        loadProject,
        getComponent,
        isOutputActive,
        isComponentConnected,
        addAlert,
        dismissAlert,
        checkConnectionCompatibility,
        toggleUncertaintyMode,
        toggleErrorSimulation,
        toggleConnectionWireType,
    };

    return (
        <SimulatorContext.Provider value={value}>
            {children}
        </SimulatorContext.Provider>
    );
}

// Custom hook to use the context
export function useSimulator() {
    const context = useContext(SimulatorContext);
    if (!context) {
        throw new Error('useSimulator must be used within a SimulatorProvider');
    }
    return context;
}

export default SimulatorContext;
