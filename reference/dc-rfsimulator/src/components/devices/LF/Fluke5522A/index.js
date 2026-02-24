/**
 * Fluke5522A Device Package
 * Fluke 5522A Multi-Product Calibrator
 */

import Fluke5522A from './Fluke5522A';

// Device Configuration
export const config = {
    type: 'fluke5522a',
    name: 'Fluke 5522A',
    description: 'Multi-Product Calibrator',
    icon: '🔧',
    category: 'transmitter',
    categoryLabel: 'Transmitter',
    role: 'calibrator',

    // Initial state for new instances
    initialState: {
        power: true,
        output: false,          // OPR/STBY
        mode: 'DC Voltage',
        value: 1.0,
        unit: 'V',
        prefix: '',
        range: '3.3',
        autoRange: true,
        frequency: 1000,        // Hz
        waveform: 'Sine',
        inputBuffer: '',
        editingFrequency: false,
        tcType: 'K',
        knobAngle: 0,
    },
};

// Export component as default
export default Fluke5522A;
