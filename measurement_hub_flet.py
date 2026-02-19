"""
Measurement Tools Hub - Flet Version
A modern, beautiful GUI hub for controlling multiple measurement instruments
Built with Flet (Flutter for Python) for stunning UI/UX
"""

import flet as ft
import pyvisa
import csv
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


class MeasurementHub:
    """Main application class for Measurement Tools Hub"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Measurement Tools Hub"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.window_width = 1400
        self.page.window_height = 900
        
        # Application state
        self.current_view = "home"
        self.rm: Optional[pyvisa.ResourceManager] = None
        self.instrument = None
        self.measurements: List[float] = []
        self.is_measuring = False
        
        # Initialize PyVISA
        self.init_visa()
        
        # Setup theme
        self.setup_theme()
        
        # Build UI
        self.build_ui()
    
    def setup_theme(self):
        """Configure custom theme with beautiful colors"""
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.colors.BLUE,
            visual_density=ft.ThemeVisualDensity.COMFORTABLE,
        )
        
        # Custom color palette
        self.colors = {
            'primary': '#2196F3',
            'primary_dark': '#1976D2',
            'accent': '#FF9800',
            'success': '#4CAF50',
            'error': '#F44336',
            'warning': '#FFC107',
            'background': '#F5F7FA',
            'surface': '#FFFFFF',
            'text_primary': '#212121',
            'text_secondary': '#757575',
        }
    
    def init_visa(self):
        """Initialize PyVISA resource manager"""
        try:
            self.rm = pyvisa.ResourceManager()
        except Exception as e:
            print(f"Failed to initialize PyVISA: {e}")
    
    def build_ui(self):
        """Build the main user interface"""
        # Create navigation rail
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.HOME_OUTLINED,
                    selected_icon=ft.icons.HOME,
                    label="Home",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SPEED_OUTLINED,
                    selected_icon=ft.icons.SPEED,
                    label="Counter",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.ELECTRICAL_SERVICES_OUTLINED,
                    selected_icon=ft.icons.ELECTRICAL_SERVICES,
                    label="Multimeter",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.PRECISION_MANUFACTURING_OUTLINED,
                    selected_icon=ft.icons.PRECISION_MANUFACTURING,
                    label="HP 3458A",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SETTINGS_OUTLINED,
                    selected_icon=ft.icons.SETTINGS,
                    label="Settings",
                ),
            ],
            on_change=self.on_nav_change,
            bgcolor=ft.colors.SURFACE_VARIANT,
        )
        
        # Create content area
        self.content_area = ft.Container(
            content=self.create_home_view(),
            expand=True,
            padding=20,
            bgcolor=self.colors['background'],
        )
        
        # Main layout
        main_layout = ft.Row(
            [
                self.nav_rail,
                ft.VerticalDivider(width=1),
                self.content_area,
            ],
            expand=True,
            spacing=0,
        )
        
        self.page.add(main_layout)
    
    def on_nav_change(self, e):
        """Handle navigation rail selection changes"""
        index = e.control.selected_index
        
        if index == 0:
            self.content_area.content = self.create_home_view()
        elif index == 1:
            self.content_area.content = self.create_counter_view()
        elif index == 2:
            self.content_area.content = self.create_multimeter_view()
        elif index == 3:
            self.content_area.content = self.create_hp3458_view()
        elif index == 4:
            self.content_area.content = self.create_settings_view()
        
        self.page.update()
    
    def create_home_view(self):
        """Create the home dashboard view"""
        return ft.Column(
            [
                # Header
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Measurement Tools Hub",
                                size=32,
                                weight=ft.FontWeight.BOLD,
                                color=self.colors['text_primary'],
                            ),
                            ft.Text(
                                "Professional instrument control and data acquisition",
                                size=16,
                                color=self.colors['text_secondary'],
                            ),
                        ],
                        spacing=5,
                    ),
                    margin=ft.margin.only(bottom=30),
                ),
                
                # Instrument cards
                ft.ResponsiveRow(
                    [
                        self.create_instrument_card(
                            title="Universal Counter",
                            description="High-precision frequency and time interval measurements",
                            icon=ft.icons.SPEED,
                            color=ft.colors.BLUE,
                            index=1,
                        ),
                        self.create_instrument_card(
                            title="Digital Multimeter",
                            description="Versatile voltage, current, and resistance measurements",
                            icon=ft.icons.ELECTRICAL_SERVICES,
                            color=ft.colors.GREEN,
                            index=2,
                        ),
                        self.create_instrument_card(
                            title="HP 3458A Multimeter",
                            description="8.5-digit precision multimeter for calibration labs",
                            icon=ft.icons.PRECISION_MANUFACTURING,
                            color=ft.colors.ORANGE,
                            index=3,
                        ),
                    ],
                    spacing=20,
                    run_spacing=20,
                ),
                
                # Quick stats
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "System Status",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=self.colors['text_primary'],
                            ),
                            ft.Divider(height=20),
                            self.create_status_row(),
                        ],
                        spacing=10,
                    ),
                    margin=ft.margin.only(top=30),
                    padding=20,
                    bgcolor=self.colors['surface'],
                    border_radius=12,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=10,
                        color=ft.colors.with_opacity(0.1, ft.colors.BLACK),
                    ),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    
    def create_instrument_card(self, title: str, description: str, icon, color, index: int):
        """Create a beautiful instrument card"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Icon(icon, size=48, color=ft.colors.WHITE),
                        width=80,
                        height=80,
                        border_radius=40,
                        bgcolor=color,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        title,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=self.colors['text_primary'],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        description,
                        size=14,
                        color=self.colors['text_secondary'],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.ElevatedButton(
                        "Open",
                        icon=ft.icons.ARROW_FORWARD,
                        on_click=lambda e, idx=index: self.open_instrument(idx),
                        style=ft.ButtonStyle(
                            bgcolor=color,
                            color=ft.colors.WHITE,
                        ),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=15,
            ),
            col={"sm": 12, "md": 6, "lg": 4},
            padding=30,
            bgcolor=self.colors['surface'],
            border_radius=16,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.colors.with_opacity(0.1, ft.colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
        )
    
    def create_status_row(self):
        """Create system status indicators"""
        available_devices = []
        if self.rm:
            try:
                available_devices = self.rm.list_resources()
            except:
                pass
        
        return ft.Row(
            [
                self.create_status_chip(
                    "PyVISA",
                    "Available" if self.rm else "Not Available",
                    ft.colors.GREEN if self.rm else ft.colors.RED,
                ),
                self.create_status_chip(
                    "Devices Found",
                    str(len(available_devices)),
                    ft.colors.BLUE,
                ),
                self.create_status_chip(
                    "Active Measurements",
                    "0",
                    ft.colors.ORANGE,
                ),
            ],
            spacing=20,
            wrap=True,
        )
    
    def create_status_chip(self, label: str, value: str, color):
        """Create a status chip"""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.CIRCLE, size=12, color=color),
                    ft.Column(
                        [
                            ft.Text(label, size=12, color=self.colors['text_secondary']),
                            ft.Text(value, size=16, weight=ft.FontWeight.BOLD),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=10,
            ),
            padding=15,
            bgcolor=ft.colors.with_opacity(0.1, color),
            border_radius=8,
        )
    
    def open_instrument(self, index: int):
        """Open specific instrument view"""
        self.nav_rail.selected_index = index
        self.on_nav_change(type('obj', (object,), {'control': self.nav_rail})())
    
    def create_counter_view(self):
        """Create Universal Counter view"""
        return self.create_instrument_view(
            title="Universal Counter",
            icon=ft.icons.SPEED,
            color=ft.colors.BLUE,
            measurement_type="Frequency",
            unit="Hz",
        )
    
    def create_multimeter_view(self):
        """Create Digital Multimeter view"""
        return self.create_instrument_view(
            title="Digital Multimeter",
            icon=ft.icons.ELECTRICAL_SERVICES,
            color=ft.colors.GREEN,
            measurement_type="DC Voltage",
            unit="V",
        )
    
    def create_hp3458_view(self):
        """Create HP 3458A Multimeter view"""
        return self.create_instrument_view(
            title="HP 3458A Multimeter",
            icon=ft.icons.PRECISION_MANUFACTURING,
            color=ft.colors.ORANGE,
            measurement_type="DC Voltage (8.5 digits)",
            unit="V",
        )
    
    def create_instrument_view(self, title: str, icon, color, measurement_type: str, unit: str):
        """Create a generic instrument control view"""
        
        # Connection section
        resource_dropdown = ft.Dropdown(
            label="VISA Resource",
            hint_text="Select instrument",
            options=[],
            width=400,
        )
        
        # Populate resources
        if self.rm:
            try:
                resources = self.rm.list_resources()
                resource_dropdown.options = [
                    ft.dropdown.Option(res) for res in resources
                ]
            except:
                pass
        
        refresh_btn = ft.IconButton(
            icon=ft.icons.REFRESH,
            tooltip="Refresh resources",
            on_click=lambda e: self.refresh_resources(resource_dropdown),
        )
        
        connect_btn = ft.ElevatedButton(
            "Connect",
            icon=ft.icons.LINK,
            on_click=lambda e: self.connect_instrument(resource_dropdown.value),
            style=ft.ButtonStyle(bgcolor=color),
        )
        
        # Measurement settings
        num_measurements = ft.TextField(
            label="Number of Measurements",
            value="10",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        # Results display
        results_text = ft.Text(
            "No measurements yet",
            size=48,
            weight=ft.FontWeight.BOLD,
            color=color,
        )
        
        stats_text = ft.Text(
            "",
            size=14,
            color=self.colors['text_secondary'],
        )
        
        # Progress
        progress_bar = ft.ProgressBar(
            width=400,
            value=0,
            visible=False,
        )
        
        # Control buttons
        start_btn = ft.ElevatedButton(
            "Start Measurement",
            icon=ft.icons.PLAY_ARROW,
            on_click=lambda e: self.start_measurement(
                num_measurements.value,
                results_text,
                stats_text,
                progress_bar,
                start_btn,
                stop_btn,
            ),
            style=ft.ButtonStyle(bgcolor=self.colors['success']),
        )
        
        stop_btn = ft.ElevatedButton(
            "Stop",
            icon=ft.icons.STOP,
            on_click=lambda e: self.stop_measurement(),
            disabled=True,
            style=ft.ButtonStyle(bgcolor=self.colors['error']),
        )
        
        save_btn = ft.ElevatedButton(
            "Save to CSV",
            icon=ft.icons.SAVE,
            on_click=lambda e: self.save_measurements(),
        )
        
        clear_btn = ft.OutlinedButton(
            "Clear",
            icon=ft.icons.CLEAR,
            on_click=lambda e: self.clear_measurements(results_text, stats_text),
        )
        
        # Build layout
        return ft.Column(
            [
                # Header
                ft.Row(
                    [
                        ft.Icon(icon, size=40, color=color),
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"Measurement Type: {measurement_type}",
                                    size=14,
                                    color=self.colors['text_secondary'],
                                ),
                            ],
                            spacing=5,
                        ),
                    ],
                    spacing=15,
                ),
                
                ft.Divider(height=30),
                
                # Connection section
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Connection", size=18, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                [resource_dropdown, refresh_btn, connect_btn],
                                spacing=10,
                            ),
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    bgcolor=self.colors['surface'],
                    border_radius=12,
                ),
                
                # Settings section
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Measurement Settings", size=18, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                [num_measurements],
                                spacing=15,
                            ),
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    bgcolor=self.colors['surface'],
                    border_radius=12,
                    margin=ft.margin.only(top=20),
                ),
                
                # Results section
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Results", size=18, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        results_text,
                                        ft.Text(unit, size=20, color=self.colors['text_secondary']),
                                        stats_text,
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=10,
                                ),
                                alignment=ft.alignment.center,
                                padding=30,
                            ),
                            progress_bar,
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    bgcolor=self.colors['surface'],
                    border_radius=12,
                    margin=ft.margin.only(top=20),
                ),
                
                # Control buttons
                ft.Row(
                    [start_btn, stop_btn, save_btn, clear_btn],
                    spacing=15,
                    wrap=True,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    
    def create_settings_view(self):
        """Create settings view"""
        return ft.Column(
            [
                ft.Text(
                    "Settings",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=30),
                
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Appearance", size=18, weight=ft.FontWeight.BOLD),
                            ft.RadioGroup(
                                content=ft.Column([
                                    ft.Radio(value="light", label="Light Mode"),
                                    ft.Radio(value="dark", label="Dark Mode"),
                                    ft.Radio(value="system", label="System Default"),
                                ]),
                                value="light",
                                on_change=self.change_theme,
                            ),
                        ],
                        spacing=15,
                    ),
                    padding=20,
                    bgcolor=self.colors['surface'],
                    border_radius=12,
                ),
                
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("About", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text("Measurement Tools Hub v2.0"),
                            ft.Text("Built with Flet (Flutter for Python)"),
                            ft.Text("© 2026 Cal-Lab"),
                        ],
                        spacing=10,
                    ),
                    padding=20,
                    bgcolor=self.colors['surface'],
                    border_radius=12,
                    margin=ft.margin.only(top=20),
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    
    def refresh_resources(self, dropdown: ft.Dropdown):
        """Refresh VISA resources"""
        if self.rm:
            try:
                resources = self.rm.list_resources()
                dropdown.options = [ft.dropdown.Option(res) for res in resources]
                dropdown.update()
                self.show_snackbar("Resources refreshed", ft.colors.GREEN)
            except Exception as e:
                self.show_snackbar(f"Error: {e}", ft.colors.RED)
    
    def connect_instrument(self, resource: str):
        """Connect to instrument"""
        if not resource:
            self.show_snackbar("Please select a resource", ft.colors.ORANGE)
            return
        
        try:
            if self.instrument:
                self.instrument.close()
            
            self.instrument = self.rm.open_resource(resource)
            idn = self.instrument.query("*IDN?")
            self.show_snackbar(f"Connected: {idn}", ft.colors.GREEN)
        except Exception as e:
            self.show_snackbar(f"Connection failed: {e}", ft.colors.RED)
    
    def start_measurement(self, num: str, results_text, stats_text, progress_bar, start_btn, stop_btn):
        """Start measurement process"""
        if not self.instrument:
            self.show_snackbar("Please connect to an instrument first", ft.colors.ORANGE)
            return
        
        try:
            num_measurements = int(num)
        except:
            self.show_snackbar("Invalid number of measurements", ft.colors.RED)
            return
        
        self.is_measuring = True
        self.measurements = []
        progress_bar.visible = True
        start_btn.disabled = True
        stop_btn.disabled = False
        self.page.update()
        
        # Run measurement in thread
        def measure():
            for i in range(num_measurements):
                if not self.is_measuring:
                    break
                
                try:
                    # Simulate measurement (replace with actual VISA commands)
                    value = float(self.instrument.query("READ?"))
                    self.measurements.append(value)
                    
                    # Update UI
                    results_text.value = f"{value:.6f}"
                    progress_bar.value = (i + 1) / num_measurements
                    
                    if len(self.measurements) > 1:
                        avg = sum(self.measurements) / len(self.measurements)
                        std = (sum((x - avg) ** 2 for x in self.measurements) / len(self.measurements)) ** 0.5
                        stats_text.value = f"Avg: {avg:.6f} | Std: {std:.6f} | Count: {len(self.measurements)}"
                    
                    self.page.update()
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.show_snackbar(f"Measurement error: {e}", ft.colors.RED)
                    break
            
            # Finish
            self.is_measuring = False
            progress_bar.visible = False
            start_btn.disabled = False
            stop_btn.disabled = True
            self.page.update()
            self.show_snackbar("Measurement complete", ft.colors.GREEN)
        
        threading.Thread(target=measure, daemon=True).start()
    
    def stop_measurement(self):
        """Stop ongoing measurement"""
        self.is_measuring = False
        self.show_snackbar("Measurement stopped", ft.colors.ORANGE)
    
    def clear_measurements(self, results_text, stats_text):
        """Clear all measurements"""
        self.measurements = []
        results_text.value = "No measurements yet"
        stats_text.value = ""
        self.page.update()
    
    def save_measurements(self):
        """Save measurements to CSV"""
        if not self.measurements:
            self.show_snackbar("No measurements to save", ft.colors.ORANGE)
            return
        
        try:
            filename = f"measurements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = Path.cwd() / filename
            
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Measurement', 'Value'])
                for i, val in enumerate(self.measurements, 1):
                    writer.writerow([i, val])
            
            self.show_snackbar(f"Saved to {filename}", ft.colors.GREEN)
        except Exception as e:
            self.show_snackbar(f"Save failed: {e}", ft.colors.RED)
    
    def change_theme(self, e):
        """Change application theme"""
        if e.control.value == "dark":
            self.page.theme_mode = ft.ThemeMode.DARK
        elif e.control.value == "light":
            self.page.theme_mode = ft.ThemeMode.LIGHT
        else:
            self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.update()
    
    def show_snackbar(self, message: str, color):
        """Show a snackbar notification"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.colors.WHITE),
            bgcolor=color,
        )
        self.page.snack_bar.open = True
        self.page.update()


def main(page: ft.Page):
    """Main entry point"""
    MeasurementHub(page)


if __name__ == "__main__":
    ft.app(target=main)
