from dataclasses import dataclass
from typing import List, Optional, Literal
import json





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
    cable_slack_mm: float
    standard_or_slimline: Literal["Standard", "Slimline"]
    expected_sensors: int
    segments: List[SegmentSpec]
    box_contents: List[BoxItem]

@dataclass
class OrderSpecSingleString:
    id: str
    customer_order: Optional[str]
    manufacturing_order: str
    project: Optional[str]
    area_section: Optional[str]
    customer: Optional[str]
    notes: Optional[str]
    string_spec: StringSpec



# now code for loading data from JSON file:
def load_order_spec_single_string_from_json(file_path: str) -> OrderSpecSingleString:
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Convert nested structures
    segments = [SegmentSpec(**seg) for seg in data['string']['segments']] # AI but is a very clean way to do it, list comprehension
    box_contents = [BoxItem(**item) for item in data['string']['box_contents']] #** operator expands the dictionary into keyword arguments, saves us having to right out the keys etc over and over again
    
    string_spec = StringSpec(
        id=data['string']['id'],
        string_description=data['string']['string_description'],
        connector_pairs=data['string']['connector_pairs'],
        connector_flying_lead=data['string']['connector_flying_lead'],
        total_cable_m=data['string']['total_cable_m'],
        cable_slack_mm=data['string']['cable_slack_mm'],
        standard_or_slimline=data['string']['standard_or_slimline'],
        expected_sensors=data['string']['expected_sensors'],
        segments=segments,
        box_contents=box_contents
    )
    
    order_spec = OrderSpecSingleString(
        id=data['id'],
        customer_order=data.get('customer_order'),
        manufacturing_order=data['manufacturing_order'],
        project=data.get('project'),
        area_section=data.get('area_section'),
        customer=data.get('customer'),
        notes=data.get('notes'),
        string_spec=string_spec
    )
    
    return order_spec

STR1 = load_order_spec_single_string_from_json("test_order.json")

# print(STR1.string_spec.segments[1].length_m)
# this setup works really well, would be easy to use this in code to access string spec data
# However, still need a full picture and a final file structure to make this a complete solution.


# for segments in STR1.string_spec.segments:
#     print(segments.label, segments.magnet_no, segments.length_m)


# Example usage:
# print(STR1.customer_order)

