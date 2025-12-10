import customtkinter as ctk
import json
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

# --- 1. DATA STRUCTURES & LOADER (Unchanged) ---
@dataclass
class SegmentSpec:
    label: str
    magnet_no: int
    length_m: float

@dataclass
class BoxItem:
    item: str
    qty: int

@dataclass
class StringSpec:
    id: str
    string_description: str
    connector_pairs: int
    connector_flying_lead: int
    total_cable_m: float
    cable_slack_mm: int
    standard_or_slimline: Optional[str]
    expected_sensors: int
    segments: List[SegmentSpec]
    box_contents: List[BoxItem]

@dataclass
class OrderSpecSingleString:
    id: str
    customer_order: str
    manufacturing_order: str
    project: Optional[str]
    area_section: Optional[str]
    customer: Optional[str]
    notes: Optional[str]
    string_spec: StringSpec

def load_order_spec_from_json(path: str) -> OrderSpecSingleString:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        string_data = data["string"]
        segments_raw = string_data.get("string", [])
        segments = [
            SegmentSpec(label=seg["label"], magnet_no=int(seg["magnet_no"]), length_m=float(seg["length_m"]))
            for seg in segments_raw
        ]
        segments.sort(key=lambda s: s.magnet_no, reverse=True)
        box_contents = [
            BoxItem(item=bi["item"], qty=int(bi["qty"]))
            for bi in string_data.get("box_contents", [])
        ]
        string_spec = StringSpec(
            id=string_data["id"],
            string_description=string_data["string_description"],
            connector_pairs=int(string_data.get("connector_pairs", 0)),
            connector_flying_lead=int(string_data.get("connector_flying_lead", 0)),
            total_cable_m=float(string_data.get("total_cable_m", 0.0)),
            cable_slack_mm=int(string_data.get("cable_slack_mm", 0)),
            standard_or_slimline=string_data.get("standard/slimline"),
            expected_sensors=int(string_data.get("expected_sensors", 0)),
            segments=segments,
            box_contents=box_contents,
        )
        return OrderSpecSingleString(
            id=data["id"],
            customer_order=data["customer_order"],
            manufacturing_order=data["manufacturing_order"],
            project=data.get("project"),
            area_section=data.get("area/section"),
            customer=data.get("customer"),
            notes=data.get("notes"),
            string_spec=string_spec,
        )
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return None

