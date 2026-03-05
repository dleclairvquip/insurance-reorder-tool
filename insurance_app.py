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
    div.stButton > button:first-child { background-color: #004a99; color: white; font-weight: bold; width: 100%; border-radius: 5px; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e1e4e8; }
    </style>
    """, unsafe_allow_html=True)

# 2. LOGIC CONSTANTS
MASTER_ORDER = [
    "Surplus Lines Disclosure", "Commercial General Liability Quote",
    "Annual Business Auto Quote", "Blanket Accident Quote",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost to my clients",
    "OK so how does it work", "Notice of Terrorism Coverage Offering",
    "The Small Print", "Overall Program Binding"
]

# 3. HELPER FUNCTIONS
def extract_value(text, marker, end_marker="\n"):
    try:
        if marker.lower() in text.lower():
            start = text.lower().find(marker.lower()) + len(marker)
            end = text.find(end_marker, start)
            return text[start:end].strip().replace(":", "")
    except: return "Not Found"
    return "Not Found"

def classify_page(text):
    t = " ".join(text.lower().split())
    if "surplus lines" in t and ("disclosure" in t or "notice" in t): return "Surplus Lines Disclosure"
    if "notice of terrorism" in t and "coverage offering" in t: return "Notice of Terrorism Coverage Offering"
    if "annual business auto" in t and "forms" in t and "endorsements" in t: return "Annual Business Auto Forms & Endorsements"
    if "commercial general liability" in t and "forms" in t and "endorsements" in t: return "Commercial General Liability Forms & Endorsements"
    if "commercial general liability" in t and ("limit" in t or "aggregate" in t): return "Commercial General Liability Quote"
    if "annual business auto" in t and ("quote" in t or "loss control" in t): return "Annual Business Auto Quote"
    if "blanket accident" in t and "details" in t: return "Blanket Accident Quote"
    if "important to transfer risk" in t: return "Why its important to transfer risk and cost to my clients"
    if "how does it work" in t: return "OK so how does it work"
    if "small print" in t: return "The Small Print"
    if "program binding" in t: return "Overall Program Binding"
    return "Unclassified/Misc"

def create_summary_pdf(data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    p.setFillColorRGB(0, 0.29, 0.6) 
    p.rect(0, height - 80, width, 80, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(40, height - 50, "ADVENTURE SHIELD | QUOTE SUMMARY")
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, height - 110, f"INSURED: {data['Insured']}")
    p.drawString(40, height - 130, f"PERIOD: {data['Dates']}")
    p.line(40, height - 145, width - 40, height - 145)
    
    y = height - 170
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, f"General Liability - Cost: {data['CGL_Premium']}")
    y -= 20
    p.setFont("Helvetica", 10)
    for k, v in data['CGL_Limits'].items():
        p.drawString(60, y, f"• {k}:")
        p.drawRightString(width-60, y, str(v))
        y -= 15
        
    y -= 25
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, f"Business Auto - Cost: {data['Auto_Premium']}")
    y -= 20
    p.setFont("Helvetica", 10)
    for k, v in data['Auto_Limits'].items():
        p.drawString(60, y, f"• {k}:")
        p.drawRightString(width-60, y, str(v))
        y -= 15
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Toolset")
st.info("Upload your 3 PDFs. The tool will assemble the package AND generate your 1-page summary automatically.")

files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    
    # Data extraction storage
    s_data = {
        "Insured": "Not Found", "Dates": "Not Found", 
        "CGL_Premium": "$0.00", "Auto_Premium": "$0.00", 
        "CGL_Limits": {}, "Auto_Limits": {}
    }

    with st.spinner("Analyzing and extracting data..."):
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                t_low = text.lower()
                
                # Classification for reordering
                cat = classify_page(text)
                buckets[cat].append(page)

                # Data Extraction Logic
                if "name insured" in t_low: s_data["Insured"] = extract_value(text, "Name Insured")
                if "period of insurance" in t_low: s_data["Dates"] = extract_value(text, "Period of Insurance")
                if "general aggregate limit" in t_low:
                    s_data["CGL_Limits"]["General Aggregate"] = extract_value(text, "General Aggregate Limit")
                    s_data["CGL_Limits"]["Each Occurrence"] = extract_value(text, "Each Occurrence Limit")
                if "bodily injury liability per person" in t_low:
                    s_data["Auto_Limits"]["BI per Person"] = extract_value(text, "Bodily Injury Liability per Person")
                    s_data["Auto_Limits"]["BI per Accident"] = extract_value(text, "Bodily Injury Liability per Accident")
                if "paid" in t_low and "full" in t_low:
                    m = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', text)
                    if m:
                        if "commercial general liability" in t_low: s_data["CGL_Premium"] = m[0]
                        elif "annual business auto" in t_low: s_data["Auto_Premium"] = m[0]

    # Display Preview Metrics
    st.header(f"Account: {s_data['Insured']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("GL Total", s_data["CGL_Premium"])
    c2.metric("Auto Total", s_data["Auto_Premium"])
    c3.metric("Pages Found", sum(len(p) for p in buckets.values()))

    st.divider()

    # ACTION BUTTONS
    col_l, col_r = st.columns(2)

    with col_l:
        if st.button("🚀 GENERATE FULL PACKAGE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            out = io.BytesIO()
            writer.write(out)
            st.download_button("💾 DOWNLOAD 11-PAGE PDF", out.getvalue(), f"Full_Package_{s_data['Insured']}.pdf")

    with col_r:
        if st.button("📊 GENERATE SUMMARY TOP-SHEET"):
            pdf_buf = create_summary_pdf(s_data)
            st.download_button("💾 DOWNLOAD 1-PAGE SUMMARY", pdf_buf, f"Summary_{s_data['Insured']}.pdf")
