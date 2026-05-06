/**
 * SMA100A Device Package
 * R&S SMA100A Analog Signal Generator
 */

import SMA100A from './SMA100A';

// Device Configuration
export const config = {
    type: 'sma100a',
    name: 'Signal Generator',
    description: 'Analog Signal Generator',
    icon: '📡',
    category: 'transmitter',
    categoryLabel: 'Transmitter',
    role: 'calibrator',

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

// Export component as default
export default SMA100A;
