/**
 * useUncertaintyMode.js
 * Custom hook for uncertainty mode functionality
 * Provides value fluctuation and compliance status for receivers
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useSimulator } from '../../context/SimulatorContext';

// Compliance status display config
export const COMPLIANCE_CONFIG = {
    compliance: { label: '✅ PASS', className: 'compliance' },
    non_compliance: { label: '⚠️ FAIL', className: 'non-compliance' },
    out_of_tolerance: { label: '❌ OOT', className: 'out-of-tolerance' }
};

/**
 * Custom hook for uncertainty mode value fluctuation
 * @param {number} baseValue - The actual measured value
 * @param {number} tolerance - Tolerance percentage (e.g., 0.01 for 1%)
 * @param {string} complianceStatus - Compliance status from device state
 * @param {boolean} isActive - Whether the value is actively being measured
 * @returns {object} - { displayValue, complianceInfo, isFluctuating }
 */
export function useUncertaintyMode(baseValue, tolerance = 0.01, complianceStatus = null, isActive = true, updateInterval = 333) {
    const { uncertaintyMode } = useSimulator();
    const [fluctuatingValue, setFluctuatingValue] = useState(null);
    const fluctuationIntervalRef = useRef(null);

    // Calculate actual tolerance based on compliance status
    const getEffectiveTolerance = useCallback(() => {
        if (complianceStatus === 'out_of_tolerance') {
            return tolerance * 10; // Much larger fluctuation for OOT
        } else if (complianceStatus === 'non_compliance') {
            return tolerance * 3; // Larger fluctuation for non-compliance
        }
        return tolerance;
    }, [tolerance, complianceStatus]);

    // Uncertainty mode value fluctuation
    useEffect(() => {
        if (uncertaintyMode && isActive && baseValue !== null && baseValue !== undefined) {
            // Clear existing interval
            if (fluctuationIntervalRef.current) {
                clearInterval(fluctuationIntervalRef.current);
            }

            // Start fluctuation
            const updateFluctuation = () => {
                const effectiveTolerance = getEffectiveTolerance();
                const maxVariation = Math.abs(baseValue) * (effectiveTolerance / 100);
                const randomOffset = (Math.random() - 0.5) * 2 * maxVariation;

                // Add minimum noise for very small values
                const minNoise = Math.abs(baseValue) * 0.0001 || 0.0001;
                const totalOffset = randomOffset + (Math.random() - 0.5) * minNoise;

                setFluctuatingValue(baseValue + totalOffset);
            };

            updateFluctuation(); // Initial value
            fluctuationIntervalRef.current = setInterval(updateFluctuation, updateInterval);

            return () => {
                if (fluctuationIntervalRef.current) {
                    clearInterval(fluctuationIntervalRef.current);
                }
            };
        } else {
            // Clear fluctuation when uncertainty mode is off
            setFluctuatingValue(null);
            if (fluctuationIntervalRef.current) {
                clearInterval(fluctuationIntervalRef.current);
            }
        }
    }, [uncertaintyMode, isActive, baseValue, getEffectiveTolerance, updateInterval]);

    // Get compliance status config
    const complianceInfo = complianceStatus ? COMPLIANCE_CONFIG[complianceStatus] : null;

    // Determine display value - use fluctuating value if uncertainty mode is active
    const displayValue = (uncertaintyMode && fluctuatingValue !== null) ? fluctuatingValue : baseValue;

    return {
        displayValue,
        complianceInfo,
        isFluctuating: uncertaintyMode && isActive && fluctuatingValue !== null,
        uncertaintyMode
    };
}

export default useUncertaintyMode;
