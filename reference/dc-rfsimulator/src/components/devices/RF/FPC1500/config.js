/**
 * Device Configuration - FPC1500
 * R&S FPC1500 Spectrum Analyzer
 */

export default {
    type: 'fpc1500',
    name: 'Spectrum Analyzer',
    description: 'Spectrum Analyzer',
    icon: '📉',
    category: 'receiver',
    categoryLabel: 'Receiver',
    role: 'analyzer', // Analyzer device (neither calibrator nor UUC)

    // Initial state for new instances
    initialState: {
        power: true,
        centerFreq: 1.0,    // GHz
        span: 0.5,          // GHz
        refLevel: 0,        // dBm
        inputBuffer: '',
    },
};
