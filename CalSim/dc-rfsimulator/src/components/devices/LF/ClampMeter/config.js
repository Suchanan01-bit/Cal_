/**
 * Device Configuration - Clamp Meter
 * Fluke 376 True RMS Clamp Meter
 */

export default {
    type: 'clamp_meter',
    name: 'Clamp Meter',
    description: 'True RMS Clamp Meter',
    icon: '🔧',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'uuc', // Unit Under Calibration (input device)

    // Initial state for new instances
    initialState: {
        power: true,
        mode: 'AC_AMP',
        range: 'AUTO',
        value: 0,
        unit: 'A',
        clampOpen: false,
        iFlexConnected: false,
        hold: false,
        minMax: false,
    },
};
