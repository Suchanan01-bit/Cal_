/**
 * AnalogMultimeter Device Package
 * Simpson 260 Analog VOM (Volt-Ohm-Milliammeter)
 */

import AnalogMultimeter from './AnalogMultimeter';

// Device Configuration
export const config = {
    type: 'analog_multimeter',
    name: 'Analog Multimeter',
    description: 'Simpson 260 Analog VOM',
    icon: '🎛️',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc',  // Unit Under Calibration

    // Tolerance for each mode (percentage of reading)
    tolerance: {
        'DCV': 0.5,    // ±0.5% (analog meters have lower accuracy)
        'ACV': 1.0,    // ±1.0%
        'DCA': 1.5,    // ±1.5%
        'OHM': 2.0,    // ±2.0%
    },

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'DCV',
        range: '10V',
        value: 0,
        unit: 'V',
        needlePosition: -45,
        zeroOffset: 0,
        complianceStatus: null,
    },
};

// Export component as default
export default AnalogMultimeter;
