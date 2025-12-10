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
        segments_raw = string_data.get("segments", [])
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

# --- 2. GUI SCREENS ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class HomeFrame(ctk.CTkFrame):
    """The Dashboard Screen: Order Info & Packing List"""
    def __init__(self, parent, order: OrderSpecSingleString, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="#1f1f1f", corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(header, text="🏭  PRODUCTION DASHBOARD", font=("Roboto", 24, "bold"), text_color="#dce4ee").pack(pady=20)

        # Left Panel: Details
        details = ctk.CTkFrame(self)
        details.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(details, text="ORDER DETAILS", font=("Roboto", 18, "bold"), text_color="gray").pack(pady=15)
        
        self.add_detail(details, "Customer:", order.customer)
        self.add_detail(details, "Project:", f"{order.project} ({order.area_section})")
        self.add_detail(details, "MO / CO:", f"{order.manufacturing_order} / {order.customer_order}", color="#3b8ed0")
        self.add_detail(details, "Description:", order.string_spec.string_description)
        self.add_detail(details, "Cable / Sensors:", f"{order.string_spec.total_cable_m}m  /  {order.string_spec.expected_sensors} sensors")

        if order.notes:
            note_frame = ctk.CTkFrame(details, fg_color="#330000", border_color="red", border_width=1)
            note_frame.pack(fill="x", padx=20, pady=20)
            ctk.CTkLabel(note_frame, text=f"⚠️ {order.notes}", font=("Roboto", 14), text_color="#ffcccc", wraplength=400).pack(padx=10, pady=10)

        # Right Panel: Packing List
        packing = ctk.CTkFrame(self)
        packing.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        ctk.CTkLabel(packing, text="📦 PACKING LIST", font=("Roboto", 18, "bold"), text_color="gray").pack(pady=15)
        
        scroll = ctk.CTkScrollableFrame(packing, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        for item in order.string_spec.box_contents:
            row = ctk.CTkFrame(scroll, fg_color="#2b2b2b")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"x{item.qty}", font=("Roboto", 16, "bold"), width=40, text_color="#2cc985").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=item.item, font=("Roboto", 16)).pack(side="left")

        # Start Button
        btn = ctk.CTkButton(self, text="GO TO CUTTING WIZARD ->", font=("Roboto", 20, "bold"), height=60, fg_color="#2cc985", hover_color="#229964",
                            command=lambda: controller.show_frame("CuttingFrame"))
        btn.grid(row=2, column=0, columnspan=2, padx=40, pady=30, sticky="ew")

    def add_detail(self, parent, label, value, color="white"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(row, text=label, font=("Roboto", 14, "bold"), width=120, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=str(value), font=("Roboto", 14), text_color=color, anchor="w").pack(side="left")


class CuttingFrame(ctk.CTkFrame):
    """The Interactive Cutting Wizard"""
    def __init__(self, parent, order: OrderSpecSingleString, controller):
        super().__init__(parent)
        self.controller = controller
        self.segments = order.string_spec.segments
        self.current_step = 0
        self.remaining_cable = order.string_spec.total_cable_m

        # Layout
        self.grid_columnconfigure(0, weight=0) # Sidebar fixed
        self.grid_columnconfigure(1, weight=1) # Main content expands
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="#1f1f1f")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        # Navigation Button (Back)
        back_btn = ctk.CTkButton(header, text="<- DASHBOARD", width=120, fg_color="transparent", border_width=1, 
                                 text_color="gray", border_color="gray", hover_color="#333333",
                                 command=lambda: controller.show_frame("HomeFrame"))
        back_btn.pack(side="left", padx=20, pady=10)
        
        ctk.CTkLabel(header, text=f"CUTTING: {order.manufacturing_order}", font=("Roboto", 16, "bold")).pack(side="left", padx=20)

        # Sidebar
        self.sidebar = ctk.CTkScrollableFrame(self, width=300, label_text="Cutting List")
        self.sidebar.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        self.sidebar_labels = []
        for seg in self.segments:
            lbl = ctk.CTkLabel(self.sidebar, text=f"#{seg.magnet_no} - {seg.length_m}m", anchor="w", font=("Roboto", 14), padx=10)
            lbl.pack(fill="x", pady=2)
            self.sidebar_labels.append(lbl)

        # Main Card
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
        
        self.step_label = ctk.CTkLabel(self.main_frame, text="", font=("Roboto", 20))
        self.step_label.pack(pady=(20, 10))

        self.card = ctk.CTkFrame(self.main_frame, fg_color="#2b2b2b", corner_radius=15, border_width=2, border_color="#3b8ed0")
        self.card.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(self.card, text="CUT CABLE LENGTH:", font=("Roboto", 24, "bold"), text_color="gray").pack(pady=(40, 10))
        self.length_display = ctk.CTkLabel(self.card, text="", font=("Roboto", 90, "bold"), text_color="#3b8ed0")
        self.length_display.pack(pady=10)
        self.magnet_display = ctk.CTkLabel(self.card, text="", font=("Roboto", 32))
        self.magnet_display.pack(pady=(0, 40))

        # Footer
        footer = ctk.CTkFrame(self, height=80, fg_color="transparent")
        footer.grid(row=2, column=1, sticky="ew", padx=20, pady=20)
        
        self.spool_label = ctk.CTkLabel(footer, text="", font=("Roboto", 16))
        self.spool_label.pack(side="left", padx=20)
        
        self.confirm_btn = ctk.CTkButton(footer, text="CONFIRM CUT (Enter)", font=("Roboto", 18, "bold"), height=50, width=250,
                                         fg_color="#2cc985", hover_color="#229964", command=self.next_step)
        self.confirm_btn.pack(side="right", padx=20)

        # Initial Update
        self.update_ui()

    def update_ui(self):
        if self.current_step >= len(self.segments):
            self.show_completion()
            return

        seg = self.segments[self.current_step]
        self.step_label.configure(text=f"Step {self.current_step + 1} of {len(self.segments)}")
        self.length_display.configure(text=f"{seg.length_m} m")
        self.magnet_display.configure(text=f"Magnet #{seg.magnet_no} ({seg.label})")
        self.spool_label.configure(text=f"Est. Spool: {self.remaining_cable:.2f}m")

        for i, lbl in enumerate(self.sidebar_labels):
            if i < self.current_step:
                lbl.configure(text_color="gray", font=("Roboto", 14, "overstrike"))
            elif i == self.current_step:
                lbl.configure(text_color="#3b8ed0", font=("Roboto", 16, "bold"))
            else:
                lbl.configure(text_color="white", font=("Roboto", 14))

    def next_step(self):
        if self.current_step < len(self.segments):
            self.remaining_cable -= self.segments[self.current_step].length_m
            self.current_step += 1
            self.update_ui()

    def show_completion(self):
        self.length_display.configure(text="DONE!", text_color="#2cc985")
        self.magnet_display.configure(text="All cables cut.")
        self.confirm_btn.configure(text="RETURN TO DASHBOARD", command=lambda: self.controller.show_frame("HomeFrame"), fg_color="#3b8ed0")
        self.step_label.configure(text="")
        for lbl in self.sidebar_labels:
            lbl.configure(text_color="gray", font=("Roboto", 14, "overstrike"))


class BuildApp(ctk.CTk):
    def __init__(self, order):
        super().__init__()
        self.title("Osprey Manufacturing Wizard")
        self.geometry("1200x800")
        
        # Container to stack frames on top of each other
        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        
        # Create and store the screens
        for F in (HomeFrame, CuttingFrame):
            page_name = F.__name__
            frame = F(parent=self.container, order=order, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Show Home initially
        self.show_frame("HomeFrame")
        
        # Global binding for Enter key to trigger the button on the active frame
        self.bind('<Return>', self.handle_enter)

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise() # Bring to front
        self.current_frame = page_name

    def handle_enter(self, event):
        # Only trigger next step if we are on the cutting frame
        if self.current_frame == "CuttingFrame":
            self.frames["CuttingFrame"].confirm_btn.invoke()

if __name__ == "__main__":
    json_path = "test_order.json"
    if not os.path.exists(json_path):
        print("Error: test_order.json not found")
        sys.exit(1)

    order_data = load_order_spec_from_json(json_path)
    if order_data:
        app = BuildApp(order_data)
        app.mainloop()