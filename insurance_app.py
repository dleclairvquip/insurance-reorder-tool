import streamlit as st
import pypdf
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. PAGE CONFIG
st.set_page_config(page_title="vQuip Master Assembler", page_icon="🛡️", layout="wide")

# Theme Colors
NAVY = colors.Color(5/255, 18/255, 23/255)
TEAL = colors.Color(60/255, 148/255, 166/255)
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

# 2. THE RESTORED MASTER SEQUENCE
MASTER_ORDER = [
    "Surplus Lines Disclosure",
    "Commercial General Liability Quote",
    "Annual Business Auto Quote",
    "Blanket Accident - Full Details",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost",
    "OK so how does it work",
    "Notice of Terrorism Coverage Offering",
    "The Small Print",
    "Overall Program Binding"
]

# 3. EXTRACTION ENGINES
def get_proximity_val(text, label):
    """Finds values in the tabular format specifically targeting the 'Paid in Full' column."""
    try:
        idx = text.lower().find(label.lower())
        if idx == -1: return "---"
        window = text[idx : idx + 250]
        # Hunts for currency, 'Excluded', 'N/A', or date ranges
        match = re.search(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|Excluded|N/A|\d{1,2}/\d{1,2}/\d{2,4}\s+to\s+\d{1,2}/\d{1,2}/\d{2,4}', window)
        return match.group(0) if match else "---"
    except: return "---"

def extract_full_address(text):
    """Captures Name Insured and multi-line Address including City, State, Zip[cite: 202]."""
    lines = text.split('\n')
    address_parts = []
    for i, line in enumerate(lines):
        if "address" in line.lower():
            # Grab the current line after 'Address' and the following 1-2 lines for City/State/Zip 
            address_parts.append(line.split('Address')[-1].strip().replace(":", ""))
            if i + 1 < len(lines): address_parts.append(lines[i+1].strip())
            if i + 2 < len(lines) and any(char.isdigit() for char in lines[i+2]): 
                address_parts.append(lines[i+2].strip())
            break
    return " ".join(address_parts).strip()

def classify_page(text):
    t = " ".join(text.lower().split())
    if "surplus lines" in t and "disclosure" in t: return "Surplus Lines Disclosure"
    if "commercial general liability" in t and "limit" in t and "forms" not in t: return "Commercial General Liability Quote"
    if "annual business auto" in t and "quote" in t and "forms" not in t: return "Annual Business Auto Quote"
    if "blanket accident" in t and "details" in t: return "Blanket Accident - Full Details"
    if "forms" in t and "endorsements" in t:
        return "Annual Business Auto Forms & Endorsements" if "auto" in t else "Commercial General Liability Forms & Endorsements"
    if "transfer risk" in t: return "Why its important to transfer risk and cost"
    if "how does it work" in t: return "OK so how does it work"
    if "terrorism" in t: return "Notice of Terrorism Coverage Offering"
    if "small print" in t: return "The Small Print"
    if "binding" in t or "binder" in t: return "Overall Program Binding"
    return "Unclassified/Misc"

# 4. SUMMARY GENERATOR
def generate_exec_summary(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    label_s = ParagraphStyle('Label', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', spaceAfter=2)
    val_s = ParagraphStyle('Value', parent=styles['Normal'], fontSize=11, fontName='Helvetica', spaceAfter=12)
    
    table_s = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY])
    ])
    
    teal_total_s = TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), TEAL), ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'), ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ])

    elements = []
    # Header Identity
    elements.append(Paragraph("Name Insured", label_s))
    elements.append(Paragraph(data['Insured'], val_s))
    elements.append(Paragraph("Address", label_s))
    elements.append(Paragraph(data['Address'], val_s))
    elements.append(Paragraph("Period of Insurance", label_s))
    elements.append(Paragraph(data['Dates'], val_s))
    elements.append(Spacer(1, 5))

    # CGL Limits
    gl_limits = [["Commercial General Liability Coverage", "Limit"]]
    for k, v in data['GL_Limits'].items(): gl_limits.append([k, v])
    t_gl = Table(gl_limits, colWidths=[380, 120]); t_gl.setStyle(table_s)
    elements.append(t_gl); elements.append(Spacer(1, 10))

    # CGL Premium Breakdown 
    gl_prem = [["General Liability Premium Summary", "Paid in Full"]]
    for k, v in data['GL_Costs'].items(): gl_prem.append([k, v])
    t_gl_p = Table(gl_prem, colWidths=[380, 120]); t_gl_p.setStyle(table_s)
    elements.append(t_gl_p); elements.append(Spacer(1, 10))

    # Auto Limits
    auto_limits = [["Business Auto Coverage", "Limit"]]
    for k, v in data['Auto_Limits'].items(): auto_limits.append([k, v])
    t_auto = Table(auto_limits, colWidths=[380, 120]); t_auto.setStyle(table_s)
    elements.append(t_auto); elements.append(Spacer(1, 10))

    # Auto Premium Breakdown 
    auto_prem = [["Business Auto Premium Summary", "Paid in Full"]]
    for k, v in data['Auto_Costs'].items(): auto_prem.append([k, v])
    t_auto_p = Table(auto_prem, colWidths=[380, 120]); t_auto_p.setStyle(table_s)
    elements.append(t_auto_p)

    doc.build(elements); buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield | Executive Assembler")
