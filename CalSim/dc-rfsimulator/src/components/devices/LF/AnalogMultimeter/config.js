/**
 * Device Configuration - Analog Multimeter
 * Simpson 260 Analog VOM (Volt-Ohm-Milliammeter)
 */

export default {
    type: 'analog_multimeter',
    name: 'Analog Multimeter',
    description: 'Simpson 260 Analog VOM',
    icon: '🎛️',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc', // Unit Under Calibration (input device)

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'DCV',
        range: '10V',
        value: 0,
        unit: 'V',
        needlePosition: -45,
        zeroOffset: 0,
    },
};
