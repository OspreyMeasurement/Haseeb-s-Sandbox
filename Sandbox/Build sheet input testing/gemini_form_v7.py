import streamlit as st
import pandas as pd
import datetime

import json
import os
from fpdf import FPDF

# --- CONFIG ---
DOWNLOAD_DIR = "generated_orders"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- PDF GENERATOR CLASS ---
class OrderPDF(FPDF):
    def header(self):
        # Header on every page
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 10, 'OSPREY MEASUREMENT SYSTEMS - PRODUCTION ORDER', border=False, align='R')
        self.ln(15)

    def footer(self):
        # Footer on every page
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

def create_pdf_with_embedded_json(order_meta, strings_data, json_path):
    pdf = OrderPDF()
    pdf.alias_nb_pages() # Enable total page numbering

    # ==========================================
    # PAGE 1: COVER SHEET
    # ==========================================
    pdf.add_page()
    
    # Title
    pdf.set_font('Helvetica', 'B', 24)
    pdf.cell(0, 20, "Production Order Summary", ln=True, align='C')
    pdf.ln(10)

    # Project Info Grid
    pdf.set_font('Helvetica', '', 12)
    
    def add_row(label, value):
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(50, 10, label, border=1, align='R')
        pdf.set_font('Helvetica', '', 12)
        pdf.cell(0, 10, str(value), border=1, align='C', ln=True)

    add_row("Customer:", order_meta['customer'])
    add_row("Project:", order_meta['project'])
    add_row("Area / Section:", order_meta['area'])
    add_row("Date:", str(order_meta['date']))
    add_row("Completed By:", order_meta['completed_by'])
    add_row("Total Strings:", str(order_meta['num_strings']))
    
    pdf.ln(20)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.cell(0, 10, "NOTE: The machine-readable JSON data is attached to this PDF file.", ln=True, align='C')
    pdf.cell(0, 10, "(Open in Adobe Acrobat > Attachments to view)", ln=True, align='C')

    # ==========================================
    # SUBSEQUENT PAGES: STRING DETAILS
    # ==========================================
    for s in strings_data:
        pdf.add_page()
        
        # String Header
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_fill_color(200, 220, 255) # Light Blue
        pdf.cell(0, 12, f"String {s['index']+1}: {s['name']}", border=1, ln=True, align='L', fill=True)
        pdf.ln(5)

        # Config Details
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, "Configuration", ln=True)
        pdf.set_font('Helvetica', '', 11)
        


        
        # Mini-table for config
        pdf.set_font('Helvetica', 'B', 11); pdf.cell(40, 8, "Type:", border=1, align='R'); pdf.set_font('Helvetica', '', 11); pdf.cell(50, 8, s['type'], border=1, align='C')
        pdf.set_font('Helvetica', 'B', 11); pdf.cell(40, 8, "Casing Depth:", border=1, align='R'); pdf.set_font('Helvetica', '', 11); pdf.cell(50, 8, f"{s['depth']} m", border=1, align='C', ln=True)
            
        pdf.set_font('Helvetica', 'B', 11); pdf.cell(40, 8, "Cable From BH Top:", border=1, align='R'); pdf.set_font('Helvetica', '', 11); pdf.cell(50, 8, f"{s['top_cable']} m", align='C', border=1)
        pdf.set_font('Helvetica', 'B', 11); pdf.cell(40, 8, "Slack:", border=1, align='R'); pdf.set_font('Helvetica', '', 11); pdf.cell(50, 8, f"{s['slack']} mm", border=1, align='C' ,ln=True)
        pdf.ln(5)

        # Hardware Extras
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, "Hardware", ln=True)
        pdf.set_font('Helvetica', '', 11)
        
        conn_text = f"{s['n_pairs']} Pairs " if s['has_connectors'] else "None" # adjusted for just showing pairs
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(40, 8, "Connectors:", border=1, align='R'); pdf.set_font('Helvetica', '', 11); pdf.cell(0, 8, conn_text, border=1, align='C', ln=True)
        # if connector pairs, generate a new cell with flying lead info
        if s['has_connectors']:
            pdf.cell(40, 8, "Flying Lead:", border=1); pdf.cell(0, 8, f"{s['fly_lead']} m", border=1, ln=True)
        
        supp_text = []
        if s['top_supp']: supp_text.append("Top")
        if s['bot_supp']: supp_text.append("Bottom")

        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(40, 8, "Supports:", border=1, align='R'); pdf.set_font('Helvetica', '', 11); pdf.cell(0, 8, ", ".join(supp_text) if supp_text else "None", border=1, align='C', ln=True)
        pdf.ln(10)

        # CUTTING LIST TABLE
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, "Magnet Depth", ln=True)
        
        # Table Header
        pdf.set_fill_color(230, 230, 230) # Grey
        pdf.cell(20, 8, "Mag #", border=1, align='C', fill=True)
        pdf.cell(30, 8, "Depth (m)", border=1, align='C', fill=True)
        pdf.cell(0, 8, "Label", border=1, align='L', fill=True)
        pdf.ln()
        
        # Table Rows
        pdf.set_font('Helvetica', '', 11)
        df = s['segments'] # This is the DataFrame from the editor
        
        # Iterate through the DataFrame rows
        for _, row in df.iterrows():
            pdf.cell(20, 8, str(row['Magnet #']), border=1, align='C')
            pdf.cell(30, 8, f"{row['Depth (m)']:.2f}", border=1, align='C')
            pdf.cell(0, 8, str(row['Label']), border=1, align='L')
            pdf.ln()


    # ==========================================
    # EMBEDDING THE JSON
    # ==========================================
    # fpdf2 feature: attach_file (or embed_file in older versions)
    pdf.embed_file(json_path, desc="Full Order Data (JSON)")

    output_path = os.path.join(DOWNLOAD_DIR, f"{order_meta['project']}_Traveler.pdf")
    pdf.output(output_path)
    return output_path


