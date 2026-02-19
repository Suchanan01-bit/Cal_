# 🔬 Measurement Tools Hub

ศูนย์รวมเครื่องมือวัดทางห้องปฏิบัติการ - แอพพลิเคชันหลักสำหรับควบคุมเครื่องมือวัดหลายชนิด

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

## 📖 ภาพรวม

**Measurement Tools Hub** เป็นแอพพลิเคชันแบบ All-in-One สำหรับควบคุมและจัดการเครื่องมือวัดต่างๆ ในห้องปฏิบัติการ Cal-Lab ออกแบบมาให้ใช้งานง่าย มี UI สวยงาม และรวมทุกเครื่องมือไว้ในที่เดียว

## ✨ ฟีเจอร์หลัก

### 🎯 ศูนย์รวมเครื่องมือวัด 6 ชนิด:

1. **🔬 Universal Counter** ✅ พร้อมใช้งาน
   - วัดความถี่และช่วงเวลา
   - กราฟแบบ Real-time
   - บันทึกข้อมูล CSV
   - คำนวณสถิติอัตโนมัติ

2. **📟 Digital Multimeter** 🚧 กำลังพัฒนา
   - วัดแรงดัน (DC/AC)
   - วัดกระแส
   - วัดความต้านทาน
   - ทดสอบความต่อเนื่อง

3. **📊 Digital Oscilloscope** 🚧 กำลังพัฒนา
   - แสดงรูปคลื่น
   - วิเคราะห์ FFT
   - Cursor measurements
   - จับภาพหน้าจอ

4. **⚡ Programmable Power Supply** 🚧 กำลังพัฒนา
   - ควบคุมแรงดัน/กระแส
   - เปิด/ปิด Output
   - ป้องกันแรงดันเกิน
   - จำกัดกระแส

5. **🌊 Signal Generator** 🚧 กำลังพัฒนา
   - สร้างสัญญาณ (Sine, Square, Triangle)
   - ควบคุมความถี่
   - ควบคุมแอมพลิจูด
   - Modulation (AM/FM)

6. **📡 Spectrum Analyzer** 🚧 กำลังพัฒนา
   - แสดง Frequency spectrum
   - ตรวจจับจุดสูงสุด
   - Marker measurements
   - Trace averaging

## 🎨 คุณสมบัติ UI

- **🏠 Home Dashboard** - ภาพรวมเครื่องมือทั้งหมด
- **🎯 Navigation Sidebar** - เมนูด้านข้างเข้าถึงง่าย
- **📱 Responsive Design** - ปรับขนาดได้ตามหน้าจอ
- **🎨 Modern Light Theme** - ธีมสีสว่างสบายตา
- **📊 Status Bar** - แสดงสถานะปัจจุบัน
- **🔄 Smooth Transitions** - การเปลี่ยนหน้าลื่นไหล

## 📋 ความต้องการของระบบ

- **Operating System**: Windows 10/11
- **Python**: 3.8 หรือสูงกว่า
- **VISA Driver**: NI-VISA หรือ PyVISA-py

## 🚀 การติดตั้ง

### 1. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 2. ตรวจสอบไฟล์

ตรวจสอบว่ามีไฟล์ทั้งหมดในโฟลเดอร์:

```
Cal-Lab/
├── measurement_tools_hub.py      # โปรแกรมหลัก (Hub)
├── universal_counter_gui.py      # โมดูล Universal Counter
├── requirements.txt              # Dependencies
└── README_Hub.md                 # คู่มือนี้
```

## 💻 การใช้งาน

### เริ่มโปรแกรม

```bash
python measurement_tools_hub.py
```

### วิธีใช้งาน

1. **หน้า Home**
   - เมื่อเปิดโปรแกรมจะเห็นหน้า Dashboard
   - แสดงการ์ดของเครื่องมือทั้งหมด 6 ชนิด
   - คลิกที่การ์ดเพื่อเข้าใช้งานเครื่องมือนั้นๆ

2. **Navigation Sidebar**
   - ใช้เมนูด้านซ้ายเพื่อสลับระหว่างเครื่องมือ
   - ปุ่มสีเทา = ยังไม่พร้อมใช้งาน
   - ปุ่มสีขาว = พร้อมใช้งาน

3. **Universal Counter**
   - คลิกที่การ์ด "Universal Counter" หรือเมนูด้านซ้าย
   - ใช้งานได้เต็มรูปแบบตามคู่มือ Universal Counter

4. **เครื่องมืออื่นๆ**
   - ยังอยู่ระหว่างพัฒนา
   - จะแสดงข้อความ "Under Development"

## 📸 ภาพหน้าจอ

### หน้า Home Dashboard
- แสดงการ์ดเครื่องมือทั้งหมด
- สถิติโดยรวม
- สถานะความพร้อมใช้งาน

### หน้า Universal Counter
- UI เต็มรูปแบบของ Universal Counter
- รวมอยู่ในแอพหลักแล้ว

## 🎯 โครงสร้างโปรแกรม

