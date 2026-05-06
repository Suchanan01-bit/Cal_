/**
 * OscilloscopeCalibrator Device Package
 * Oscilloscope Calibrator for precise signal generation
 */

import OscilloscopeCalibrator from './OscilloscopeCalibrator';

// Device Configuration
export const config = {
    type: 'oscilloscope-calibrator',
    name: 'Oscilloscope Calibrator',
    description: 'Precision Oscilloscope Calibrator',
    icon: '📊',
    category: 'transmitter',
    categoryLabel: 'Transmitter',
    role: 'calibrator',

    // Initial state for new instances
    initialState: {
        power: true,
        output: false,              // Output ON/OFF
        waveform: 'Square',         // Square, Sine, Triangle, Pulse
        frequency: 1000,            // Hz
        amplitude: 1,               // Vpp
        offset: 0,                  // V DC offset
        dutyCycle: 50,              // % (for square/pulse)
        riseTime: 1,                // ns (for fast edge)
        impedance: '50Ω',           // 50Ω or 1MΩ
        attenuation: '1X',          // 1X, 10X
        marker: false,              // Marker output
        levelingMode: 'PEAK',       // PEAK, RMS
    },
};

// Export component as default
export default OscilloscopeCalibrator;
