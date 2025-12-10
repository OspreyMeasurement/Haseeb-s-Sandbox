import customtkinter as ctk
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class OspreyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Osprey Production Suite v1.0")
        self.geometry("1200x800")
        
        # Grid Layout (1 row, 2 cols)
        # Col 0 = Navigation Sidebar (Fixed width)
        # Col 1 = Main Content (Expands)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 1. SIDEBAR NAVIGATION ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Logo / Title
        self.logo_label = ctk.CTkLabel(self.sidebar, text="OSPREY\nMEASUREMENT", font=("Roboto", 24, "bold"))
        self.logo_label.pack(pady=30)

        # Nav Buttons
        self.btn_home = self.create_nav_button("🏠  Home / Load", self.show_home)
        self.btn_build = self.create_nav_button("✂️  Build Wizard", self.show_build)
        self.btn_config = self.create_nav_button("🔌  Configurator", self.show_config)
        self.btn_report = self.create_nav_button("📄  Reports", self.show_report)

        # Status Footer
        self.status_label = ctk.CTkLabel(self.sidebar, text="System Ready", text_color="gray")
        self.status_label.pack(side="bottom", pady=20)

        # --- 2. MAIN CONTENT AREA ---
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Initialize with Home Screen
        self.show_home()

    def create_nav_button(self, text, command):
        btn = ctk.CTkButton(self.sidebar, text=text, command=command, 
                            fg_color="transparent", text_color=("gray10", "#DCE4EE"), 
                            anchor="w", height=50, font=("Roboto", 16, "bold"))
        btn.pack(fill="x", padx=10, pady=5)
        return btn

    def clear_main_area(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

    # --- SCREENS ---

    def show_home(self):
        self.clear_main_area()
        
        # Title
        ctk.CTkLabel(self.main_area, text="Load Production Order", font=("Roboto", 32)).pack(pady=(40, 20))
        
        # Input Box
        entry = ctk.CTkEntry(self.main_area, placeholder_text="Scan Barcode or Enter JSON Path...", width=400, height=50, font=("Roboto", 16))
        entry.pack(pady=10)
        
        # Load Button
        ctk.CTkButton(self.main_area, text="LOAD ORDER", width=200, height=50, font=("Roboto", 16, "bold"),
                      command=lambda: self.status_label.configure(text=f"Loaded: {entry.get()}", text_color="#2cc985")).pack(pady=10)

        # Recent History
        ctk.CTkLabel(self.main_area, text="Recent Orders", font=("Roboto", 20)).pack(pady=(50, 10), anchor="w")
        for i in range(3):
            card = ctk.CTkFrame(self.main_area, height=60)
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(card, text=f"MO-2024-00{i+1}  |  WSCT Project  |  8 Sensors", font=("Roboto", 14)).pack(side="left", padx=20)
            ctk.CTkLabel(card, text="SUCCESS", text_color="#2cc985", font=("Roboto", 14, "bold")).pack(side="right", padx=20)

    def show_build(self):
        self.clear_main_area()
        ctk.CTkLabel(self.main_area, text="Physical Build Wizard", font=("Roboto", 32)).pack(pady=20)
        
        # Placeholder for your "Interactive Build Tool" logic
        info_card = ctk.CTkFrame(self.main_area, height=200, fg_color="#2b2b2b")
        info_card.pack(fill="x", pady=20)
        ctk.CTkLabel(info_card, text="CURRENT TASK: Cut Magnet #8", font=("Roboto", 24, "bold"), text_color="yellow").pack(expand=True)

    def show_config(self):
        self.clear_main_area()
        ctk.CTkLabel(self.main_area, text="Sensor Configuration", font=("Roboto", 32)).pack(pady=20)
        
        # Split into Sensors List vs Log
        content = ctk.CTkFrame(self.main_area, fg_color="transparent")
        content.pack(fill="both", expand=True)
        
        # Left: Sensor Status Grid
        sensor_list = ctk.CTkScrollableFrame(content, width=400, label_text="Connected Sensors")
        sensor_list.pack(side="left", fill="both", padx=(0, 20))
        
        for i in range(1, 9):
            row = ctk.CTkFrame(sensor_list)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"Sensor {i}", font=("Roboto", 14, "bold"), width=80).pack(side="left", padx=10)
            ctk.CTkLabel(row, text="12345678", font=("Roboto", 14), text_color="gray").pack(side="left", padx=10)
            # Status Icon
            color = "gray" if i > 3 else "#2cc985" # Fake status
            ctk.CTkLabel(row, text="●", font=("Roboto", 24), text_color=color).pack(side="right", padx=15)

        # Right: Console Log
        console = ctk.CTkTextbox(content, font=("Consolas", 12))
        console.pack(side="right", fill="both", expand=True)
        console.insert("0.0", "[INFO] Detecting sensors...\n[INFO] Found 8 devices.\n[INFO] Calibrating Sensor 1...\n[SUCCESS] Sensor 1 calibrated.\n...")

    def show_report(self):
        self.clear_main_area()
        ctk.CTkLabel(self.main_area, text="Final Reports", font=("Roboto", 32)).pack(pady=20)
        ctk.CTkButton(self.main_area, text="Open PDF Report", height=50).pack(pady=10)
        ctk.CTkButton(self.main_area, text="View Calibration Plots", height=50).pack(pady=10)

if __name__ == "__main__":
    app = OspreyApp()
    app.mainloop()