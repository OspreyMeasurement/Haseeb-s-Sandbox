import json
import os
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

# --- RICH LIBRARY IMPORTS ---
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box

# --- 1. DATA STRUCTURES (Unchanged) ---
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

# --- 2. THE LOADER (Unchanged) ---
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

# --- 3. THE RICH TUI WIZARD ---

console = Console()

def get_header_panel(order: OrderSpecSingleString):
    """Creates the nice 'Factory Logo' header with customer info."""
    s = order.string_spec
    
    # Use a Grid for perfect alignment of the details
    grid = Table.grid(expand=True)
    grid.add_column(style="bold cyan", width=12)
    grid.add_column()
    
    grid.add_row("Customer:", order.customer or "Unknown")
    grid.add_row("Project:", f"{order.project} ({order.area_section})")
    grid.add_row("Order Refs:", f"{order.manufacturing_order} / {order.customer_order}")
    grid.add_row("Description:", s.string_description)
    grid.add_row("Total Cable:", f"{s.total_cable_m} meters")
    grid.add_row("Sensors:", str(s.expected_sensors))

    return Panel(
        grid,
        title="🏭  PRODUCTION ORDER  🏭",
        subtitle="Osprey Measurement Systems",
        border_style="blue",
        padding=(1, 2)
    )

def get_cutting_table(segments, current_index):
    """Creates the table showing all cuts."""
    table = Table(title="✂️  CABLE CUTTING PROGRESS", expand=True, box=box.SIMPLE)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Mag #", style="magenta", width=10)
    table.add_column("Length", justify="right", style="cyan", width=10)
    table.add_column("Label", style="white")

    for i, seg in enumerate(segments):
        if i < current_index:
            status = "[green]DONE[/]"
            style = "dim"
        elif i == current_index:
            status = "[bold yellow]CURRENT[/]"
            style = "bold white"
        else:
            status = "[dim]WAITING[/]"
            style = "dim"
        
        table.add_row(
            status,
            f"#{seg.magnet_no}",
            f"{seg.length_m:.2f}m",
            seg.label,
            style=style
        )
    return table

def run_rich_wizard(order: OrderSpecSingleString):
    s = order.string_spec
    
    # --- 1. HEADER & START ---
    console.clear()
    
    # Show the big header panel
    console.print(get_header_panel(order))
    
    if order.notes:
        console.print(Panel(f"[bold red]⚠️  NOTE: {order.notes}[/]", border_style="red"))
    
    console.input("\n[bold green]Press Enter to START CUTTING...[/]")

    # --- 2. CUTTING PHASE ---
    remaining_cable = s.total_cable_m
    
    for i, seg in enumerate(s.segments):
        # CLEAR SCREEN FOR EVERY STEP
        console.clear()
        
        # 1. Re-print the nice header (smaller version context)
        console.print(f"[dim]MO: {order.manufacturing_order} | CO: {order.customer_order} | Desc: {s.string_description}[/]")
        
        # 2. Print the Table (Context)
        console.print(get_cutting_table(s.segments, i))
        console.print("") 

        # 3. Print the BIG Instruction (Focus)
        instruction_text = Text()
        instruction_text.append("CUT THIS CABLE:\n", style="bold white")
        instruction_text.append(f"{seg.length_m:.2f} meters\n", style="bold yellow reverse")
        instruction_text.append(f"Magnet #{seg.magnet_no}", style="bold magenta")
        
        panel = Panel(
            Align.center(instruction_text),
            title="[bold yellow]Current Task[/]",
            border_style="yellow",
            padding=(1, 2)
        )
        console.print(panel)
        
        # 4. Footer Info
        console.print(f"[dim]Cable remaining on spool approx: {remaining_cable:.2f}m[/]")
        
        # 5. Input
        choice = console.input("\n[bold]Press Enter to confirm cut[/] (or 'q' to quit): ")
        if choice.lower() == 'q':
            sys.exit()
        
        remaining_cable -= seg.length_m

    # --- 3. PACKING PHASE (STATIC LIST) ---
    console.clear()
    
    # Show the final cutting table one last time
    console.print(get_cutting_table(s.segments, len(s.segments)))
    console.print("\n")

    # Show Packing List (Static Table)
    pack_table = Table(title="📦 BOX CONTENTS CHECKLIST", expand=True, box=box.ROUNDED)
    pack_table.add_column("Item", style="white")
    pack_table.add_column("Qty", justify="right", style="cyan")
    
    for item in s.box_contents:
        pack_table.add_row(item.item, str(item.qty))
    
    console.print(pack_table)
    
    # Single confirmation
    console.input("\n[bold green]Verify contents and Press Enter to Finish...[/]")

    # --- 4. COMPLETION ---
    console.clear()
    console.print(Panel(
        Align.center(
            f"[bold green]Ready for configuration: {order.manufacturing_order}[/]\n"
            f"Proceed to the configuration tool."
        ),
        title="🎉 BUILD COMPLETE",
        border_style="green",
        padding=(1, 4)
    ))

# --- MAIN ---
if __name__ == "__main__":
    # Ensure you have 'test_order.json'
    json_path = "test_order.json"
    if not os.path.exists(json_path):
        console.print(f"[red]Error: Could not find {json_path}[/]")
        sys.exit(1)

    order = load_order_spec_from_json(json_path)
    if order:
        try:
            run_rich_wizard(order)
        except KeyboardInterrupt:
            console.print("\n[red]Operation cancelled.[/]")