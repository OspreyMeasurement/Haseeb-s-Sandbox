import customtkinter as ctk
import json
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

# --- 1. DATA STRUCTURES & LOADER (Same as before) ---
# We keep this exactly the same so it works with your existing JSON files.

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

ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class BuildWizardApp(ctk.CTk):
    def __init__(self, order: OrderSpecSingleString):
        super().__init__()

        self.order = order
        self.segments = order.string_spec.segments
        self.current_step = 0
        self.remaining_cable = order.string_spec.total_cable_m

        # Window Setup
        self.title("Osprey Manufacturing Wizard")
        self.geometry("1100x700")

        # --- LAYOUT CONFIGURATION ---
        self.grid_columnconfigure(1, weight=1) # Right side expands
        self.grid_rowconfigure(1, weight=1)    # Content area expands

        # --- 1. HEADER (Top Bar) ---
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1f1f1f")
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        header_text = f"MANUFACTURING ORDER: {order.manufacturing_order}  |  CUSTOMER: {order.customer}  |  DESC: {order.string_spec.string_description}"
        self.header_label = ctk.CTkLabel(self.header_frame, text=header_text, font=("Roboto", 16, "bold"), text_color="#dce4ee")
        self.header_label.pack(pady=10, padx=20, anchor="w")

        # --- 2. SIDEBAR (List of Cuts) ---
        self.sidebar_frame = ctk.CTkScrollableFrame(self, width=300, label_text="Cutting List")
        self.sidebar_frame.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        
        self.sidebar_labels = []
        for i, seg in enumerate(self.segments):
            # Create a label for each segment in the sidebar
            lbl = ctk.CTkLabel(
                self.sidebar_frame, 
                text=f"#{seg.magnet_no} - {seg.length_m}m", 
                anchor="w",
                font=("Roboto", 14),
                padx=10
            )
            lbl.pack(fill="x", pady=2)
            self.sidebar_labels.append(lbl)

        # --- 3. MAIN WORK AREA (The Big Instruction) ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
        
        # Step Indicator
        self.step_label = ctk.CTkLabel(self.main_frame, text="Step 1 of X", font=("Roboto", 20))
        self.step_label.pack(pady=(20, 10))

        # The Card Container
        self.card = ctk.CTkFrame(self.main_frame, fg_color="#2b2b2b", corner_radius=15, border_width=2, border_color="#3b8ed0")
        self.card.pack(fill="both", expand=True, padx=20, pady=10)

        # Big "CUT THIS" Text
        self.action_label = ctk.CTkLabel(self.card, text="CUT CABLE LENGTH:", font=("Roboto", 24, "bold"), text_color="gray")
        self.action_label.pack(pady=(40, 10))

        # The Huge Number (Length)
        self.length_display = ctk.CTkLabel(self.card, text="0.00 m", font=("Roboto", 90, "bold"), text_color="#3b8ed0")
        self.length_display.pack(pady=10)

        # Magnet Number
        self.magnet_display = ctk.CTkLabel(self.card, text="For Magnet #X", font=("Roboto", 32))
        self.magnet_display.pack(pady=(0, 40))

        # --- 4. FOOTER (Controls & Info) ---
        self.footer_frame = ctk.CTkFrame(self, height=100, fg_color="transparent")
        self.footer_frame.grid(row=2, column=1, sticky="ew", padx=20, pady=20)

        self.spool_label = ctk.CTkLabel(self.footer_frame, text="Est. Spool Remaining: 0.00m", font=("Roboto", 16))
        self.spool_label.pack(side="left", padx=20)

        self.confirm_button = ctk.CTkButton(
            self.footer_frame, 
            text="CONFIRM CUT & NEXT (Enter)", 
            font=("Roboto", 18, "bold"),
            height=50, 
            width=250,
            command=self.next_step,
            fg_color="#2cc985",
            hover_color="#229964"
        )
        self.confirm_button.pack(side="right", padx=20)

        # Bind Enter key to the button
        self.bind('<Return>', lambda event: self.next_step())

        # Initialize UI state
        self.update_ui()

    def update_ui(self):
        """Refreshes the UI based on the current step."""
        if self.current_step >= len(self.segments):
            self.show_completion_screen()
            return

        seg = self.segments[self.current_step]

        # Update Main Card
        self.step_label.configure(text=f"Step {self.current_step + 1} of {len(self.segments)}")
        self.length_display.configure(text=f"{seg.length_m} m")
        self.magnet_display.configure(text=f"For Magnet #{seg.magnet_no} ({seg.label})")
        self.spool_label.configure(text=f"Est. Spool Remaining: {self.remaining_cable:.2f}m")

        # Update Sidebar Styling
        for i, lbl in enumerate(self.sidebar_labels):
            if i < self.current_step:
                # Completed items
                lbl.configure(text_color="gray", font=("Roboto", 14, "overstrike"))
            elif i == self.current_step:
                # Current item
                lbl.configure(text_color="#3b8ed0", font=("Roboto", 16, "bold"))
            else:
                # Future items
                lbl.configure(text_color="white", font=("Roboto", 14))

    def next_step(self):
        """Advances to the next cutting instruction."""
        if self.current_step < len(self.segments):
            # Deduct length from spool
            self.remaining_cable -= self.segments[self.current_step].length_m
            
            # Advance step
            self.current_step += 1
            self.update_ui()

    def show_completion_screen(self):
        """Shows the final screen."""
        self.length_display.configure(text="DONE!", text_color="#2cc985")
        self.magnet_display.configure(text="All cables cut successfully.")
        self.action_label.configure(text="BUILD COMPLETE")
        self.confirm_button.configure(text="CLOSE", command=self.destroy, fg_color="#3b8ed0")
        self.step_label.configure(text="")
        
        # Mark all sidebar items as done
        for lbl in self.sidebar_labels:
            lbl.configure(text_color="gray", font=("Roboto", 14, "overstrike"))

if __name__ == "__main__":
    # Ensure you have 'test_order.json'
    json_path = "test_order.json"
    if not os.path.exists(json_path):
        print(f"Error: Could not find {json_path}")
        sys.exit(1)

    order_data = load_order_spec_from_json(json_path)
    
    if order_data:
        app = BuildWizardApp(order_data)
        app.mainloop()