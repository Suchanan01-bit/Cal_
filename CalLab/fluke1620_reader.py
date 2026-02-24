"""
Fluke 1620A "DewK" Thermo-Hygrometer Serial Reader
อ่านค่าจากเครื่อง Fluke 1620 ผ่าน RS-232 Serial Port

การเชื่อมต่อ:
- ใช้สาย 3.5mm stereo mini jack ต่อที่ช่อง RS-232 ด้านหลังเครื่อง
- Serial Settings: 9600 baud, 8 data bits, no parity, 1 stop bit
"""

import serial
import serial.tools.list_ports
from datetime import datetime
import time
import threading


class Fluke1620Reader:
    """อ่านค่าจากเครื่อง Fluke 1620A DewK ผ่าน RS-232"""
    
    # Serial settings for Fluke 1620
    BAUD_RATE = 57600
    DATA_BITS = 8
    PARITY = serial.PARITY_NONE
    STOP_BITS = serial.STOPBITS_ONE
    TIMEOUT = 2  # seconds
    
    # Fluke 1620 Commands (tested and verified)
    CMD_IDN = "*IDN?"           # Identify device -> returns "HART,1620,A63,1.10"
    CMD_READ = "READ?"          # All measurements -> "Temp1,Humidity,Temp2,Dewpoint"
    CMD_MEASURE = "MEASURE?"    # Same as READ?
    CMD_TEMP1 = "T1?"           # Temperature 1 -> "t: 23.25 C"
    CMD_TEMP2 = "T2?"           # Temperature 2 -> "t: 23.24 C"
    # Note: MEAS:TEMP1?, MEAS:TEMP2?, MEAS:HUMID?, MEAS:DEWP? do NOT work on this device
    
    def __init__(self):
        self.serial_port = None
        self.port_name = None
        self.connected = False
        self.last_error = None
        self._lock = threading.Lock()
        
    @staticmethod
    def list_available_ports():
        """รายการ COM ports ที่พร้อมใช้งาน"""
        ports = serial.tools.list_ports.comports()
        return [(p.device, p.description) for p in ports]
    
    def connect(self, port_name):
        """เชื่อมต่อกับ Fluke 1620"""
        with self._lock:
            try:
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()
                
                self.serial_port = serial.Serial(
                    port=port_name,
                    baudrate=self.BAUD_RATE,
                    bytesize=self.DATA_BITS,
                    parity=self.PARITY,
                    stopbits=self.STOP_BITS,
                    timeout=self.TIMEOUT
                )
                
                self.port_name = port_name
                self.connected = True
                self.last_error = None
                
                # Verify connection by asking for ID
                time.sleep(0.5)  # Wait for device to be ready
                idn = self._send_command(self.CMD_IDN)
                
                if idn and ("FLUKE" in idn.upper() or "HART" in idn.upper() or "1620" in idn):
                    return True, f"Connected to {idn.strip()}"
                else:
                    # May still work even if IDN doesn't return expected
                    return True, f"Connected to {port_name}"
                    
            except serial.SerialException as e:
                self.connected = False
                self.last_error = str(e)
                return False, f"Connection failed: {e}"
            except Exception as e:
                self.connected = False
                self.last_error = str(e)
                return False, f"Error: {e}"
    
    def disconnect(self):
        """ตัดการเชื่อมต่อ"""
        with self._lock:
            try:
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()
                self.connected = False
                self.port_name = None
                return True, "Disconnected"
            except Exception as e:
                return False, f"Error disconnecting: {e}"
    
    def _send_command(self, command):
        """ส่งคำสั่งและรับ response"""
        if not self.serial_port or not self.serial_port.is_open:
            return None
        
        try:
            # Clear buffers
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            # Send command with carriage return
            cmd_bytes = (command + "\r").encode('ascii')
            self.serial_port.write(cmd_bytes)
            self.serial_port.flush()
            
            # Read response (terminated by carriage return)
            response = self.serial_port.readline().decode('ascii').strip()
            return response
            
        except Exception as e:
            self.last_error = str(e)
            return None
    
    def read_temperature1(self):
        """อ่านค่าอุณหภูมิ Probe 1 (uses T1? command)"""
        with self._lock:
            response = self._send_command(self.CMD_TEMP1)
            return self._parse_temp_response(response)
    
    def read_temperature2(self):
        """อ่านค่าอุณหภูมิ Probe 2 (uses T2? command)"""
        with self._lock:
            response = self._send_command(self.CMD_TEMP2)
            return self._parse_temp_response(response)
    
    def _parse_temp_response(self, response):
        """แปลง response จาก T1?/T2? เป็นค่าตัวเลข (format: 't: 23.25 C')"""
        if response is None:
            return None
        try:
            # Response format: "t: 23.25 C"
            if 't:' in response.lower():
                value_str = response.lower().replace('t:', '').replace('c', '').strip()
                return float(value_str)
            return float(response.strip())
        except (ValueError, IndexError) as e:
            self.last_error = f"Could not parse temp: {response}"
            return None
    
    def read_all(self):
        """อ่านค่าทั้งหมดด้วยคำสั่ง READ? (returns Temp1,Humidity,Temp2,Dewpoint)"""
        with self._lock:
            response = self._send_command(self.CMD_READ)
            return self._parse_read_response(response)
    
    def _parse_read_response(self, response):
        """แปลง response จาก READ? เป็น dictionary"""
        result = {
            'datetime': datetime.now(),
            'temperature1': None,
            'temperature2': None,
            'humidity': None,
            'dewpoint': None
        }
        
        if response is None:
            return result
        
        try:
            # Response format: "23.30,49.39,21.72,53.45"
            # Order: Temp1, Humidity, Temp2, Dewpoint (based on test results)
            values = response.split(',')
            if len(values) >= 4:
                result['temperature1'] = float(values[0].strip())
                result['humidity'] = float(values[1].strip())
                result['temperature2'] = float(values[2].strip())
                result['dewpoint'] = float(values[3].strip())
            elif len(values) >= 2:
                result['temperature1'] = float(values[0].strip())
                result['humidity'] = float(values[1].strip())
        except (ValueError, IndexError) as e:
            self.last_error = f"Could not parse: {response}"
        
        return result
    
    def is_connected(self):
        """ตรวจสอบสถานะการเชื่อมต่อ"""
        return self.connected and self.serial_port and self.serial_port.is_open
    
    def get_device_info(self):
        """ดึงข้อมูลเครื่อง"""
        with self._lock:
            if not self.is_connected():
                return None
            return self._send_command(self.CMD_IDN)


# ===== TEST / DEMO =====
if __name__ == "__main__":
    print("Fluke 1620A DewK Reader - Test Mode")
    print("=" * 40)
    
    reader = Fluke1620Reader()
    
    # List available ports
    print("\nAvailable COM ports:")
    ports = reader.list_available_ports()
    if not ports:
        print("  No COM ports found!")
    else:
        for i, (port, desc) in enumerate(ports):
            print(f"  [{i+1}] {port}: {desc}")
    
    # Demo: Try to connect to first port
    if ports:
        port = ports[0][0]
        print(f"\nTrying to connect to {port}...")
        success, msg = reader.connect(port)
        print(f"  Result: {msg}")
        
        if success:
            print("\nReading values...")
            data = reader.read_all()
            print(f"  Temperature 1: {data['temperature1']}")
            print(f"  Temperature 2: {data['temperature2']}")
            print(f"  Humidity: {data['humidity']}")
            print(f"  Dewpoint: {data['dewpoint']}")
            
            reader.disconnect()
            print("\nDisconnected.")
