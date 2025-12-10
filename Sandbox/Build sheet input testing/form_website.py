import streamlit as st
import pandas as pd
import json
import os
from fpdf import FPDF
from barcode import Code128
from barcode.writer import ImageWriter

# --- 1. CONFIGURATION ---
# This is where your files will be saved. 
# Change this to your OneDrive folder path in the future.
SAVE_DIR = "generated_orders" 

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# --- 2. HELPER FUNCTIONS ---

def generate_json(order_data, segments_df, box_contents_df):
    """Converts form data into strict JSON schema, handling empty cells safely."""
    
    # --- FIX 1: Fill empty cells with 0 to prevent crashes ---
    segments_df = segments_df.fillna(0)
    box_contents_df = box_contents_df.fillna(0)

    # Convert DataFrame to list of dicts for segments
    segments = []
    for _, row in segments_df.iterrows():
        # Skip rows where Magnet # is 0 (empty rows)
        if row["Magnet #"] == 0:
            continue
            
        segments.append({
            "label": str(row["Label"]), 
            "magnet_no": int(row["Magnet #"]),
            "length_m": float(row["Length (m)"])
        })
        
    # Convert DataFrame for box contents
    box_contents = []
    for _, row in box_contents_df.iterrows():
        # Skip empty items
        if row["Qty"] == 0:
            continue
            
        box_contents.append({
            "item": str(row["Item"]),
            "qty": int(row["Qty"])
        })

    # Construct the full object
    payload = {
        "id": f"{order_data['co']}_{order_data['mo']}_{order_data['string_id']}",
        "customer_order": order_data['co'],
        "manufacturing_order": order_data['mo'],
        "project": order_data['project'],
        "area_section": order_data['area'],
        "customer": order_data['customer'],
        "notes": order_data['notes'],
        "string": {
            "id": order_data['string_id'],
            "string_description": order_data['desc'],
            "connector_pairs": 0,
            "connector_flying_lead": 0,
            "total_cable_m": segments_df["Length (m)"].sum(),
            "cable_slack_mm": 15,
            "standard_or_slimline": order_data['type'],
            "expected_sensors": len(segments),
            "segments": segments,
            "box_contents": box_contents
        }
    }
    return payload

def generate_barcode(mo_number, filename_base):
    """Generates a barcode image and returns the absolute file path."""
    # 1. Define the full path WITHOUT extension (library adds .png)
    full_save_path = os.path.join(SAVE_DIR, filename_base)
    
    code = Code128(mo_number, writer=ImageWriter())
    
    # 2. Save. This returns the actual filename used (e.g. ".../MO001.png")
    actual_filename = code.save(full_save_path)
    
    # 3. Return absolute path to ensure FPDF finds it
    return os.path.abspath(actual_filename)

def generate_pdf(payload, filename, barcode_image_path):
    """Generates a professional PDF traveler that mimics the Excel sheet."""
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "OSPREY PRODUCTION ORDER", ln=True, align='C')
    pdf.ln(10)
    
    # Info Grid
    pdf.set_font("Arial", '', 11)
    
    def add_field(label, value):
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(50, 8, label, border=1)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 8, str(value), border=1, ln=True)

    add_field("Manufacturing Order:", payload['manufacturing_order'])
    add_field("Customer Order:", payload['customer_order'])
    add_field("Customer:", payload['customer'])
    add_field("Description:", payload['string']['string_description'])
    
    pdf.ln(10)
    
    # Segments Table
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Cutting List", ln=True)
    
    # Table Header
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(30, 8, "Mag #", 1, 0, 'C', True)
    pdf.cell(40, 8, "Length (m)", 1, 0, 'C', True)
    pdf.cell(100, 8, "Label", 1, 1, 'C', True)
    
    # Table Rows
    pdf.set_font("Arial", '', 11)
    for seg in payload['string']['segments']:
        pdf.cell(30, 8, str(seg['magnet_no']), 1, 0, 'C')
        pdf.cell(40, 8, str(seg['length_m']), 1, 0, 'C')
        pdf.cell(100, 8, str(seg['label']), 1, 1, 'L')
        
    # Barcode
    pdf.ln(20)
    pdf.cell(0, 10, "Scan to Load Order:", align='C', ln=True)
    
    # --- FIX 2: Use the exact path returned from generate_barcode ---
    try:
        pdf.image(barcode_image_path, x=80, w=50)
    except Exception as e:
        pdf.cell(0, 10, f"Error loading barcode: {e}", ln=True, align='C')
    
    pdf_path = os.path.join(SAVE_DIR, f"{filename}.pdf")
    pdf.output(pdf_path)
    return pdf_path