# ----------------------------------------- STREAMLIT APP ----------------------------------------- #
# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="IPX Order Form", layout="wide")
st.image("OSPREY-LOGO-Positive-0057d62a.webp", width=350, )
st.title("IPX Order Form: BH Details")
st.info("Please fill in the details below for the BH order.")

# --- SECTION 1: CUSTOMER DETAILS ---
with st.container():
    st.subheader("1. Project Information")
    
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", datetime.date.today())
        customer = st.text_input("Customer Name", )
        project = st.text_input("Project")
    
    with col2:
        area_section = st.text_input("Area / Section")
        completed_by = st.text_input("Completed By")
        
    st.markdown("---")

# --- SECTION 2: QUANTITY ---
st.subheader("2. String Configuration")
# This number dictates how many sections we generate below
num_strings = st.number_input("How many strings are in this order?", min_value=1, value=1)

# We will store all the data in this list
all_strings_data = []

# --- SECTION 3: DYNAMIC STRING INPUTS ---
for i in range(int(num_strings)):
    # Create a distinct section for each string
    # We use an expander so the page doesn't get too huge visually
    with st.expander(f"String {i+1} Details", expanded=True):
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            install_name = st.text_input(f"Installation Name (String {i+1})", key=f"inst_{i}")
            string_type = st.selectbox(f"Type", ["Standard", "Slimline"], key=f"type_{i}")
            
        with c2:
            depth = st.number_input(f"Total Depth of Casing (m)", min_value=0.0, step=0.1, key=f"depth_{i}")
            cable_top = st.number_input(f"Cable from Top of BH (m)", min_value=0.0, step=0.1, key=f"top_{i}")
            
        with c3:
            # conditional for slack based on type
            if string_type == "Standard":
                slack = st.number_input(f"Cable Slack (mm)", value=150, step=1, key=f"slack_{i}")
            else:
                # if slimline hide input and default value to 0
                slack = 0
                st.markdown("**Cable Slack (mm)**: 0 (Slimline type)")
            
        # --- Connectors & Supports ---
        st.markdown("#### Hardware Extras")
        col_hw1, col_hw2 = st.columns(2)
        
        with col_hw1:
            has_connectors = st.checkbox("Connector Pairs?", key=f"has_conn_{i}")
            if has_connectors:
                # These inputs only appear if the checkbox is ticked
                n_pairs = st.number_input("No. Connector Pairs", min_value=1, key=f"n_pairs_{i}")
                fly_lead = st.number_input("Connector Flying Lead (m)", min_value=0.0, step=0.1, key=f"fly_{i}")
            else:
                n_pairs = 0
                fly_lead = 0.0

        with col_hw2:
            st.markdown("**Select supports required**")
            top_support = st.checkbox("Top Support", value=False, key=f"top_supp_{i}")
            bot_support = st.checkbox("Bottom Support", value=False, key=f"bot_supp_{i}")

        # --- SECTION 4: MAGNET TABLE ---
        st.markdown("#### BH Magnet Depth Info")

        # Ask for number of magnets to auto-generate the table
        num_magnets = st.number_input(f"How many magnets for String {i+1}?", min_value=1, value=8, key=f"num_mags_{i}")
        
        # 1. Generate the Default Data Logic
        # We create a list of dictionaries to pre-fill the table
        table_rows = []
        
        # Loop from Top (num_magnets) down to Bottom (1)
        for mag_num in range(num_magnets, 0, -1):
            
            # Auto-Labeling Logic
            if mag_num == num_magnets:
                label = f"Top / Magnet {mag_num}"
            elif mag_num == 1:
                label = f"Datum / Bottom Magnet {mag_num}"
            else:
                label = f"Magnet {mag_num}"
                
            table_rows.append({
                "Magnet #": mag_num,
                "Depth (m)": 0.0,  # Default to 0 so they can fill it in
                "Label": label
            })
            
        # Create DataFrame
        df_default = pd.DataFrame(table_rows)
        
        # Display the Editor
        st.info("💡 Edit the Depths below. Depths are from top of casing (m).")
        edited_df = st.data_editor(
            df_default, 
            num_rows="dynamic", 
            use_container_width=True, 
            key=f"editor_{i}",
            column_config={
                "Magnet #": st.column_config.NumberColumn(disabled=True),
                "Label": st.column_config.TextColumn(disabled=True),
                "Depth (m)": st.column_config.NumberColumn(
                    min_value=0.01,
                    format="%.2f",
                    required=True,
                    )
            },
            hide_index=True,
        )
        
        
        # Store this string's data
        all_strings_data.append({
            "index": i,
            "name": install_name,
            "type": string_type,          # <--- Was missing
            "depth": depth,               # <--- Was missing
            "top_cable": cable_top,       # <--- Was missing
            "slack": slack,               # <--- Was missing
            "has_connectors": has_connectors, # <--- Was missing
            "n_pairs": n_pairs,           # <--- Was missing
            "fly_lead": fly_lead,         # <--- Was missing
            "top_supp": top_support,      # <--- Was missing
            "bot_supp": bot_support,      # <--- Was missing
            "segments": edited_df
        })

