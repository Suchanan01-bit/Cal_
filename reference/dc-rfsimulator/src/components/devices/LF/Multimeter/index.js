/**
 * Multimeter Device Package
 * Digital Multimeter - 6.5 Digit DMM
 */

import Multimeter from './Multimeter';

// Device Configuration
export const config = {
    type: 'multimeter',
    name: 'Digital Multimeter',
    description: '5.5 Digit DMM',
    icon: '⚡',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc',  // Unit Under Calibration

    // Tolerance for each mode (percentage of reading)
    // Tolerance for each mode (percentage of reading)
    // Updated for 5 ½ Digit DMM specs (approx)
    tolerance: {
        'DC V': 0.015,   // ±0.015%
        'AC V': 0.06,    // ±0.06%
        'DC A': 0.05,    // ±0.05%
        'AC A': 0.15,    // ±0.15%
        'Ω': 0.04,       // ±0.04%
        'F': 1.0,        // ±1.0%
        'Hz': 0.005      // ±0.005%
    },

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'DC V',
        value: 0,
        unit: 'V',
        autoRange: true,
        complianceStatus: null,
    },
};

// Export component as default
export default Multimeter;
