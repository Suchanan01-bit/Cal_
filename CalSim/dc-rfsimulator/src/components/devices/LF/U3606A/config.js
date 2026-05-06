/**
 * Device Configuration - Keysight U3606A
 * 5½ Digit Multimeter + DC Power Supply
 */

export default {
    type: 'u3606a',
    name: '5 1/2 Digital Multimeter',
    description: '5½ Digit DMM + DC Supply',
    icon: '🔬',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc', // Unit Under Calibration (input device)

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'DCV',
        value: 0,
        unit: 'V',
        autoRange: true,
        range: 'AUTO',
        // DC Supply section
        dcSupply: {
            enabled: false,
            voltage: 0,
            current: 0,
            outputOn: false,
        },
    },
};
