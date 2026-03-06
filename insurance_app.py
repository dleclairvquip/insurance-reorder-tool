import streamlit as st
import pypdf
import io
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. PAGE CONFIG
st.set_page_config(page_title="Adventure Shield Proposal Builder", page_icon="🛡️", layout="wide")

# Visual Palette
NAVY = colors.Color(5/255, 18/255, 23/255) 
TEAL = colors.Color(60/255, 148/255, 166/255) 
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

# 2. MASTER SEQUENCE (Restored for the Quote Package)
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

# 3. STABILIZED EXTRACTION ENGINE
def get_clean_val(text, label, is_date=False):
    """
    Finds the label and scans the horizontal plane.
    Uses negative lookahead (?!.*to) to block Period of Insurance dates.
    """
    flat_text = " ".join(text.split())
    search_label = " ".join(label.lower().split())
    
    idx = flat_text.lower().find(search_label)
    if idx == -1: return "---"
    
    # Widened 450-character window to jump across table gutters
    window = flat_text[idx : idx + 450]
    
    if is_date:
        match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}\s+to\s+\d{1,2}/\d{1,2}/\d{2,4}', window)
    else:
        # Prioritizes currency/Excluded. Negative lookahead blocks date ranges
        match = re.search(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?!\s+to)|Excluded|---', window)
        
    return match.group(0) if match else "---"

def extract_clean_identity(text, label):
    """Surgical identity extraction that stops exactly at metadata."""
    lines = text.split('\n')
    result = ""
    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            result = line.split(label)[-1].strip().replace(":", "")
            if i + 1 < len(lines): result += " " + lines[i+1].strip()
            break
    result = re.split(r'Period of Insurance|Quote Valid|Date Quoted|Carrier|Date:', result, flags=re.IGNORECASE)[0]
    return " ".join(result.split()).strip()

def classify_page(text):
    t = " ".join(text.lower().split())
    if "surplus lines" in t and "disclosure" in t: return "Surplus Lines Disclosure"
    if "terrorism" in t and "coverage offering" in t: return "Notice of Terrorism Coverage Offering"
    if "commercial general liability" in t and "limit" in t and "forms" not in t: return "Commercial General Liability Quote"
    if "annual business auto" in t and "quote" in t and "forms" not in t: return "Annual Business Auto Quote"
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

    # CGL, Auto, and Costs Tables
    sections = [
        ("Commercial General Liability Coverage", data['GL_Limits'], "Limit"),
        ("Business Auto Coverage", data['Auto_Limits'], "Limit"),
        ("General Liability Premium Summary", data['GL_Costs'], "Paid in Full"),
    ]
    for title, d_map, header in sections:
        t_data = [[title, header]]
        for k, v in d_map.items(): t_data.append([k, v])
        t = Table(t_data, colWidths=[380, 120]); t.setStyle(table_s)
        elements.append(t); elements.append(Spacer(1, 15))

    # Financial Totals
    elements.append(Table([["Total Premium & Taxes / Fees", data['GL_Total']]], colWidths=[380, 120], style=total_bar_s))
    elements.append(Spacer(1, 15))
    au_costs = [["Business Auto Premium Summary", "Paid in Full"]]
    for k, v in data['Auto_Costs'].items(): au_costs.append([k, v])
    t_au = Table(au_costs, colWidths=[380, 120]); t_au.setStyle(table_s)
    elements.append(t_au)
    elements.append(Table([["Total", data['Auto_Total']]], colWidths=[380, 120], style=total_bar_s))

    doc.build(elements); buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Proposal Builder")
files = st.file_uploader("Upload All Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    text_by_type = {name: "" for name in MASTER_ORDER}; text_by_type["Unclassified/Misc"] = ""
    buckets = {name: [] for name in MASTER_ORDER}; buckets["Unclassified/Misc"] = []
    
    for f in files:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            t = page.extract_text() or ""
            cat = classify_page(t)
            text_by_type[cat] += "\n" + t
            buckets[cat].append(page)

    gl_text, auto_text = text_by_type["Commercial General Liability Quote"], text_by_type["Annual Business Auto Quote"]
    full_text = "\n".join(text_by_type.values())

    s_data = {
        "Insured": extract_clean_identity(full_text, "Name Insured"), 
        "Address": extract_clean_identity(full_text, "Address"),
        "Dates": get_clean_val(full_text, "Period of Insurance", is_date=True),
        "GL_Limits": {
            "General Aggregate Limit": get_clean_val(gl_text, "General Aggregate Limit"),
            "Each Occurrence Limit": get_clean_val(gl_text, "Each Occurrence Limit"),
            "Medical Expense": get_clean_val(gl_text, "Medical Expense")
        },
        "Auto_Limits": {
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
            "Tech Transaction Fee": get_clean_val(auto_text, "Tech Transaction Fee")
        },
        "Auto_Total": get_clean_val(auto_text, "Total")
    }

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 GENERATE QUOTE PACKAGE"):
            writer = pypdf.PdfWriter()
            # Restore the master sequence combining all pages
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            out_buf = io.BytesIO(); writer.write(out_buf)
            st.download_button("💾 DOWNLOAD PACKAGE", out_buf.getvalue(), "Package.pdf")
            
    with col2:
        if st.button("📊 GENERATE SUMMARY"):
            pdf_buf = generate_exec_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY", pdf_buf.getvalue(), "Summary.pdf")