files = st.file_uploader("Upload all Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}; buckets["Unclassified/Misc"] = []
    full_text = ""
    for f in files:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            t = page.extract_text() or ""; full_text += "\n" + t
            buckets[classify_page(t)].append(page)

    # Scrape data for summary
    s_data = {
        "Insured": "Midnight Sun ATV/Snowmobile Tours" if "Midnight Sun" in full_text else "Unknown Insured",
        "Address": extract_full_address(full_text),
        "Dates": get_proximity_val(full_text, "Period of Insurance"),
        "GL_Limits": {
            "General Aggregate Limit": get_proximity_val(full_text, "General Aggregate Limit"),
            "Each Occurrence Limit": get_proximity_val(full_text, "Each Occurrence Limit"),
            "Products - Completed Operations": get_proximity_val(full_text, "Products - Completed Operations"),
            "Personal and Advertising Injury": get_proximity_val(full_text, "Personal and Advertising Injury"),
            "Damage to Premises Rented to You": get_proximity_val(full_text, "Damage to Premises Rented"),
            "Medical Expense Limit": get_proximity_val(full_text, "Medical Expense Limit")
        },
        "Auto_Limits": {
            "Bodily Injury per Person": get_proximity_val(full_text, "Bodily Injury Liability per Person"),
            "Bodily Injury per Accident": get_proximity_val(full_text, "Bodily Injury Liability per Accident"),
            "Property Damage per Accident": get_proximity_val(full_text, "Property Damage Liability"),
            "Collision": get_proximity_val(full_text, "Collision"),
            "Comprehensive": get_proximity_val(full_text, "Comprehensive")
        },
        "GL_Costs": {
            "Premium": get_proximity_val(full_text, "Premium"),
            "Surplus Lines Tax": get_proximity_val(full_text, "Surplus Lines Tax:"),
            "Stamping Fee": get_proximity_val(full_text, "Stamping Fee"),
            "vQuip Platform Fee": get_proximity_val(full_text, "vQuip Platform Fee"),
            "Total Premium & Taxes / Fees": get_proximity_val(full_text, "Total Premium & Taxes")
        },
        "Auto_Costs": {
            "Annual Premium": get_proximity_val(full_text, "Annual Premium"),
            "Surplus Lines Tax": get_proximity_val(full_text, "Surplus Lines Tax"),
            "Stamping Fee": get_proximity_val(full_text, "Stamping Fee"),
            "Technology Transaction Fee": get_proximity_val(full_text, "Technology Transaction Fee"),
            "Total": get_proximity_val(full_text, "Total")
        }
    }

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 ASSEMBLE 11-PAGE MASTER QUOTE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            st.download_button("💾 DOWNLOAD PACKAGE", writer.write(io.BytesIO()), "Package.pdf")
            
    with col2:
        if st.button("📊 GENERATE SEPARATE SUMMARY"):
            pdf_buf = generate_exec_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY", pdf_buf, "Summary.pdf")