# --- 3. STREAMLIT UI ---

st.set_page_config(page_title="Osprey Order Creator", layout="wide")

st.title("🏭 Production Order Generator")
st.markdown("Use this form to generate JSON files and PDF travelers for the factory floor.")

# Top Section: Order Details
col1, col2 = st.columns(2)

with col1:
    co = st.text_input("Customer Order (CO)", "CO12345")
    mo = st.text_input("Manufacturing Order (MO)", "MO001")
    customer = st.text_input("Customer Name", "SOCOTEC UK")
    project = st.text_input("Project", "HS2")

with col2:
    string_id = st.text_input("String ID", "STR1")
    desc = st.text_input("String Description", "WSCT-XM01001")
    area = st.text_input("Area / Section", "WSCT")
    type_ = st.selectbox("String Type", ["Standard", "Slimline"])

notes = st.text_area("Production Notes", "Verify bottom sensor readings.")

# Middle Section: The Excel-Like Editor
st.subheader("✂️ Cutting List")
st.info("💡 Tip: You can copy-paste multiple rows directly from Excel into this table.")

# Default data structure
default_data = pd.DataFrame([
    {"Magnet #": 8, "Length (m)": 6.12, "Label": "Top / Magnet 8"},
    {"Magnet #": 7, "Length (m)": 5.74, "Label": "Magnet 7"},
    {"Magnet #": 6, "Length (m)": 4.91, "Label": "Magnet 6"},
])

edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# Box Contents (Hidden by default to save space)
with st.expander("📦 Box Contents (Optional)"):
    box_data = pd.DataFrame([
        {"Item": "Top support", "Qty": 1},
        {"Item": "Bottom support", "Qty": 1},
        {"Item": "USB Adapter", "Qty": 1},
    ])
    box_df = st.data_editor(box_data, num_rows="dynamic")

# Submit Button
if st.button("🚀 GENERATE ORDER PACKAGE", type="primary", use_container_width=True):
    
    # 1. Prepare Data
    order_data = {
        "co": co, "mo": mo, "string_id": string_id, "desc": desc,
        "customer": customer, "project": project, "area": area,
        "type": type_, "notes": notes
    }
    
    base_filename = mo  # We use MO as the main identifier
    
    try:
        # 2. Generate JSON
        json_payload = generate_json(order_data, edited_df, box_df)
        json_path = os.path.join(SAVE_DIR, f"{base_filename}.json")
        with open(json_path, "w") as f:
            json.dump(json_payload, f, indent=4)
            
        # 3. Generate Barcode (Get the correct path back!)
        barcode_path = generate_barcode(mo, f"{base_filename}_barcode")
        
        # 4. Generate PDF (Pass that path correctly)
        pdf_path = generate_pdf(json_payload, base_filename, barcode_path)
        
        # 5. Success Message
        st.success(f"✅ Order {mo} Generated Successfully!")
        
        # Show Download Links
        with open(json_path, "rb") as f:
            st.download_button("Download JSON", f, file_name=f"{base_filename}.json")
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF Traveler", f, file_name=f"{base_filename}.pdf")
            
        # Preview
        st.image(barcode_path, caption="Generated Traveler Barcode")
        
    except Exception as e:
        st.error(f"Error generating order: {e}")