/**
 * ComplianceBadge.jsx
 * Reusable compliance status badge component for uncertainty mode
 */

import './ComplianceBadge.css';

const COMPLIANCE_CONFIG = {
    compliance: { label: '✅ PASS', className: 'compliance' },
    non_compliance: { label: '⚠️ FAIL', className: 'non-compliance' },
    out_of_tolerance: { label: '❌ OOT', className: 'out-of-tolerance' }
};

function ComplianceBadge({ status, visible = true }) {
    if (!visible || !status || !COMPLIANCE_CONFIG[status]) {
        return null;
    }

    const config = COMPLIANCE_CONFIG[status];

    return (
        <div className={`compliance-badge ${config.className}`}>
            {config.label}
        </div>
    );
}

export default ComplianceBadge;
