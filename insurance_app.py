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
st.set_page_config(page_title="vQuip | Adventure Shield Assembler", page_icon="🛡️", layout="wide")

# vQuip Visual Palette
NAVY = colors.Color(5/255, 18/255, 23/255)
TEAL = colors.Color(60/255, 148/255, 166/255)
LIGHT_GRAY = colors.Color(245/255, 245/255, 245/255)

# 2. MASTER SEQUENCE LOGIC
MASTER_ORDER = [
    "Surplus Lines Disclosure", "Commercial General Liability Quote",
    "Annual Business Auto Quote", "Blanket Accident Quote",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost to my clients",
    "OK so how does it work", "Notice of Terrorism Coverage Offering",
    "The Small Print", "Overall Program Binding"
]

# 3. SMART EXTRACTION HELPERS
def get_amount_near(text, label):
    """Finds a dollar amount within a window of a specific label."""
    idx = text.lower().find(label.lower())
    if idx == -1: return "---"
    window = text[max(0, idx-80) : min(len(text), idx+150)]
    amounts = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|Excluded|N/A', window)
    return amounts[0] if amounts else "---"

def extract_field(text, marker):
    """Captures text values like Insured Name or Address."""
    try:
        if marker.lower() in text.lower():
            start = text.lower().find(marker.lower()) + len(marker)
            end = text.find("\n", start)
            return text[start:end].strip().replace(":", "").replace("[", "").replace("]", "")
    except: return "Not Found"
    return "Not Found"

def classify_page(text):
    t = " ".join(text.lower().split())
    # Optimized for AdventSure & vQuip formats
    if "surplus lines" in t and ("disclosure" in t or "notice" in t): return "Surplus Lines Disclosure"
    if "insurance quotation" in t or ("commercial general liability" in t and "limit" in t): return "Commercial General Liability Quote"
    if "annual business auto" in t and "quote" in t: return "Annual Business Auto Quote"
    if "accident protection program" in t or "blanket accident" in t: return "Blanket Accident Quote"
    if "binder agreement" in t or "program binding" in t: return "Overall Program Binding"
    if "forms" in t and "endorsements" in t:
        if "auto" in t: return "Annual Business Auto Forms & Endorsements"
        return "Commercial General Liability Forms & Endorsements"
    return "Unclassified/Misc"

# 4. PROFESSIONAL PDF GENERATOR
def create_master_summary_page(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, textColor=colors.black, spaceAfter=20)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', spaceAfter=2)
    val_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=12, fontName='Helvetica', spaceAfter=15)
    
    elements = []

    # --- Header: Account Info (Image 30dcef style) ---
    elements.append(Paragraph("Name Insured", label_style))
    elements.append(Paragraph(data['Insured'], val_style))
    elements.append(Paragraph("Address", label_style))
    elements.append(Paragraph(data['Address'], val_style))
    elements.append(Paragraph("Period of Insurance", label_style))
    elements.append(Paragraph(data['Dates'], val_style))
    elements.append(Spacer(1, 20))

    # --- GL Limits Table (Image 3136e3 style) ---
    gl_data = [["Coverage", "Limit of Liability"]]
    for k, v in data['GL_Limits'].items(): gl_data.append([k, v])
    
    gl_table = Table(gl_data, colWidths=[380, 120])
    gl_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY])
    ]))
    elements.append(gl_table)
    elements.append(Spacer(1, 25))

    # --- Premium Summary (Image 30dd4c / 30dd84 style) ---
    elements.append(Paragraph("Premium & Fee Breakdown", label_style))
    cost_data = [["Description", "Paid in Full"]]
    for k, v in data['Costs'].items(): cost_data.append([k, v])
    cost_data.append(["TOTAL PACKAGE COST", data['Total']])
    
    cost_table = Table(cost_data, colWidths=[380, 120])
    cost_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), NAVY),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(cost_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- MAIN APP INTERFACE ---
st.title("🛡️ Adventure Shield Master Assembler")
st.markdown("Upload all carrier documents. This tool builds a **Summary Top-Sheet** and reorders your **11-page package** automatically.")

uploaded_files = st.file_uploader("Drop Quote PDFs here", type="pdf", accept_multiple_files=True)

if uploaded_files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    full_text = ""
    
    with st.spinner("Analyzing document structure..."):
        for f in uploaded_files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                txt = page.extract_text() or ""
                full_text += "\n" + txt
                buckets[classify_page(txt)].append(page)

    # DATA EXTRACTION
    s_data = {
        "Insured": extract_field(full_text, "For") if "For:" in full_text else extract_field(full_text, "Name Insured"),
        "Address": extract_field(full_text, "Address") if "Address" in full_text else "Refer to Quote",
        "Dates": extract_field(full_text, "Policy Term") if "Term" in full_text else extract_field(full_text, "Period of Insurance"),
        "GL_Limits": {
            "General Aggregate": get_amount_near(full_text, "General Aggregate"),
            "Each Occurrence": get_amount_near(full_text, "Each Occurrence"),
            "Products/Completed Ops": get_amount_near(full_text, "Products"),
            "Medical Expense": get_amount_near(full_text, "Medical Expense")
        },
        "Costs": {
            "Carrier Premium": get_amount_near(full_text, "General Liability"),
            "Surplus Lines Tax": get_amount_near(full_text, "Surplus Lines Tax"),
            "Stamping Fees": get_amount_near(full_text, "Stamp Fee"),
            "Policy/Admin Fees": get_amount_near(full_text, "Policy Fee")
        },
        "Total": get_amount_near(full_text, "TOTAL PREMIUM COST") if "TOTAL PREMIUM" in full_text else get_amount_near(full_text, "Total Premium & Taxes")
    }

    # DASHBOARD & ACTIONS
    st.header(f"Account: {s_data['Insured']}")
    if st.button("🚀 GENERATE COMPLETE ADVENTURE SHIELD PACKAGE"):
        # 1. Create Summary Page
        summary_pdf_stream = create_master_summary_page(s_data)
        summary_reader = pypdf.PdfReader(summary_pdf_stream)
        
        # 2. Start Assembly
        writer = pypdf.PdfWriter()
        writer.add_page(summary_reader.pages[0]) # Add Summary First
        
        # 3. Add Carrier Pages in Order
        for cat in MASTER_ORDER:
            for p in buckets[cat]: writer.add_page(p)
        for p in buckets["Unclassified/Misc"]: writer.add_page(p)
        
        final_out = io.BytesIO()
        writer.write(final_out)
        
        st.balloons()
        st.download_button(
            label="💾 DOWNLOAD COMPLETE PACKAGE (Summary + Quote Docs)",
            data=final_out.getvalue(),
            file_name=f"Adventure_Shield_{s_data['Insured']}.pdf",
            mime="application/pdf"
        )
