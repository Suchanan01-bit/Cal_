/**
 * LightSource Device Package
 * Fiber Optic Light Source for Calibration
 */

import LightSource from './LightSource';

// Device Configuration
export const config = {
    type: 'lightsource',
    name: 'Light Source',
    description: 'Fiber Optic Light Source',
    icon: '💡',
    category: 'transmitter',
    categoryLabel: 'Transmitter',
    role: 'calibrator',

    // Initial state for new instances
    initialState: {
        power: true,
        output: false,          // LASER ON/OFF
        wavelength: 1310,       // nm (common wavelengths: 850, 1310, 1550)
        outputPower: -10,       // dBm
        modulationMode: 'CW',   // CW, 270Hz, 1kHz, 2kHz
        displayBrightness: 100, // %
        stabilized: true,       // Stabilized output mode
    },
};

// Export component as default
export default LightSource;
