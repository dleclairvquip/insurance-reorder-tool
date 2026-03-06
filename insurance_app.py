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

NAVY = colors.Color(5/255, 18/255, 23/255) 
TEAL = colors.Color(60/255, 148/255, 166/255) 
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

MASTER_ORDER = [
    "Surplus Lines Disclosure",
    "Commercial General Liability Quote",
    "Annual Business Auto Quote",
    "Blanket Accident - Full Details",
    "Forms & Endorsements",
    "Why its important",
    "How it works",
    "Terrorism Notice",
    "Small Print",
    "Binding"
]

# 2. THE NEW SECTION-AWARE ENGINE
def get_clean_val(text, label, section_header=None, is_date=False):
    """
    1. Isolates the relevant section to prevent data bleed.
    2. Uses a horizontal lock to find the value.
    3. Blocks date ranges using negative lookahead.
    """
    search_text = text
    if section_header:
        parts = re.split(section_header, text, flags=re.IGNORECASE)
        if len(parts) > 1:
            # Only look at the text AFTER the section header
            search_text = parts[1].split("Premium Summary")[0] 

    lines = search_text.split('\n')
    for i, line in enumerate(lines):
        clean_line = " ".join(line.lower().split())
        clean_label = " ".join(label.lower().split())
        
        if clean_label in clean_line:
            # Horizontal plane capture
            search_area = line
            if i + 1 < len(lines): search_area += " " + lines[i+1] # Catch wraps
            
            if is_date:
                match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}\s+to\s+\d{1,2}/\d{1,2}/\d{2,4}', search_area)
            else:
                # The 'Magic Bullet': (?!.*to) forbids picking up the 'to' in date ranges
                match = re.search(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?!\s+to)|Excluded|---', search_area)
            
            if match: return match.group(0)
    return "---"

def extract_identity(text, label):
    """Cleanly extracts Name/Address and stops before the first table."""
    parts = re.split(label, text, flags=re.IGNORECASE)
    if len(parts) > 1:
        # Stop at 'Period of Insurance' or the first table header
        val = re.split(r'Period of Insurance|Commercial General', parts[1], flags=re.IGNORECASE)[0]
        return " ".join(val.replace(":", "").split()).strip()
    return "---"

# 3. PDF PROCESSING
st.title("🛡️ Adventure Shield Proposal Builder")
files = st.file_uploader("Upload Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    full_text = ""
    gl_text = ""
    au_text = ""
    all_pages = []

    for f in files:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            t = page.extract_text() or ""
            full_text += "\n" + t
            if "Commercial General Liability" in t: gl_text += "\n" + t
            if "Business Auto" in t: au_text += "\n" + t
            all_pages.append(page)

    s_data = {
        "Insured": extract_identity(full_text, "Name Insured"),
        "Address": extract_identity(full_text, "Address"),
        "Dates": get_clean_val(full_text, "Period of Insurance", is_date=True),
        "GL_Limits": {
            "General Aggregate": get_clean_val(gl_text, "General Aggregate", "Commercial General"),
            "Each Occurrence": get_clean_val(gl_text, "Each Occurrence", "Commercial General"),
            "Medical Expense": get_clean_val(gl_text, "Medical Expense", "Commercial General")
        },
        "Auto_Limits": {
            "Collision": get_clean_val(au_text, "Collision", "Business Auto"),
            "Comprehensive": get_clean_val(au_text, "Comprehensive", "Business Auto")
        },
        "GL_Total": get_clean_val(gl_text, "Total Premium & Taxes / Fees"),
        "Auto_Total": get_clean_val(au_text, "Total", "Business Auto Premium Summary")
    }

    if st.button("📊 GENERATE NEW SUMMARY"):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=LETTER)
        styles = getSampleStyleSheet()
        elements = []
        
        # Identity
        elements.append(Paragraph(f"<b>Insured:</b> {s_data['Insured']}", styles['Normal']))
        elements.append(Paragraph(f"<b>Period:</b> {s_data['Dates']}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # GL Table
        gl_t = [["GL Coverage", "Limit"]]
        for k, v in s_data['GL_Limits'].items(): gl_t.append([k, v])
        t1 = Table(gl_t, colWidths=[300, 150])
        t1.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), NAVY), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        elements.append(t1)
        
        doc.build(elements)
        st.download_button("💾 DOWNLOAD SUMMARY", buffer.getvalue(), "Summary.pdf")
