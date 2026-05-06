/**
 * Device Configuration - Fluke5500A
 * Fluke 5500A Multi-Product Calibrator
 */

export default {
    type: 'fluke5500a',
    name: 'Calibrator',
    description: 'Multi-Product Calibrator',
    icon: '🔧',
    category: 'transmitter',
    categoryLabel: 'Transmitter',
    role: 'calibrator', // Output device

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
