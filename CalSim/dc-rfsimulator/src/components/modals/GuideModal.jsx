/**
 * GuideModal.jsx
 * Usage guide modal
 */

import './GuideModal.css';

function GuideModal({ onClose }) {
    return (
        <div className="guide-modal" onClick={onClose}>
            <div className="guide-content" onClick={(e) => e.stopPropagation()}>
                <div className="guide-header">
                    <h2>📖 คู่มือการใช้งาน</h2>
                    <button className="guide-close" onClick={onClose}>×</button>
                </div>

                <div className="guide-body">
                    <div className="guide-section">
                        <h3>🎯 เริ่มต้นใช้งาน</h3>
                        <ol>
                            <li><strong>ลาก Component</strong> - ลากเครื่องมือจาก Sidebar ไปวางบน Canvas</li>
                            <li><strong>ต่อสาย</strong> - คลิกจุดสีแดง (Output) แล้วคลิกจุดสีเขียว (Input)</li>
                            <li><strong>เปิดเครื่อง</strong> - กดปุ่ม Power ก่อนใช้งาน</li>
                            <li><strong>ตั้งค่า</strong> - ใช้ Keypad หรือคลิกที่หน้าจอ</li>
                        </ol>
                    </div>

                    <div className="guide-section">
                        <h3>🔌 การเชื่อมต่อ</h3>
                        <ul>
                            <li><span className="dot red"></span> <strong>จุดแดง (Output)</strong> - ส่งสัญญาณออก</li>
                            <li><span className="dot green"></span> <strong>จุดเขียว (Input)</strong> - รับสัญญาณเข้า</li>
                        </ul>
                    </div>

                    <div className="guide-section">
                        <h3>⌨️ Keyboard Shortcuts</h3>
                        <ul>
                            <li><kbd>Delete</kbd> - ลบ Component ที่เลือก</li>
                            <li><kbd>Escape</kbd> - ยกเลิกการเชื่อมต่อ</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default GuideModal;