# --- 2. THE GUI APPLICATION ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class BuildWizardApp(ctk.CTk):
    def __init__(self, order: OrderSpecSingleString):
        super().__init__()

        self.order = order
        self.segments = order.string_spec.segments
        
        # State variables
        self.current_step = 0
        self.remaining_cable = order.string_spec.total_cable_m

        # Window Setup
        self.title("Osprey Manufacturing Wizard")
        self.geometry("1200x800")
        
        # Start at the Home Screen
        self.show_home_screen()

    def clear_window(self):
        """Removes all widgets from the window to prepare for a new screen."""
        for widget in self.winfo_children():
            widget.destroy()

    # =========================================================================
    # SCREEN 1: HOME DASHBOARD
    # =========================================================================
    def show_home_screen(self):
        self.clear_window()
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Header ---
        header = ctk.CTkFrame(self, fg_color="#1f1f1f", corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(header, text="🏭  PRODUCTION ORDER DASHBOARD", font=("Roboto", 24, "bold"), text_color="#dce4ee").pack(pady=20)

        # --- Left Panel: Order Details ---
        details_frame = ctk.CTkFrame(self, corner_radius=10)
        details_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(details_frame, text="ORDER DETAILS", font=("Roboto", 18, "bold"), text_color="gray").pack(pady=15)
        
        # Helper for details
        def add_detail(label, value, color="white"):
            row = ctk.CTkFrame(details_frame, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(row, text=label, font=("Roboto", 14, "bold"), width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(value), font=("Roboto", 14), text_color=color, anchor="w").pack(side="left")

        add_detail("Customer:", self.order.customer)
        add_detail("Project:", f"{self.order.project} ({self.order.area_section})")
        add_detail("Manuf. Order:", self.order.manufacturing_order, color="#3b8ed0")
        add_detail("Cust. Order:", self.order.customer_order)
        add_detail("Description:", self.order.string_spec.string_description)
        add_detail("Sensors:", self.order.string_spec.expected_sensors)
        add_detail("Total Cable:", f"{self.order.string_spec.total_cable_m} m")

        if self.order.notes:
            note_frame = ctk.CTkFrame(details_frame, fg_color="#330000", border_color="red", border_width=1)
            note_frame.pack(fill="x", padx=20, pady=20)
            ctk.CTkLabel(note_frame, text="⚠️ NOTE:", font=("Roboto", 14, "bold"), text_color="red").pack(anchor="w", padx=10, pady=(10,0))
            ctk.CTkLabel(note_frame, text=self.order.notes, font=("Roboto", 14), wraplength=400).pack(anchor="w", padx=10, pady=(0,10))

        # --- Right Panel: Packing List ---
        packing_frame = ctk.CTkFrame(self, corner_radius=10)
        packing_frame.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(packing_frame, text="📦 PACKING LIST", font=("Roboto", 18, "bold"), text_color="gray").pack(pady=15)
        
        scroll_pack = ctk.CTkScrollableFrame(packing_frame, fg_color="transparent")
        scroll_pack.pack(fill="both", expand=True, padx=10, pady=10)

        for item in self.order.string_spec.box_contents:
            row = ctk.CTkFrame(scroll_pack, fg_color="#2b2b2b")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"x{item.qty}", font=("Roboto", 16, "bold"), width=50, text_color="#2cc985").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=item.item, font=("Roboto", 16)).pack(side="left", padx=10)

        # --- Footer: Start Button ---
        start_btn = ctk.CTkButton(
            self, 
            text="START CABLE CUTTING ->", 
            font=("Roboto", 20, "bold"), 
            height=60,
            fg_color="#2cc985", 
            hover_color="#229964",
            command=self.show_cutting_screen
        )
        start_btn.grid(row=2, column=0, columnspan=2, padx=40, pady=30, sticky="ew")


    # =========================================================================
    # SCREEN 2: CUTTING WIZARD (The existing interactive tool)
    # =========================================================================
    def show_cutting_screen(self):
        self.clear_window()
        
        # Grid layout reset
        self.grid_columnconfigure(0, weight=0) # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1) # Main content expands
        self.grid_rowconfigure(1, weight=1)

        # --- Header ---
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1f1f1f")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        header_text = f"RUNNING ORDER: {self.order.manufacturing_order}  |  {self.order.string_spec.string_description}"
        ctk.CTkLabel(header_frame, text=header_text, font=("Roboto", 16, "bold"), text_color="#dce4ee").pack(pady=10, padx=20, anchor="w")

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkScrollableFrame(self, width=300, label_text="Cutting List")
        self.sidebar_frame.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        
        self.sidebar_labels = []
        for i, seg in enumerate(self.segments):
            lbl = ctk.CTkLabel(
                self.sidebar_frame, 
                text=f"#{seg.magnet_no} - {seg.length_m}m", 
                anchor="w",
                font=("Roboto", 14),
                padx=10
            )
            lbl.pack(fill="x", pady=2)
            self.sidebar_labels.append(lbl)

        # --- Main Card ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
        
        self.step_label = ctk.CTkLabel(self.main_frame, text="", font=("Roboto", 20))
        self.step_label.pack(pady=(20, 10))

        self.card = ctk.CTkFrame(self.main_frame, fg_color="#2b2b2b", corner_radius=15, border_width=2, border_color="#3b8ed0")
        self.card.pack(fill="both", expand=True, padx=20, pady=10)

        self.action_label = ctk.CTkLabel(self.card, text="CUT CABLE LENGTH:", font=("Roboto", 24, "bold"), text_color="gray")
        self.action_label.pack(pady=(40, 10))

        self.length_display = ctk.CTkLabel(self.card, text="", font=("Roboto", 90, "bold"), text_color="#3b8ed0")
        self.length_display.pack(pady=10)

        self.magnet_display = ctk.CTkLabel(self.card, text="", font=("Roboto", 32))
        self.magnet_display.pack(pady=(0, 40))

        # --- Footer ---
        self.footer_frame = ctk.CTkFrame(self, height=100, fg_color="transparent")
        self.footer_frame.grid(row=2, column=1, sticky="ew", padx=20, pady=20)

        self.spool_label = ctk.CTkLabel(self.footer_frame, text="", font=("Roboto", 16))
        self.spool_label.pack(side="left", padx=20)

        self.confirm_button = ctk.CTkButton(
            self.footer_frame, 
            text="CONFIRM CUT & NEXT (Enter)", 
            font=("Roboto", 18, "bold"),
            height=50, 
            width=250,
            command=self.next_cut_step,
            fg_color="#2cc985",
            hover_color="#229964"
        )
        self.confirm_button.pack(side="right", padx=20)

        self.bind('<Return>', lambda event: self.next_cut_step())
        
        self.update_cutting_ui()

    def update_cutting_ui(self):
        """Refreshes the Cutting UI based on the current step."""
        if self.current_step >= len(self.segments):
            self.show_completion_screen()
            return

        seg = self.segments[self.current_step]

        self.step_label.configure(text=f"Step {self.current_step + 1} of {len(self.segments)}")
        self.length_display.configure(text=f"{seg.length_m} m")
        self.magnet_display.configure(text=f"For Magnet #{seg.magnet_no} ({seg.label})")
        self.spool_label.configure(text=f"Est. Spool Remaining: {self.remaining_cable:.2f}m")

        # Update Sidebar Styling
        for i, lbl in enumerate(self.sidebar_labels):
            if i < self.current_step:
                lbl.configure(text_color="gray", font=("Roboto", 14, "overstrike"))
            elif i == self.current_step:
                lbl.configure(text_color="#3b8ed0", font=("Roboto", 16, "bold"))
            else:
                lbl.configure(text_color="white", font=("Roboto", 14))

    def next_cut_step(self):
        if self.current_step < len(self.segments):
            self.remaining_cable -= self.segments[self.current_step].length_m
            self.current_step += 1
            self.update_cutting_ui()

    def show_completion_screen(self):
        self.length_display.configure(text="DONE!", text_color="#2cc985")
        self.magnet_display.configure(text="All cables cut.")
        self.action_label.configure(text="BUILD COMPLETE")
        # Change button to allow exit or restart
        self.confirm_button.configure(text="CLOSE", command=self.destroy, fg_color="#3b8ed0")
        self.unbind('<Return>') # Stop Enter key
        
        for lbl in self.sidebar_labels:
            lbl.configure(text_color="gray", font=("Roboto", 14, "overstrike"))

if __name__ == "__main__":
    json_path = "test_order.json"
    if not os.path.exists(json_path):
        print(f"Error: Could not find {json_path}")
        sys.exit(1)

    order_data = load_order_spec_from_json(json_path)
    
    if order_data:
        app = BuildWizardApp(order_data)
        app.mainloop()