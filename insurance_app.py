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

# vQuip Visual Palette
NAVY = colors.Color(5/255, 18/255, 23/255) 
TEAL = colors.Color(60/255, 148/255, 166/255) 
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

# 2. FIXED MASTER SEQUENCE (Terrorism before Small Print)
MASTER_ORDER = [
    "Surplus Lines Disclosure",
    "Commercial General Liability Quote",
    "Annual Business Auto Quote",
    "Blanket Accident - Full Details",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost",
    "OK so how does it work",
    "Notice of Terrorism Coverage Offering",  # Pinned here
    "The Small Print",                        # Pinned here
    "Overall Program Binding"
]

# 3. EXTRACTION ENGINES
def get_proximity_val(text, label):
    try:
        idx = text.lower().find(label.lower())
        if idx == -1: return "---"
        window = text[idx : idx + 250]
        # Specifically targeting date ranges and currency
        match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}\s+to\s+\d{1,2}/\d{1,2}/\d{2,4}|\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|Excluded|N/A', window)
        return match.group(0) if match else "---"
    except: return "---"

def extract_full_address(text):
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if "address" in line.lower():
            addr = line.split('Address')[-1].strip().replace(":", "")
            if i + 1 < len(lines): addr += " " + lines[i+1].strip()
            if i + 2 < len(lines): addr += " " + lines[i+2].strip()
            return addr
    return "Not Found"

def classify_page(text):
    t = " ".join(text.lower().split())
    # Precise ordering triggers
    if "surplus lines" in t and "disclosure" in t: return "Surplus Lines Disclosure"
    if "terrorism" in t and "insurance coverage offering" in t: return "Notice of Terrorism Coverage Offering"
    if "small print" in t: return "The Small Print"
    if "commercial general liability" in t and "limit" in t and "forms" not in t: return "Commercial General Liability Quote"
    if "annual business auto" in t and "quote" in t and "forms" not in t: return "Annual Business Auto Quote"
    if "blanket accident" in t and "details" in t: return "Blanket Accident - Full Details"
    if "forms" in t and "endorsements" in t:
        return "Annual Business Auto Forms & Endorsements" if "auto" in t else "Commercial General Liability Forms & Endorsements"
    if "transfer risk" in t: return "Why its important to transfer risk and cost"
    if "how does it work" in t: return "OK so how does it work"
    if "overall program binding" in t or "where you sign" in t: return "Overall Program Binding"
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

    elements = []
    # Header Section
    elements.append(Paragraph("Name Insured", label_s))
    elements.append(Paragraph(data['Insured'], val_s))
    elements.append(Paragraph("Address", label_s))
    elements.append(Paragraph(data['Address'], val_s))
    elements.append(Paragraph("Period of Insurance", label_s))
    elements.append(Paragraph(data['Dates'], val_s))
    elements.append(Spacer(1, 5))

    # CGL Section
    gl_t = [["Commercial General Liability Coverage", "Limit"]]
    for k, v in data['GL_Limits'].items(): gl_t.append([k, v])
    t1 = Table(gl_t, colWidths=[380, 120]); t1.setStyle(table_s)
    elements.append(t1); elements.append(Spacer(1, 10))

    # Auto Section
    au_t = [["Business Auto Coverage", "Limit"]]
    for k, v in data['Auto_Limits'].items(): au_t.append([k, v])
    t2 = Table(au_t, colWidths=[380, 120]); t2.setStyle(table_s)
    elements.append(t2); elements.append(Spacer(1, 10))

    # Financial Summary
    fin_t = [["Premium Summary (Paid in Full)", "Amount"]]
    for k, v in data['GL_Costs'].items(): fin_t.append([f"GL {k}", v])
    for k, v in data['Auto_Costs'].items(): fin_t.append([f"Auto {k}", v])
    t3 = Table(fin_t, colWidths=[380, 120]); t3.setStyle(table_s)
    elements.append(t3)

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

    s_data = {
        "Insured": "Midnight Sun ATV/Snowmobile Tours", 
        "Address": extract_full_address(full_text),
        "Dates": get_proximity_val(full_text, "Period of Insurance"),
        "GL_Limits": {
            "General Aggregate Limit": get_proximity_val(full_text, "General Aggregate Limit"),
            "Each Occurrence Limit": get_proximity_val(full_text, "Each Occurrence Limit"),
            "Products-Completed Ops": get_proximity_val(full_text, "Products - Completed Operations"),
            "Personal/Advertising": get_proximity_val(full_text, "Personal and Advertising Injury"),
            "Medical Expense": get_proximity_val(full_text, "Medical Expense Limit")
        },
        "Auto_Limits": {
            "BI per Person": get_proximity_val(full_text, "Bodily Injury Liability per Person"),
            "BI per Accident": get_proximity_val(full_text, "Bodily Injury Liability per Accident"),
            "Collision": get_proximity_val(full_text, "Collision"),
            "Comprehensive": get_proximity_val(full_text, "Comprehensive")
        },
        "GL_Costs": {
            "Premium": get_proximity_val(full_text, "Premium"),
            "Total": get_proximity_val(full_text, "Total Premium & Taxes / Fees")
        },
        "Auto_Costs": {
            "Annual Premium": get_proximity_val(full_text, "Annual Premium"),
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
            
            out_buf = io.BytesIO()
            writer.write(out_buf)
            st.download_button("💾 DOWNLOAD PACKAGE", out_buf.getvalue(), "Package.pdf")
            
    with col2:
        if st.button("📊 GENERATE SEPARATE SUMMARY"):
            pdf_buf = generate_exec_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY", pdf_buf.getvalue(), "Summary.pdf")
