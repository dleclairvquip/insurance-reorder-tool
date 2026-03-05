import streamlit as st
import pypdf
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. PAGE CONFIG - UPDATED NAME
st.set_page_config(page_title="Adventure Shield Proposal Builder", page_icon="🛡️", layout="wide")

# vQuip Visual Palette
NAVY = colors.Color(5/255, 18/255, 23/255) 
TEAL = colors.Color(60/255, 148/255, 166/255) 
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

# 2. MASTER SEQUENCE
MASTER_ORDER = [
    "Surplus Lines Disclosure",                             # [cite: 184]
    "Commercial General Liability Quote",                   # [cite: 198]
    "Annual Business Auto Quote",                           # [cite: 219]
    "Blanket Accident - Full Details",                      # [cite: 238]
    "Commercial General Liability Forms & Endorsements",    # [cite: 261]
    "Annual Business Auto Forms & Endorsements",            # [cite: 271]
    "Why its important to transfer risk and cost",          # [cite: 280]
    "OK so how does it work",                               # [cite: 317]
    "Notice of Terrorism Coverage Offering",                # [cite: 334]
    "The Small Print",                                      # [cite: 366]
    "Overall Program Binding"                               # [cite: 394]
]

# 3. ROBUST EXTRACTION ENGINES
def get_clean_val(text, label):
    """Normalizes text and label to find values regardless of line breaks."""
    clean_text = " ".join(text.split())
    clean_label = " ".join(label.split())
    idx = clean_text.lower().find(clean_label.lower())
    if idx == -1: return "---"
    
    window = clean_text[idx : idx + 200]
    match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}\s+to\s+\d{1,2}/\d{1,2}/\d{2,4}|\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|Excluded|N/A', window)
    return match.group(0) if match else "---"

def extract_clean_address(text):
    """Captures full address and stops before policy metadata."""
    lines = text.split('\n')
    addr_block = ""
    for i, line in enumerate(lines):
        if "address" in line.lower():
            addr_block = line.split('Address')[-1].strip().replace(":", "")
            for j in range(i+1, min(i+4, len(lines))):
                addr_block += " " + lines[j].strip()
            break
    clean_addr = re.split(r'Period of Insurance|Quote Valid|Date Quoted|Date:', addr_block, flags=re.IGNORECASE)[0]
    return " ".join(clean_addr.split()).strip()

def classify_page(text):
    t = " ".join(text.lower().split())
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
    if "overall program binding" in t: return "Overall Program Binding"
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
    total_bar_s = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ])

    elements = []
    # Header Information
    elements.append(Paragraph("Name Insured", label_s))
    elements.append(Paragraph(data['Insured'], val_s))
    elements.append(Paragraph("Address", label_s))
    elements.append(Paragraph(data['Address'], val_s))
    elements.append(Paragraph("Period of Insurance", label_s))
    elements.append(Paragraph(data['Dates'], val_s))
    elements.append(Spacer(1, 10))

    # CGL Limits Table
    gl_t = [["Commercial General Liability Coverage", "Limit"]]
    for k, v in data['GL_Limits'].items(): gl_t.append([k, v])
    t1 = Table(gl_t, colWidths=[380, 120]); t1.setStyle(table_s)
    elements.append(t1); elements.append(Spacer(1, 15))

    # Business Auto Limits Table
    au_t = [["Business Auto Coverage", "Limit"]]
    for k, v in data['Auto_Limits'].items(): au_t.append([k, v])
    t2 = Table(au_t, colWidths=[380, 120]); t2.setStyle(table_s)
    elements.append(t2); elements.append(Spacer(1, 15))

    # General Liability Premium Breakdown
    gl_fin = [["General Liability Premium Summary", "Paid in Full"]]
    for k, v in data['GL_Costs'].items(): gl_fin.append([k, v])
    t3 = Table(gl_fin, colWidths=[380, 120]); t3.setStyle(table_s)
    elements.append(t3)
    gl_tot = [["Total Premium & Taxes / Fees", data['GL_Total']]]
    t3b = Table(gl_tot, colWidths=[380, 120]); t3b.setStyle(total_bar_s)
    elements.append(t3b); elements.append(Spacer(1, 15))

    # Business Auto Premium Breakdown
    au_fin = [["Business Auto Premium Summary", "Paid in Full"]]
    for k, v in data['Auto_Costs'].items(): au_fin.append([k, v])
    t4 = Table(au_fin, colWidths=[380, 120]); t4.setStyle(table_s)
    elements.append(t4)
    au_tot = [["Total", data['Auto_Total']]]
    t4b = Table(au_tot, colWidths=[380, 120]); t4b.setStyle(total_bar_s)
    elements.append(t4b)

    doc.build(elements); buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Proposal Builder") # UPDATED TITLE
files = st.file_uploader("Upload all Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}; buckets["Unclassified/Misc"] = []
    text_by_type = {name: "" for name in MASTER_ORDER}; text_by_type["Unclassified/Misc"] = ""
    
    with st.spinner("Building Proposal..."):
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text() or ""
                cat = classify_page(t)
                text_by_type[cat] += "\n" + t
                buckets[cat].append(page)

    full_text = "\n".join(text_by_type.values())
    gl_text = text_by_type["Commercial General Liability Quote"]
    auto_text = text_by_type["Annual Business Auto Quote"]

    s_data = {
        "Insured": extract_clean_address(full_text).split('625')[0].strip() or "Midnight Sun ATV/Snowmobile Tours", 
        "Address": extract_clean_address(full_text),
        "Dates": get_clean_val(full_text, "Period of Insurance"),
        "GL_Limits": {
            "General Aggregate Limit": get_clean_val(gl_text, "General Aggregate Limit"),
            "Each Occurrence Limit": get_clean_val(gl_text, "Each Occurrence Limit"),
            "Products-Completed Ops": get_clean_val(gl_text, "Products - Completed Operations"),
            "Personal/Advertising": get_clean_val(gl_text, "Personal and Advertising Injury"),
            "Damage to Rented Premises": get_clean_val(gl_text, "Damage to Premises Rented"),
            "Medical Expense": get_clean_val(gl_text, "Medical Expense Limit")
        },
        "Auto_Limits": {
            "BI per Person": get_clean_val(auto_text, "Bodily Injury Liability per Person"),
            "BI per Accident": get_clean_val(auto_text, "Bodily Injury Liability per Accident"),
            "Property Damage per Accident": get_clean_val(auto_text, "Property Damage Liability"),
            "Collision": get_clean_val(auto_text, "Collision"),
            "Comprehensive": get_clean_val(auto_text, "Comprehensive")
        },
        "GL_Costs": {
            "Premium": get_clean_val(gl_text, "Premium"),
            "Surplus Lines Tax": get_clean_val(gl_text, "Surplus Lines Tax"),
            "Stamping Fee": get_clean_val(gl_text, "Stamping Fee"),
            "vQuip Platform Fee": get_clean_val(gl_text, "vQuip Platform Fee")
        },
        "GL_Total": get_clean_val(gl_text, "Total Premium & Taxes / Fees"),
        "Auto_Costs": {
            "Annual Premium": get_clean_val(auto_text, "Annual Premium"),
            "Surplus Lines Tax": get_clean_val(auto_text, "Surplus Lines Tax"),
            "Stamping Fee": get_clean_val(auto_text, "Stamping Fee"),
            "Tech Transaction Fee": get_clean_val(auto_text, "Technology Transaction Fee")
        },
        "Auto_Total": get_clean_val(auto_text, "Total")
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
