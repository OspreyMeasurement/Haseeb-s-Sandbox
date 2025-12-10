from dataclasses import dataclass
from typing import List, Optional
import json
import logging



# #1 Create data structure , for the order spec single string. THis will make it easier later to work with the data 

# @dataclass
# class SegmentSpec:
#     label: str
#     magnet_no: int
#     length_m: float



# @dataclass
# class BoxItem:
#     item: str
#     qty: int

# @dataclass
# class StringSpec:
#     id:str
#     string_desciption: str
#     connector_pairs:str
#     connector_flying_lead:int
#     total_cable_m:float
#     cable_slack_mm:int
#     standard_or_slimline: Optional[str]
#     expected_sensors: int
#     segments: List[SegmentSpec]
#     box_contents: List


# @dataclass
# class OrderSpecSingleString:
#     id: str
#     customer_order: str
#     manufacturing_order: str
#     project: Optional[str]
#     area_section: Optional[str]
#     customer: Optional[str]
#     notes: Optional[str]
#     string_spec: StringSpec


import json
import logging
from dataclasses import dataclass
from typing import List, Optional

# --- 1. DATA STRUCTURES (The Interface) ---

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

# --- 2. THE LOADER (JSON -> Python) ---

def load_order_spec_from_json(path: str) -> OrderSpecSingleString:
    """Parses the JSON file into a strict Python object structure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        string_data = data["string"]

        # Parse Segments
        segments_raw = string_data.get("string", [])
        segments = [
            SegmentSpec(
                label=seg["label"],
                magnet_no=int(seg["magnet_no"]),
                length_m=float(seg["length_m"]),
            )
            for seg in segments_raw
        ]
        # Sort segments: Highest Magnet Number (Top) -> Lowest (Bottom)
        segments.sort(key=lambda s: s.magnet_no, reverse=True)

        # Parse Box Contents
        box_contents = [
            BoxItem(item=bi["item"], qty=int(bi["qty"]))
            for bi in string_data.get("box_contents", [])
        ]

        # Create String Spec Object
        string_spec = StringSpec(
            id=string_data["id"],
            string_description=string_data["string_description"],
            connector_pairs=int(string_data.get("connector_pairs", 0)),
            connector_flying_lead=int(string_data.get("connector_flying_lead", 0)),
            total_cable_m=float(string_data.get("total_cable_m", 0.0)),
            cable_slack_mm=int(string_data.get("cable_slack_mm", 0)),
            standard_or_slimline=string_data.get("standard/slimline"), # Handling the '/' key
            expected_sensors=int(string_data.get("expected_sensors", 0)),
            segments=segments,
            box_contents=box_contents,
        )

        # Create Main Order Object
        order = OrderSpecSingleString(
            id=data["id"],
            customer_order=data["customer_order"],
            manufacturing_order=data["manufacturing_order"],
            project=data.get("project"),
            area_section=data.get("area/section"), # Handling the '/' key
            customer=data.get("customer"),
            notes=data.get("notes"),
            string_spec=string_spec,
        )

        return order

    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return None

# --- 3. THE VISUALIZER (The "Build Instruction" Screen) ---

def show_build_instructions(order: OrderSpecSingleString):
    """Prints a formatted build sheet to the console."""
    s = order.string_spec
    
    print("\n" + "="*60)
    print(f"   🛠️  BUILD INSTRUCTIONS: {order.manufacturing_order} / {order.customer_order}  🛠️")
    print("="*60)
    
    # Header Info
    print(f"Customer:      {order.customer}")
    print(f"Project:       {order.project} ({order.area_section})")
    print(f"String ID:     {s.id}")
    print(f"Description:   {s.string_description}")
    print("-" * 60)
    
    if order.notes:
        print(f"⚠️  NOTES: {order.notes.upper()}")
        print("-" * 60)

    # String Config
    print("STRING CONFIGURATION:")
    print(f"  • Type:            {s.standard_or_slimline}")
    print(f"  • Sensors:         {s.expected_sensors}")
    print(f"  • Total Cable:     {s.total_cable_m} m")
    print(f"  • Cable Slack:     {s.cable_slack_mm} mm")
    print("-" * 60)

    # Cutting List (The most important part for the operator)
    print("✂️  CUTTING LIST (Top to Bottom):")
    print(f"   {'Mag #':<8} | {'Length (m)':<12} | {'Label'}")
    print("   " + "-"*45)
    
    for seg in s.segments:
        print(f"   #{seg.magnet_no:<7} | {seg.length_m:<12} | {seg.label}")
    print("-" * 60)

    # Box Contents
    if s.box_contents:
        print("📦  BOX CONTENTS:")
        for item in s.box_contents:
            print(f"  [ ] {item.item} (x{item.qty})")
    
    print("="*60 + "\n")

# --- 4. TEST RUNNER ---

if __name__ == "__main__":
    # Test the loader with the file we just created
    json_path = "CO12345_MO001_STR1.json"
    
    print(f"Attempting to load: {json_path}...")
    loaded_order = load_order_spec_from_json(json_path)
    
    if loaded_order:
        show_build_instructions(loaded_order)
        
        # Verification logic for your future integration:
        print(f"✅ Data ready for IPXConfigurator:")
        print(f"   -> Sensors to configure: {loaded_order.string_spec.expected_sensors}")
        print(f"   -> MO for Report: {loaded_order.manufacturing_order}")
        print(f"   -> CO for Report: {loaded_order.customer_order}")