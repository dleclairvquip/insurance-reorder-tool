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

# vQuip Visual Palette
NAVY = colors.Color(5/255, 18/255, 23/255) 
TEAL = colors.Color(60/255, 148/255, 166/255) 
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

# 2. MASTER SEQUENCE
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

# 3. ABSOLUTE HORIZONTAL LOCK ENGINE
def get_clean_val(text, label, is_date=False):
    """
    Surgical row scan. Identifies the label and searches ONLY its own row 
    for the first valid dollar amount or status word.
    """
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Normalize the label to handle split-word formatting in PDF text layers
        clean_line = " ".join(line.lower().split())
        clean_label = " ".join(label.lower().split())
        
        if clean_label in clean_line:
            # Anchor to this specific horizontal line
            search_area = line
            
            if is_date:
                # MM/DD/YYYY to MM/DD/YYYY
                match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}\s+to\s+\d{1,2}/\d{1,2}/\d{2,4}', search_area)
            else:
                # REGEX: Finds $ currency or 'Excluded'. 
                # (?!.*to) is the 'Magic Bullet' - it forbids picking up the 'to' in header dates.
                match = re.search(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?!\s+to)|Excluded|---', search_area)
            
            if match:
                return match.group(0)
            
            # Contextual Fallback: Check one line down for misaligned PDF grids
            if i + 1 < len(lines):
                next_line = lines[i+1]
                match = re.search(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?!\s+to)|Excluded|---', next_line)
                if match: return match.group(0)
            
    return "---"

def extract_clean_identity(text, label):
    """Surgical identity extraction that stops exactly at metadata."""
    lines = text.split('\n')
    result = ""
    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            result = line.split(label)[-1].strip().replace(":", "")
            if i + 1 < len(lines): result += " " + lines[i+1].strip()
            break
    # Hard stop to prevent 'Period of Insurance' bleed into identity
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

    # CGL & Auto Sections
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
    au_fin = [["Business Auto Premium Summary", "Paid in Full"]]
    for k, v in data['Auto_Costs'].items(): au_fin.append([k, v])
    t_au = Table(au_fin, colWidths=[380, 120]); t_au.setStyle(table_s)
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
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            out_buf = io.BytesIO(); writer.write(out_buf)
            st.download_button("💾 DOWNLOAD PACKAGE", out_buf.getvalue(), "Package.pdf")
            
    with col2:
        if st.button("📊 GENERATE SUMMARY"):
            pdf_buf = generate_exec_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY", pdf_buf.getvalue(), "Summary.pdf")
