/**
 * Oscilloscope Device Package
 * Digital Oscilloscope for Signal Measurement
 */

import Oscilloscope from './Oscilloscope';

// Device Configuration
export const config = {
    type: 'oscilloscope',
    name: 'Oscilloscope',
    description: 'Digital Storage Oscilloscope',
    icon: '📺',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc',

    // Tolerance for measurements (percentage)
    tolerance: {
        'frequency': 0.01,   // ±0.01%
        'voltage': 0.02,     // ±2%
        'time': 0.01,        // ±0.01%
    },

    // Initial state for new instances
    initialState: {
        power: true,
        channel1: true,
        channel2: false,
        timebase: 1,           // ms/div
        voltsDiv1: 1,          // V/div for CH1
        voltsDiv2: 1,          // V/div for CH2
        triggerLevel: 0,       // V
        triggerMode: 'AUTO',   // AUTO, NORMAL, SINGLE
        triggerSource: 'CH1',  // CH1, CH2, EXT
        coupling1: 'DC',       // AC, DC, GND
        coupling2: 'DC',       // AC, DC, GND
        running: true,         // Run/Stop state
        measuredFrequency: 0,
        measuredVpp: 0,
        measuredVrms: 0,
        complianceStatus: null,
    },
};

// Export component as default
export default Oscilloscope;
