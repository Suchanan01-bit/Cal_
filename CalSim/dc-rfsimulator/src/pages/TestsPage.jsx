/**
 * TestsPage.jsx
 * Page displaying all available tests with Google Form links
 */

import './TestsPage.css';

function TestsPage({ onNavigate }) {
    const tests = [
        {
            id: 1,
            title: 'แบบทดสอบ Resolution Uncertainty',
            description: 'ทดสอบความรู้เกี่ยวกับการคำนวณ Resolution Uncertainty และหลักการวิเคราะห์ความไม่แน่นอน',
            formUrl: 'https://docs.google.com/forms/d/e/1FAIpQLSfpRNCK7trv98K0YVg-MfnV0Ha6Ay2Dx_l4TWuQRRVSULak2A/viewform?usp=dialog',
            lastUpdated: '23 ม.ค. 2569',
            duration: '15 นาที',
            questions: 10,
            icon: '🔬'
        },
        {
            id: 2,
            title: 'แบบทดสอบ Loading Error',
            description: 'ทดสอบความรู้เกี่ยวกับการคำนวณ Loading Error และผลกระทบต่อการวัด',
            formUrl: 'https://docs.google.com/forms/d/e/1FAIpQLSd5MszSrIAq6g7ho7XKIds3XY2ZMqHyRaNGKWZ3XhNCIX3arw/viewform?usp=dialog',
            lastUpdated: '23 ม.ค. 2569',
            duration: '15 นาที',
            questions: 10,
            icon: '⚖️'
        },
        {
            id: 3,
            title: 'แบบทดสอบ Instrument Error',
            description: 'ทดสอบความรู้เกี่ยวกับการคำนวณ Instrument Error และความคลาดเคลื่อนของเครื่องมือวัด',
            formUrl: 'https://docs.google.com/forms/d/e/1FAIpQLSc2HhonfIhq5XyQ5z3QprG_uTispcPUFjybCx06yCmG_jZKXA/viewform?usp=dialog',
            lastUpdated: '23 ม.ค. 2569',
            duration: '15 นาที',
            questions: 10,
            icon: '🔧'
        }
    ];

    return (
        <div className="tests-container">
            {/* Background Effects */}
            <div className="tests-bg-pattern"></div>
            <div className="tests-grid-overlay"></div>

            <div className="tests-content-wrapper">
                {/* Navigation */}
                <nav className="tests-nav">
                    <a href="#" className="logo" onClick={(e) => { e.preventDefault(); onNavigate(); }}>
                        <div className="logo-icon">📡</div>
                        <div className="logo-text">
                            <span>RF-LF</span> Simulator
                        </div>
                    </a>
                    <button className="back-btn" onClick={onNavigate}>
                        ← กลับหน้าหลัก
                    </button>
                </nav>

                {/* Header */}
                <header className="tests-header">
                    <div className="tests-badge">
                        <span className="badge-dot"></span>
                        Calibration Tests
                    </div>
                    <h1>แบบทดสอบ</h1>
                    <p className="tests-subtitle">
                        เลือกทำแบบทดสอบเพื่อประเมินความรู้ความเข้าใจในการใช้งานเครื่องมือสอบเทียบ
                    </p>
                </header>

                {/* Tests Grid */}
                <section className="tests-grid">
                    {tests.map(test => (
                        <div key={test.id} className="test-card">
                            <div className="test-icon">{test.icon}</div>
                            <h3 className="test-title">{test.title}</h3>
                            <p className="test-description">{test.description}</p>

                            <div className="test-meta">
                                <div className="meta-item">
                                    <span className="meta-icon">⏱️</span>
                                    <span>{test.duration}</span>
                                </div>
                                <div className="meta-item">
                                    <span className="meta-icon">❓</span>
                                    <span>{test.questions} ข้อ</span>
                                </div>
                            </div>

                            <div className="test-footer">
                                <span className="test-date">อัพเดท: {test.lastUpdated}</span>
                                <a
                                    href={test.formUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="test-btn"
                                >
                                    เริ่มทำแบบทดสอบ →
                                </a>
                            </div>
                        </div>
                    ))}
                </section>

                {/* Footer */}
                <footer className="tests-footer">
                    <p>© 2024 RF-LF Signal Simulator | Calibration Training Platform</p>
                </footer>
            </div>
        </div>
    );
}

export default TestsPage;
