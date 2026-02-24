/**
 * U3606A Device Package
 * Keysight U3606A - 5½ Digit Multimeter + DC Power Supply
 */

import U3606A from './U3606A';

// Device Configuration
export const config = {
    type: 'u3606a',
    name: '5 1/2 Digital Multimeter',
    description: '5½ Digit DMM + DC Supply',
    icon: '🔬',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc',  // Unit Under Calibration

    // Tolerance for each mode (percentage of reading)
    tolerance: {
        'DCV': 0.0035,   // ±0.0035%
        'ACV': 0.06,     // ±0.06%
        'DCA': 0.05,     // ±0.05%
        'ACA': 0.1,      // ±0.1%
        'OHM': 0.01,     // ±0.01%
        'FREQ': 0.005,   // ±0.005%
    },

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'DCV',
        value: 0,
        unit: 'V',
        autoRange: true,
        range: 'AUTO',
        complianceStatus: null,
        dcSupply: {
            enabled: false,
            voltage: 0,
            current: 0,
            outputOn: false,
        },
    },
};

// Export component as default
export default U3606A;
