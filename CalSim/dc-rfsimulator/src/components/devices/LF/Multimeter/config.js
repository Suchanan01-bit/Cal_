/**
 * Device Configuration - Multimeter
 * Digital Multimeter (6.5 Digit DMM)
 */

export default {
    type: 'multimeter',
    name: 'Digital Multimeter',
    description: '6.5 Digit DMM',
    icon: '⚡',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc', // Unit Under Calibration (input device)

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'DC V',
        value: 0,
        unit: 'V',
        autoRange: true,
    },
};
