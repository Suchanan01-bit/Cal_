/**
 * deviceRegistry.js
 * Centralized Device Registry for dynamic device loading
 * 
 * This registry automatically loads device configurations and components,
 * eliminating the need for hardcoded switch statements.
 */

// ===== RF Devices =====
import SMA100A, { config as sma100aConfig } from '../components/devices/RF/SMA100A';
import FPC1500, { config as fpc1500Config } from '../components/devices/RF/FPC1500';

// ===== LF Devices =====
import Fluke5500A, { config as fluke5500aConfig } from '../components/devices/LF/Fluke5500A';
import Fluke5522A, { config as fluke5522aConfig } from '../components/devices/LF/Fluke5522A';
import Multimeter, { config as multimeterConfig } from '../components/devices/LF/Multimeter';
import U3606A, { config as u3606aConfig } from '../components/devices/LF/U3606A';
import AnalogMultimeter, { config as analogMultimeterConfig } from '../components/devices/LF/AnalogMultimeter';
import ClampMeter, { config as clampMeterConfig } from '../components/devices/LF/ClampMeter';
import LightSource, { config as lightSourceConfig } from '../components/devices/LF/LightSource';
import Oscilloscope, { config as oscilloscopeConfig } from '../components/devices/LF/Oscilloscope';
import OscilloscopeCalibrator, { config as oscCalibratorConfig } from '../components/devices/LF/OscilloscopeCalibrator';

// ===== Placeholder Device =====
import PlaceholderDevice from '../components/devices/PlaceholderDevice';

/**
 * All device configurations indexed by type
 */
export const DEVICES = {
    [sma100aConfig.type]: sma100aConfig,
    [fpc1500Config.type]: fpc1500Config,
    [fluke5500aConfig.type]: fluke5500aConfig,
    [fluke5522aConfig.type]: fluke5522aConfig,
    [multimeterConfig.type]: multimeterConfig,
    [u3606aConfig.type]: u3606aConfig,
    [analogMultimeterConfig.type]: analogMultimeterConfig,
    [clampMeterConfig.type]: clampMeterConfig,
    [lightSourceConfig.type]: lightSourceConfig,
    [oscilloscopeConfig.type]: oscilloscopeConfig,
    [oscCalibratorConfig.type]: oscCalibratorConfig,
};

/**
 * All device React components indexed by type
 */
export const DEVICE_COMPONENTS = {
    [sma100aConfig.type]: SMA100A,
    [fpc1500Config.type]: FPC1500,
    [fluke5500aConfig.type]: Fluke5500A,
    [fluke5522aConfig.type]: Fluke5522A,
    [multimeterConfig.type]: Multimeter,
    [u3606aConfig.type]: U3606A,
    [analogMultimeterConfig.type]: AnalogMultimeter,
    [clampMeterConfig.type]: ClampMeter,
    [lightSourceConfig.type]: LightSource,
    [oscilloscopeConfig.type]: Oscilloscope,
    [oscCalibratorConfig.type]: OscilloscopeCalibrator,
};

/**
 * Get devices grouped by category for sidebar
 * @returns {Object} Devices grouped by category { rf: [...], lf: [...] }
 */
export function getDevicesByCategory() {
    const categories = {};

    Object.values(DEVICES).forEach(device => {
        const category = device.category;
        if (!categories[category]) {
            categories[category] = {
                label: device.categoryLabel,
                devices: []
            };
        }
        categories[category].devices.push({
            type: device.type,
            name: device.name,
            description: device.description,
            icon: device.icon,
        });
    });

    return categories;
}

/**
 * Get initial state for a device type
 * @param {string} type - Device type
 * @returns {Object} Initial state for the device
 */
export function getInitialState(type) {
    const config = DEVICES[type];
    if (config && config.initialState) {
        return { ...config.initialState };
    }
    return { power: false };
}

/**
 * Get React component for a device type
 * @param {string} type - Device type
 * @returns {React.Component} Device component or PlaceholderDevice
 */
export function getDeviceComponent(type) {
    return DEVICE_COMPONENTS[type] || PlaceholderDevice;
}

/**
 * Get device configuration by type
 * @param {string} type - Device type
 * @returns {Object|null} Device configuration
 */
export function getDeviceConfig(type) {
    return DEVICES[type] || null;
}

/**
 * Check if a device type is a calibrator (output device)
 * @param {string} type - Device type
 * @returns {boolean}
 */
export function isCalibrator(type) {
    const config = DEVICES[type];
    return config && config.role === 'calibrator';
}

/**
 * Check if a device type is a UUC (input device)
 * @param {string} type - Device type
 * @returns {boolean}
 */
export function isUUC(type) {
    const config = DEVICES[type];
    return config && config.role === 'uuc';
}

/**
 * Get all calibrator device types
 * @returns {string[]} Array of calibrator type names
 */
export function getCalibratorTypes() {
    return Object.values(DEVICES)
        .filter(d => d.role === 'calibrator')
        .map(d => d.type);
}

/**
 * Get all UUC device types
 * @returns {string[]} Array of UUC type names
 */
export function getUUCTypes() {
    return Object.values(DEVICES)
        .filter(d => d.role === 'uuc')
        .map(d => d.type);
}

export default {
    DEVICES,
    DEVICE_COMPONENTS,
    getDevicesByCategory,
    getInitialState,
    getDeviceComponent,
    getDeviceConfig,
    isCalibrator,
    isUUC,
    getCalibratorTypes,
    getUUCTypes,
};
