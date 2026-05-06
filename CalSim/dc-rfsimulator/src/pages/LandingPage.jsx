/**
 * LandingPage.jsx
 * Landing page with hero section and navigation to simulator
 */

import './LandingPage.css';

function LandingPage({ onNavigate, onNavigateTests }) {
    return (
        <div className="landing-container">
            {/* Background Effects */}
            <div className="bg-pattern"></div>
            <div className="grid-overlay"></div>
            <div className="particles">
                {[...Array(9)].map((_, i) => (
                    <div key={i} className="particle"></div>
                ))}
            </div>

            <div className="content-wrapper">
                {/* Navigation */}
                <nav className="landing-nav">
                    <a href="#" className="logo">
                        <div className="logo-icon">📡</div>
                        <div className="logo-text">
                            <span>RF-LF</span> Simulator
                        </div>
                    </a>
                    <ul className="nav-links">
                        <li><a href="#">หน้าแรก</a></li>
                        <li><a href="#">เกี่ยวกับ</a></li>
                        <li><a href="#">คู่มือ</a></li>
                        <li><a href="#">ติดต่อ</a></li>
                        <li>
                            <a href="#" onClick={(e) => { e.preventDefault(); onNavigateTests(); }}>
                                📝 แบบทดสอบ
                            </a>
                        </li>
                    </ul>
                </nav>

                {/* Hero Section */}
                <section className="hero">
                    <div className="hero-content">
                        <div className="badge">
                            <span className="badge-dot"></span>
                            Calibration Training Platform
                        </div>

                        <h1>
                            แพลตฟอร์มจำลอง<br />
                            <span className="highlight">เครื่องมือสอบเทียบ</span>
                        </h1>

                        <p className="subtitle">
                            ฝึกฝนการใช้งานเครื่องมือ RF และ LF Signal Generator แบบเสมือนจริง
                            พร้อมระบบ Drag & Drop และการเชื่อมต่อสายสัญญาณที่ใช้งานง่าย
                        </p>

                        <div className="cta-group">
                            <button className="btn btn-primary" onClick={onNavigate}>
                                <span className="btn-icon">🚀</span>
                                เข้าสู่ Canvas Simulator
                            </button>
                            <a href="#features" className="btn btn-secondary">
                                <span className="btn-icon">📖</span>
                                ดูคุณสมบัติ
                            </a>
                        </div>
                    </div>
                </section>

                {/* Features Section */}
                <section className="features" id="features">
                    <div className="feature-card">
                        <div className="feature-icon">📡</div>
                        <h3 className="feature-title">RF Signal Generator</h3>
                    </div>

                    <div className="feature-card">
                        <div className="feature-icon">⚡</div>
                        <h3 className="feature-title">LF Calibrator</h3>
                    </div>

                    <div className="feature-card">
                        <div className="feature-icon">🔌</div>
                        <h3 className="feature-title">Wire Connection</h3>
                    </div>

                    <div className="feature-card">
                        <div className="feature-icon">💾</div>
                        <h3 className="feature-title">Save & Load</h3>
                    </div>
                </section>

                {/* Footer */}
                <footer className="landing-footer">
                    <p>© 2024 RF-LF Signal Simulator | Calibration Training Platform</p>
                </footer>
            </div>
        </div>
    );
}

export default LandingPage;
