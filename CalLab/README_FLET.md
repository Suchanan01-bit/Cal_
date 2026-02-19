# Measurement Tools Hub - Flet Edition 🚀

A **modern, beautiful** measurement instruments control hub built with **Flet** (Flutter for Python).

## ✨ Features

### 🎨 **Stunning Modern UI**
- Material Design 3 components
- Smooth animations and transitions
- Responsive layout
- Light/Dark theme support
- Beautiful gradient cards

### 🔧 **Supported Instruments**
1. **Universal Counter** - High-precision frequency measurements
2. **Digital Multimeter** - Versatile voltage, current, resistance measurements
3. **HP 3458A Multimeter** - 8.5-digit precision for calibration labs

### 📊 **Capabilities**
- Real-time measurement display
- Live statistics (Average, Standard Deviation)
- Progress tracking
- CSV data export
- Auto-save functionality

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python measurement_hub_flet.py
```

## 📸 Screenshots

### Home Dashboard
Beautiful instrument cards with quick access to all tools.

### Instrument Control
Modern interface with:
- VISA resource selection
- Real-time measurements
- Live statistics
- Progress indicators

## 🎯 Why Flet?

### **Advantages over PyQt:**
- ✅ **Modern UI** - Material Design out of the box
- ✅ **Cross-platform** - Desktop, Web, Mobile from same code
- ✅ **Beautiful** - Stunning UI with minimal code
- ✅ **Fast Development** - Less code, more features
- ✅ **Responsive** - Adaptive layouts automatically
- ✅ **Animations** - Smooth transitions built-in

### **Comparison:**

| Feature | PyQt6 | Flet |
|---------|-------|------|
| UI Design | Manual styling | Material Design |
| Code Lines | ~800 lines | ~600 lines |
| Animations | Custom CSS | Built-in |
| Responsive | Manual | Automatic |
| Theme Support | Custom | Built-in |
| Learning Curve | Steep | Gentle |

## 🔌 Hardware Requirements

- VISA-compatible measurement instruments
- USB/GPIB/Ethernet connection
- NI-VISA or PyVISA-py backend

## 📝 Usage Guide

### Connecting to Instrument

1. Click **Refresh** to scan for available VISA resources
2. Select your instrument from dropdown
3. Click **Connect**
4. Wait for confirmation message

### Taking Measurements

1. Set **Number of Measurements**
2. Click **Start Measurement**
3. Watch real-time results
4. Click **Save to CSV** when complete

### Viewing Statistics

- **Current Value**: Large display shows latest reading
- **Average**: Mean of all measurements
- **Std Dev**: Standard deviation
- **Count**: Total measurements taken

## 🎨 Customization

### Changing Theme

Go to **Settings** → **Appearance** and select:
- Light Mode
- Dark Mode
- System Default

### Color Scheme

Edit `measurement_hub_flet.py` and modify the `colors` dictionary:

```python
self.colors = {
    'primary': '#2196F3',      # Blue
    'accent': '#FF9800',       # Orange
    'success': '#4CAF50',      # Green
    'error': '#F44336',        # Red
    ...
}
```

## 🔧 Development

### Project Structure

```
Cal-Lab/
├── measurement_hub_flet.py      # Main Flet application
├── measurement_tools_hub.py     # Legacy PyQt6 version
├── multimeter_gui.py            # PyQt6 multimeter
├── multimeter_3458_gui.py       # PyQt6 HP 3458A
├── universal_counter_gui.py     # PyQt6 counter
└── requirements.txt             # Dependencies
```

### Adding New Instruments

1. Create new view method in `MeasurementHub` class
2. Add navigation destination to `nav_rail`
3. Implement VISA commands for your instrument
4. Add instrument card to home view

## 🐛 Troubleshooting

### "No VISA resources found"
- Check instrument is powered on
- Verify USB/GPIB connection
- Install NI-VISA or use PyVISA-py

### "Connection failed"
- Verify correct VISA address
- Check instrument settings
- Try different VISA backend

### "Module not found: flet"
```bash
pip install flet
```

## 📚 Resources

- [Flet Documentation](https://flet.dev)
- [PyVISA Documentation](https://pyvisa.readthedocs.io)
- [Material Design 3](https://m3.material.io)

## 🎓 Migration from PyQt6

Both versions are included:
- **Legacy**: `measurement_tools_hub.py` (PyQt6)
- **Modern**: `measurement_hub_flet.py` (Flet)

You can run both side-by-side during transition.

## 📄 License

© 2026 Cal-Lab

## 🙏 Acknowledgments

- Built with [Flet](https://flet.dev) by Google
- Powered by [PyVISA](https://pyvisa.readthedocs.io)
- Icons from Material Design

---

**Enjoy your beautiful, modern measurement tools! 🎉**
