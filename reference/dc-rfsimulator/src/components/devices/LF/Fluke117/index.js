/**
 * Fluke117 Device Package
 * Fluke 117 True RMS Digital Multimeter
 */

import Fluke117 from './Fluke117';

// Device Configuration
export const config = {
    type: 'fluke117',
    name: 'Fluke 117',
    description: 'True RMS Digital Multimeter',
    icon: '🔆',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc', // Unit Under Calibration

    // Tolerance specs based on Fluke 117 datasheet (% of reading)
    tolerance: {
        'DC V': 0.5,    // ±0.5% + 2 digits
        'AC V': 1.0,    // ±1.0% + 3 digits (True RMS)
        'DC mA': 1.0,    // ±1.0% + 2 digits
        'AC mA': 1.5,    // ±1.5% + 3 digits (True RMS)
        'Ω': 0.9,    // ±0.9% + 1 digit
        'Hz': 0.5,    // ±0.5% + 1 digit
        'Diode': 1.5,    // ~1.5% indicative
        '~V': 1.0,    // LoZ mode AC V
    },

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'DC V',
        range: 'AUTO',
        value: 0,
        unit: 'V',
        hold: false,
        minMax: false,
        relMode: false,
        autoRange: true,
        backlight: true,
        complianceStatus: null,
    },
};

// Export component as default
export default Fluke117;
