/**
 * ClampMeter Device Package
 * Fluke 376 True RMS Clamp Meter
 */

import ClampMeter from './ClampMeter';

// Device Configuration
export const config = {
    type: 'clamp_meter',
    name: 'Clamp Meter',
    description: 'True RMS Clamp Meter',
    icon: '🔧',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc',  // Unit Under Calibration

    // Tolerance for each mode (percentage of reading)
    tolerance: {
        'AC_AMP': 0.02,   // ±2%
        'DC_AMP': 0.02,   // ±2%
        'AC_V': 0.01,     // ±1%
        'DC_V': 0.01,     // ±1%
        'OHM': 0.015,     // ±1.5%
        'FREQ': 0.01,     // ±0.1%
    },

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'AC_AMP',
        range: 'AUTO',
        value: 0,
        unit: 'A',
        clampOpen: false,
        iFlexConnected: false,
        hold: false,
        minMax: false,
        complianceStatus: null,
    },
};

// Export component as default
export default ClampMeter;