st.markdown("---")

# --- FINAL SUBMISSION ---
if st.button("🚀 Generate All Order Files", type="primary"):
    
    
    # 1. Prepare the metadata
    order_meta = {
        "customer": customer, "project": project, "area": area_section,
        "date": str(date), "completed_by": completed_by, "num_strings": num_strings
    }

    # generate json file as one big file for whole order, dont worry about strings individually for now
    json_payload = {
        "meta":order_meta,
        "strings": []
    }

    for s in all_strings_data:
        # Convert df to list of dicts for json
        seg_list = s['segments'].to_dict(orient='records')
        s_clean = s.copy()
        s_clean['segments'] = seg_list # replace df with list of dicts
        json_payload['strings'].append(s_clean)

    json_filename = f"{project}_order_data.json"
    json_path = os.path.join(DOWNLOAD_DIR, json_filename)
    
    with open(json_path, 'w') as f:
        json.dump(json_payload, f, indent=4)

    # 2. Create the PDF with embedded JSON
    try:
        pdf_path = create_pdf_with_embedded_json(order_meta, all_strings_data, json_path)
        st.success(f"✅ PDF Generated!")

        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 Download Production Order PDF",
                data=f,
                file_name=os.path.basename(pdf_path),
            )

    except Exception as e:
        st.error(f"❌ Error generating PDF: {e}")

