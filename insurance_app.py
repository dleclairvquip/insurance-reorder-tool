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
st.set_page_config(page_title="Adventure Shield | Master Assembler", page_icon="🛡️", layout="wide")

# Theme Colors based on user screenshots
NAVY = colors.Color(5/255, 18/255, 23/255)
TEAL = colors.Color(60/255, 148/255, 166/255)
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

# 2. MASTER SEQUENCE
MASTER_ORDER = [
    "Surplus Lines Disclosure", "Commercial General Liability Quote",
    "Annual Business Auto Quote", "Blanket Accident Quote",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost to my clients",
    "OK so how does it work", "Notice of Terrorism Coverage Offering",
    "The Small Print", "Overall Program Binding"
]

# 3. ADVANCED EXTRACTION HELPERS
def get_val_after(text, label):
    """Targeted search for values in tabular PDF layouts."""
    try:
        idx = text.lower().find(label.lower())
        if idx == -1: return "---"
        window = text[idx : idx + 150]
        # Regex targets: currency, 'Excluded', 'N/A', or date ranges
        match = re.search(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|Excluded|N/A|\d{1,2}/\d{1,2}/\d{2,4}\s+to\s+\d{1,2}/\d{1,2}/\d{2,4}', window)
        return match.group(0) if match else "---"
    except: return "---"

def extract_multi_line(text, label):
    """Handles fields that wrap or have significant whitespace after the label."""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            content = line[line.lower().find(label.lower()) + len(label):].strip()
            # If the value is on the line below (common in PDF parsing)
            if i + 1 < len(lines) and len(content) < 3:
                content = lines[i+1].strip()
            return content.replace(":", "").strip()
    return "Not Found"

def classify_page(text):
    """Categorizes pages based on proven keyword triggers."""
    t = " ".join(text.lower().split())
    if "surplus lines" in t and ("disclosure" in t or "notice" in t): return "Surplus Lines Disclosure"
    if "insurance quotation" in t or ("commercial general liability" in t and "limit" in t and "forms" not in t): return "Commercial General Liability Quote"
    if "annual business auto" in t and "quote" in t and "forms" not in t: return "Annual Business Auto Quote"
    if "accident protection" in t or "blanket accident" in t: return "Blanket Accident Quote"
    if "forms" in t and "endorsements" in t:
        return "Annual Business Auto Forms & Endorsements" if "auto" in t else "Commercial General Liability Forms & Endorsements"
    if "transfer risk" in t: return "Why its important to transfer risk and cost to my clients"
    if "how does it work" in t: return "OK so how does it work"
    if "terrorism" in t: return "Notice of Terrorism Coverage Offering"
    if "small print" in t: return "The Small Print"
    if "binding" in t or "binder" in t: return "Overall Program Binding"
    return "Unclassified/Misc"

# 4. SUMMARY GENERATOR
def create_master_summary(data):
    """Builds the separate 1-page summary PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    label_s = ParagraphStyle('Label', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', spaceAfter=2)
    val_s = ParagraphStyle('Value', parent=styles['Normal'], fontSize=12, fontName='Helvetica', spaceAfter=12)
    header_s = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY])
    ])

    elements = []
    # Identity Block
    elements.append(Paragraph("Name Insured", label_s))
    elements.append(Paragraph(data['Insured'], val_s))
    elements.append(Paragraph("Address", label_s))
    elements.append(Paragraph(data['Address'], val_s))
    elements.append(Paragraph("Period of Insurance", label_s))
    elements.append(Paragraph(data['Dates'], val_s))
    elements.append(Spacer(1, 15))

    # CGL Section
    gl_data = [["Commercial General Liability Coverage", "Limit"]]
    for k, v in data['GL_Limits'].items(): gl_data.append([k, v])
    t_gl = Table(gl_data, colWidths=[380, 120])
    t_gl.setStyle(header_s)
    elements.append(t_gl)
    elements.append(Spacer(1, 15))

    # Auto Section
    auto_data = [["Business Auto Coverage", "Limit"]]
    for k, v in data['Auto_Limits'].items(): auto_data.append([k, v])
    t_auto = Table(auto_data, colWidths=[380, 120])
    t_auto.setStyle(header_s)
    elements.append(t_auto)
    elements.append(Spacer(1, 15))

    # Premium Summary
    cost_data = [["Premium Payment Plans", "Paid-in-Full"]]
    for k, v in data['Costs'].items(): cost_data.append([k, v])
    t_cost = Table(cost_data, colWidths=[380, 120])
    t_cost.setStyle(header_s)
    elements.append(t_cost)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield | Master Assembler")
files = st.file_uploader("Upload all PDFs", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    full_text = ""
    
    with st.spinner("Processing documents..."):
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                txt = page.extract_text() or ""
                full_text += "\n" + txt
                buckets[classify_page(txt)].append(page)

    # DATA EXTRACTION Logic
    s_data = {
        "Insured": extract_multi_line(full_text, "Name Insured"),
        "Address": extract_multi_line(full_text, "Address"),
        "Dates": get_val_after(full_text, "Period of Insurance"),
        "GL_Limits": {
            "General Aggregate Limit": get_val_after(full_text, "General Aggregate Limit"),
            "Each Occurrence Limit": get_val_after(full_text, "Each Occurrence Limit"),
            "Products-Completed Ops": get_val_after(full_text, "Products - Completed Operations"),
            "Medical Expense Limit": get_val_after(full_text, "Medical Expense Limit")
        },
        "Auto_Limits": {
            "Bodily Injury per Person": get_val_after(full_text, "Bodily Injury Liability per Person"),
            "Bodily Injury per Accident": get_val_after(full_text, "Bodily Injury Liability per Accident"),
            "Property Damage": get_val_after(full_text, "Property Damage Liability"),
            "Collision": get_val_after(full_text, "Collision"),
            "Comprehensive": get_val_after(full_text, "Comprehensive")
        },
        "Costs": {
            "Annual Premium": get_val_after(full_text, "Annual Premium"),
            "Surplus Lines Tax": get_val_after(full_text, "Surplus Lines Tax"),
            "vQuip Platform Fee": get_val_after(full_text, "vQuip Platform Fee"),
            "TOTAL ESTIMATED COST": get_val_after(full_text, "Total Premium & Taxes / Fees")
        }
    }

    st.header(f"Account: {s_data['Insured']}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 ASSEMBLE 11-PAGE QUOTE PACKAGE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            
            final_out = io.BytesIO()
            writer.write(final_out)
            st.download_button("💾 DOWNLOAD MASTER PDF", final_out.getvalue(), f"Package_{s_data['Insured']}.pdf")
            
    with col2:
        if st.button("📊 GENERATE SEPARATE SUMMARY PAGE"):
            summary_pdf = create_master_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY PDF", summary_pdf, f"Executive_Summary_{s_data['Insured']}.pdf")
