/**
 * Device Configuration - SMA100A
 * R&S SMA100A Analog Signal Generator
 */

export default {
    type: 'sma100a',
    name: 'Signal Generator',
    description: 'Analog Signal Generator',
    icon: '📡',
    category: 'transmitter',
    categoryLabel: 'Transmitter',
    role: 'calibrator', // Output device

    // Initial state for new instances
    initialState: {
        power: true,
        frequency: 6.000000000,  // GHz
        frequencyUnit: 'GHz',
        level: 15.00,           // dBm
        rfOn: false,
        modOn: false,
        inputBuffer: '',
    },
};
