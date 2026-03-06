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
st.set_page_config(page_title="Adventure Shield Proposal Builder", page_icon="🛡️", layout="wide")

# vQuip Visual Palette
NAVY = colors.Color(5/255, 18/255, 23/255) 
TEAL = colors.Color(60/255, 148/255, 166/255) 
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

# 2. MASTER SEQUENCE [cite: 184, 198, 219, 238, 261, 271, 279, 316, 334, 365, 394]
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
def get_clean_val(text, label, is_date=False):
    """Normalizes text and label. Uses a tight window for currency to prevent date-bleed."""
    clean_text = " ".join(text.split())
    clean_label = " ".join(label.split())
    idx = clean_text.lower().find(clean_label.lower())
    if idx == -1: return "---"
    
    window_size = 180 if is_date else 70 # Tight window for limits [cite: 213, 230]
    window = clean_text[idx : idx + window_size]
    
    if is_date:
        match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}\s+to\s+\d{1,2}/\d{1,2}/\d{2,4}', window)
    else:
        match = re.search(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|Excluded|N/A', window)
        
    return match.group(0) if match else "---"

def extract_clean_identity(text, label):
    """Extracts identity fields and aggressively strips trailing PDF metadata[cite: 202, 220]."""
    lines = text.split('\n')
    result = ""
    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            result = line.split(label)[-1].strip().replace(":", "")
            if i + 1 < len(lines): result += " " + lines[i+1].strip()
            if i + 2 < len(lines): result += " " + lines[i+2].strip()
            break
    # Aggressive stripping to prevent address bleed [cite: 204, 206, 225]
    result = re.split(r'Period of Insurance|Quote Valid|Date Quoted|Carrier|Date Quoted|Date:', result, flags=re.IGNORECASE)[0]
    return " ".join(result.split()).strip()

def classify_page(text):
    t = " ".join(text.lower().split())
    if "surplus lines" in t and "disclosure" in t: return "Surplus Lines Disclosure" [cite: 184]
    if "terrorism" in t and "coverage offering" in t: return "Notice of Terrorism Coverage Offering" [cite: 334]
    if "small print" in t: return "The Small Print" [cite: 365]
    if "commercial general liability" in t and "limit" in t and "forms" not in t: return "Commercial General Liability Quote" [cite: 198]
    if "annual business auto" in t and "quote" in t and "forms" not in t: return "Annual Business Auto Quote" [cite: 219]
    if "blanket accident" in t and "details" in t: return "Blanket Accident - Full Details" [cite: 238]
    if "forms" in t and "endorsements" in t:
        return "Annual Business Auto Forms & Endorsements" if "auto" in t else "Commercial General Liability Forms & Endorsements" [cite: 261, 271]
    if "transfer risk" in t: return "Why its important to transfer risk and cost" [cite: 279]
    if "how does it work" in t: return "OK so how does it work" [cite: 316]
    if "overall program binding" in t: return "Overall Program Binding" [cite: 394]
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
    # Header Section [cite: 202, 204]
    elements.append(Paragraph("Name Insured", label_s))
    elements.append(Paragraph(data['Insured'], val_s))
    elements.append(Paragraph("Address", label_s))
    elements.append(Paragraph(data['Address'], val_s))
    elements.append(Paragraph("Period of Insurance", label_s))
    elements.append(Paragraph(data['Dates'], val_s))
    elements.append(Spacer(1, 10))

    # CGL Limits [cite: 213]
    gl_t = [["Commercial General Liability Coverage", "Limit"]]
    for k, v in data['GL_Limits'].items(): gl_t.append([k, v])
    t1 = Table(gl_t, colWidths=[380, 120]); t1.setStyle(table_s)
    elements.append(t1); elements.append(Spacer(1, 15))

    # Auto Limits [cite: 230]
    au_t = [["Business Auto Coverage", "Limit"]]
    for k, v in data['Auto_Limits'].items(): au_t.append([k, v])
    t2 = Table(au_t, colWidths=[380, 120]); t2.setStyle(table_s)
    elements.append(t2); elements.append(Spacer(1, 15))

    # Financial Summary [cite: 215, 232]
    fin_gl = [["General Liability Premium Summary", "Paid in Full"]]
    for k, v in data['GL_Costs'].items(): fin_gl.append([k, v])
    t3 = Table(fin_gl, colWidths=[380, 120]); t3.setStyle(table_s)
    elements.append(t3)
    gl_tot = [["Total Premium & Taxes / Fees", data['GL_Total']]]
    t3b = Table(gl_tot, colWidths=[380, 120]); t3b.setStyle(total_bar_s)
    elements.append(t3b); elements.append(Spacer(1, 15))

    fin_au = [["Business Auto Premium Summary", "Paid in Full"]]
    for k, v in data['Auto_Costs'].items(): fin_au.append([k, v])
    t4 = Table(fin_au, colWidths=[380, 120]); t4.setStyle(table_s)
    elements.append(t4)
    au_tot = [["Total", data['Auto_Total']]]
    t4b = Table(au_tot, colWidths=[380, 120]); t4b.setStyle(total_bar_s)
    elements.append(t4b)

    doc.build(elements); buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Proposal Builder")
files = st.file_uploader("Upload all Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}; buckets["Unclassified/Misc"] = []
    text_by_type = {name: "" for name in MASTER_ORDER}; text_by_type["Unclassified/Misc"] = ""
    
    with st.spinner("Analyzing Carrier Documents..."):
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
        "Insured": extract_clean_identity(full_text, "Name Insured"), # [cite: 202]
        "Address": extract_clean_identity(full_text, "Address"), # [cite: 202]
        "Dates": get_clean_val(full_text, "Period of Insurance", is_date=True), # [cite: 204]
        "GL_Limits": { # [cite: 213]
            "General Aggregate Limit": get_clean_val(gl_text, "General Aggregate Limit"),
            "Each Occurrence Limit": get_clean_val(gl_text, "Each Occurrence Limit"),
            "Products-Completed Ops": get_clean_val(gl_text, "Products - Completed Operations"),
            "Personal/Advertising": get_clean_val(gl_text, "Personal and Advertising Injury"),
            "Damage to Rented Premises": get_clean_val(gl_text, "Damage to Premises Rented"),
            "Medical Expense": get_clean_val(gl_text, "Medical Expense Limit")
        },
        "Auto_Limits": { # [cite: 230]
            "BI per Person": get_clean_val(auto_text, "Bodily Injury Liability per Person"),
            "BI per Accident": get_clean_val(auto_text, "Bodily Injury Liability per Accident"),
            "Property Damage per Accident": get_clean_val(auto_text, "Property Damage Liability"),
            "Collision": get_clean_val(auto_text, "Collision"),
            "Comprehensive": get_clean_val(auto_text, "Comprehensive")
        },
        "GL_Costs": { # [cite: 215]
            "Premium": get_clean_val(gl_text, "Premium"),
            "Surplus Lines Tax": get_clean_val(gl_text, "Surplus Lines Tax"),
            "Stamping Fee": get_clean_val(gl_text, "Stamping Fee"),
            "vQuip Platform Fee": get_clean_val(gl_text, "vQuip Platform Fee")
        },
        "GL_Total": get_clean_val(gl_text, "Total Premium & Taxes / Fees"), # [cite: 215]
        "Auto_Costs": { # [cite: 232]
            "Annual Premium": get_clean_val(auto_text, "Annual Premium"),
            "Surplus Lines Tax": get_clean_val(auto_text, "Surplus Lines Tax"),
            "Stamping Fee": get_clean_val(auto_text, "Stamping Fee"),
            "Tech Transaction Fee": get_clean_val(auto_text, "Technology Transaction Fee")
        },
        "Auto_Total": get_clean_val(auto_text, "Total") # [cite: 232]
    }

    col1, col2 = st.columns(2)
    with col1:
        # UPDATED BUTTON WORDING
        if st.button("🚀 GENERATE ADVENTURESHIELD QUOTE PACKAGE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            out_buf = io.BytesIO()
            writer.write(out_buf)
            st.download_button("💾 DOWNLOAD PACKAGE", out_buf.getvalue(), "Package.pdf")
            
    with col2:
        # UPDATED BUTTON WORDING
        if st.button("📊 SUMMARY OF INSURANCE PAGE"):
            pdf_buf = generate_exec_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY", pdf_buf.getvalue(), "Summary.pdf")
