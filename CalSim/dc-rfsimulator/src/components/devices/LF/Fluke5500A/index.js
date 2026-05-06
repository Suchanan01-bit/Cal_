/**
 * Fluke5500A Device Package
 * Fluke 5500A Multi-Product Calibrator
 */

import Fluke5500A from './Fluke5500A';

// Device Configuration
export const config = {
    type: 'fluke5500a',
    name: 'Calibrator',
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
        value: 0,
        unit: 'V',
        prefix: '',
        frequency: 1000,        // Hz
        waveform: 'Sine',
        inputBuffer: '',
        editingFrequency: false,
        tcType: 'K',
    },
};

// Export component as default
export default Fluke5500A;