```
MeasurementToolsHub (Main Window)
│
├── Header (Title Bar)
│
├── Sidebar (Navigation)
│   ├── Home
│   ├── Universal Counter ✅
│   ├── Multimeter 🚧
│   ├── Oscilloscope 🚧
│   ├── Power Supply 🚧
│   ├── Signal Generator 🚧
│   ├── Spectrum Analyzer 🚧
│   └── About
│
├── Content Area (Stacked Widget)
│   ├── Home Page (Dashboard)
│   ├── Universal Counter Widget
│   ├── Multimeter Widget
│   ├── Oscilloscope Widget
│   ├── Power Supply Widget
│   ├── Signal Generator Widget
│   └── Spectrum Analyzer Widget
│
└── Status Bar
```

## 🔧 การพัฒนาต่อ

### เพิ่มเครื่องมือใหม่

1. สร้างคลาส Widget ใหม่:
```python
class NewInstrumentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # สร้าง UI ของเครื่องมือ
        pass
```

2. เพิ่มใน `MeasurementToolsHub.__init__()`:
```python
self.new_instrument = NewInstrumentWidget()
self.stacked_widget.addWidget(self.new_instrument)
```

3. เพิ่มปุ่มใน Sidebar

### แก้ไขธีม

แก้ไขฟังก์ชัน `set_light_theme()` หรือสร้าง `set_dark_theme()` ใหม่

## 📊 สถานะการพัฒนา

| เครื่องมือ | สถานะ | ความสมบูรณ์ |
|-----------|-------|-------------|
| Universal Counter | ✅ เสร็จสมบูรณ์ | 100% |
| Digital Multimeter | 🚧 กำลังพัฒนา | 0% |
| Oscilloscope | 🚧 กำลังพัฒนา | 0% |
| Power Supply | 🚧 กำลังพัฒนา | 0% |
| Signal Generator | 🚧 กำลังพัฒนา | 0% |
| Spectrum Analyzer | 🚧 กำลังพัฒนา | 0% |

## 🆘 การแก้ปัญหา

### Universal Counter ไม่แสดง

1. ตรวจสอบว่ามีไฟล์ `universal_counter_gui.py` ในโฟลเดอร์เดียวกัน
2. ตรวจสอบว่าติดตั้ง dependencies ครบ

### Import Error

```bash
pip install --upgrade PyQt6 pyvisa pyvisa-py matplotlib
```

### หน้าจอแสดงผลไม่ถูกต้อง

- ลองปรับขนาดหน้าต่าง
- รีสตาร์ทโปรแกรม

## 💡 เคล็ดลับการใช้งาน

1. **ใช้ Sidebar** - เข้าถึงเครื่องมือได้เร็วกว่าคลิกการ์ด
2. **ดู Status Bar** - แสดงข้อมูลเครื่องมือที่กำลังใช้งาน
3. **Home Button** - กดเพื่อกลับหน้าหลักได้ทุกเมื่อ
4. **About** - ดูข้อมูลเวอร์ชันและ dependencies

## 🎓 การใช้งานขั้นสูง

### รันแบบ Standalone

แต่ละโมดูลสามารถรันแยกได้:

```bash
# รัน Universal Counter แยก
python universal_counter_gui.py

# รัน Hub ทั้งหมด
python measurement_tools_hub.py
```

### Integration กับระบบอื่น

โปรแกรมออกแบบให้ขยายได้ง่าย สามารถ import เป็น module:

```python
from measurement_tools_hub import MeasurementToolsHub
from universal_counter_gui import UniversalCounterGUI
```

## 📞 การสนับสนุน

หากพบปัญหาหรือต้องการความช่วยเหลือ:
- ตรวจสอบ Status Bar ด้านล่าง
- อ่านคู่มือของแต่ละเครื่องมือ
- ตรวจสอบ error message ในคอนโซล

## 🔮 แผนการพัฒนาในอนาคต

- [ ] เพิ่ม Digital Multimeter module
- [ ] เพิ่ม Oscilloscope module
- [ ] เพิ่ม Power Supply module
- [ ] เพิ่ม Signal Generator module
- [ ] เพิ่ม Spectrum Analyzer module
- [ ] เพิ่มระบบ User Preferences
- [ ] เพิ่มการบันทึก Session
- [ ] เพิ่ม Dark Theme Toggle
- [ ] เพิ่มการ Export รายงาน PDF
- [ ] เพิ่มการเชื่อมต่อหลายเครื่องพร้อมกัน

## 📄 License

MIT License - ใช้งานได้อย่างอิสระ

## 👨‍💻 ผู้พัฒนา

**Cal-Lab Team**  
Powered by Antigravity AI Assistant

---

**เวอร์ชัน**: 1.0.0  
**วันที่สร้าง**: 2026-01-12  
**อัพเดทล่าสุด**: 2026-01-12

---

## 🌟 ขอบคุณที่ใช้งาน Measurement Tools Hub!

หากต้องการพัฒนาเครื่องมือเพิ่มเติมหรือปรับแต่งโปรแกรม ติดต่อได้ทุกเมื่อ! 🚀
