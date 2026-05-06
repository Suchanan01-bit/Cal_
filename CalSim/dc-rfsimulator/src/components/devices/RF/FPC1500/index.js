/**
 * FPC1500 Device Package
 * R&S FPC1500 Spectrum Analyzer
 */

import FPC1500 from './FPC1500';

// Device Configuration
export const config = {
    type: 'fpc1500',
    name: 'Spectrum Analyzer',
    description: 'Spectrum Analyzer',
    icon: '📉',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc',  // Input device for receiving signals

    // Tolerance for measurements (dB or percentage)
    tolerance: {
        'level': 0.5,      // ±0.5 dB
        'frequency': 0.01, // ±0.01%
    },

    // Initial state for new instances
    initialState: {
        power: true,
        centerFreq: 1.0,    // GHz
        span: 0.5,          // GHz
        refLevel: 0,        // dBm
        inputBuffer: '',
        complianceStatus: null,
    },
};

// Export component as default
export default FPC1500;
