import streamlit as st
import pypdf
import io
import re
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Adventure Shield Toolset", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div.stButton > button:first-child { background-color: #004a99; color: white; font-weight: bold; width: 100%; border-radius: 5px; height: 3em; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e1e4e8; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONSTANTS & ORDERING
MASTER_ORDER = [
    "Surplus Lines Disclosure", "Commercial General Liability Quote",
    "Annual Business Auto Quote", "Blanket Accident Quote",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost to my clients",
    "OK so how does it work", "Notice of Terrorism Coverage Offering",
    "The Small Print", "Overall Program Binding"
]

# 3. EXTRACTION & CLASSIFICATION ENGINES
def extract_value(text, marker, end_marker="\n"):
    try:
        if marker.lower() in text.lower():
            start = text.lower().find(marker.lower()) + len(marker)
            # Find the end of the line or a specific marker
            end = text.find(end_marker, start)
            if end == -1: end = start + 50 # Fallback
            return text[start:end].strip().replace(":", "").replace("[", "").replace("]", "")
    except: return "---"
    return "---"

def classify_page(text):
    t = " ".join(text.lower().split())
    if "surplus lines" in t and ("disclosure" in t or "notice" in t): return "Surplus Lines Disclosure"
    if "notice of terrorism" in t and "coverage offering" in t: return "Notice of Terrorism Coverage Offering"
    if "annual business auto" in t and "forms" in t and "endorsements" in t: return "Annual Business Auto Forms & Endorsements"
    if "commercial general liability" in t and "forms" in t and "endorsements" in t: return "Commercial General Liability Forms & Endorsements"
    if "commercial general liability" in t and ("limit" in t or "aggregate" in t) and "forms" not in t: return "Commercial General Liability Quote"
    if "annual business auto" in t and ("quote" in t or "loss control" in t) and "forms" not in t: return "Annual Business Auto Quote"
    if "blanket accident" in t and "details" in t: return "Blanket Accident Quote"
    if "important to transfer risk" in t: return "Why its important to transfer risk and cost to my clients"
    if "how does it work" in t: return "OK so how does it work"
    if "small print" in t: return "The Small Print"
    if "overall program binding" in t: return "Overall Program Binding"
    return "Unclassified/Misc"

# 4. EXECUTIVE PDF GENERATOR
def create_executive_summary(data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER

    # Header section
    p.setFont("Helvetica-Bold", 16)
    p.drawString(40, height - 50, "INSURANCE QUOTATION SUMMARY")
    p.setFont("Helvetica", 10)
    p.drawString(40, height - 65, f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    
    # Client Info Box
    p.setStrokeColorRGB(0, 0.29, 0.6)
    p.rect(40, height - 120, width - 80, 45, stroke=1, fill=0)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, height - 95, f"FOR: {data['Insured']}")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 110, f"POLICY TERM: {data['Dates']}")

    # GL Section
    y = height - 150
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0, 0.29, 0.6)
    p.drawString(40, y, "COMMERCIAL GENERAL LIABILITY")
    p.setFillColor(colors.black)
    
    y -= 20
    p.setFont("Helvetica", 10)
    for label, val in data['GL_Limits'].items():
        p.drawString(60, y, label)
        p.drawRightString(width - 60, y, str(val))
        y -= 15

    # Auto Section
    y -= 15
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0, 0.29, 0.6)
    p.drawString(40, y, "ANNUAL BUSINESS AUTO")
    p.setFillColor(colors.black)
    
    y -= 20
    p.setFont("Helvetica", 10)
    for label, val in data['Auto_Limits'].items():
        p.drawString(60, y, label)
        p.drawRightString(width - 60, y, str(val))
        y -= 15

    # Totals Section
    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "FINANCIAL SUMMARY")
    p.line(40, y - 5, width - 40, y - 5)
    
    y -= 25
    p.setFont("Helvetica", 11)
    p.drawString(60, y, "General Liability Premium")
    p.drawRightString(width - 60, y, data['GL_Premium'])
    y -= 20
    p.drawString(60, y, "Business Auto Premium")
    p.drawRightString(width - 60, y, data['Auto_Premium'])
    
    y -= 30
    p.setFont("Helvetica-Bold", 13)
    p.drawString(60, y, "ESTIMATED PACKAGE TOTAL")
    p.drawRightString(width - 60, y, data['Total_Cost'])

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- MAIN APP INTERFACE ---
st.title("🛡️ Adventure Shield Toolset")
st.markdown("Upload your quote documents to generate the finalized package and executive summary.")

files = st.file_uploader("Upload PDF Documents", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    
    # Universal Data Scraper
    s_data = {
        "Insured": "Not Found", "Dates": "Not Found", "Total_Cost": "$0.00",
        "GL_Premium": "$0.00", "Auto_Premium": "$0.00",
        "GL_Limits": {}, "Auto_Limits": {}
    }

    with st.spinner("Processing documents and extracting data..."):
        full_text_dump = ""
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                full_text_dump += text
                
                # Sort page for reordering
                cat = classify_page(text)
                buckets[cat].append(page)

        # Extraction Logic (Supporting both carrier formats)
        t_low = full_text_dump.lower()
        
        # Insured & Term
        if "for:" in t_low: s_data["Insured"] = extract_value(full_text_dump, "For:")
        elif "name insured" in t_low: s_data["Insured"] = extract_value(full_text_dump, "Name Insured")
        
        if "policy term:" in t_low: s_data["Dates"] = extract_value(full_text_dump, "Policy Term:")
        elif "period of insurance" in t_low: s_data["Dates"] = extract_value(full_text_dump, "Period of Insurance")

        # Limits (CGL)
        if "general aggregate" in t_low:
            s_data["GL_Limits"]["General Aggregate"] = extract_value(full_text_dump, "General Aggregate")
            s_data["GL_Limits"]["Each Occurrence"] = extract_value(full_text_dump, "Each Occurrence")
        
        # Limits (Auto)
        if "bodily injury liability per person" in t_low:
            s_data["Auto_Limits"]["BI per Person"] = extract_value(full_text_dump, "Bodily Injury Liability per Person")
            s_data["Auto_Limits"]["Property Damage"] = extract_value(full_text_dump, "Property Damage Liability per Accident")

        # Premium Logic
        prices = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', full_text_dump)
        if "total premium cost" in t_low: s_data["Total_Cost"] = prices[0] if prices else "$0.00"
        
    # DISPLAY DASHBOARD
    st.header(f"Account: {s_data['Insured']}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Cost", s_data["Total_Cost"])
    m2.metric("Term", s_data["Dates"])
    m3.metric("Pages Analyzed", sum(len(p) for p in buckets.values()))

    st.divider()
    
    # ACTIONS
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 GENERATE FULL 11-PAGE PACKAGE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            
            final_out = io.BytesIO()
            writer.write(final_out)
            st.download_button("💾 DOWNLOAD FULL PDF", final_out.getvalue(), "Full_Adventure_Shield.pdf")

    with c2:
        if st.button("📊 GENERATE 1-PAGE TOP SHEET"):
            summary_buf = create_executive_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY PDF", summary_buf, "Quote_Summary.pdf")
