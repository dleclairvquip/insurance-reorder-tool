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

# Custom UI Styling for a clean, professional feel
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
    """Extracts text following a specific keyword marker."""
    try:
        if marker.lower() in text.lower():
            start = text.lower().find(marker.lower()) + len(marker)
            end = text.find(end_marker, start)
            return text[start:end].strip().replace(":", "")
    except: return "Not Found"
    return "Not Found"

def classify_page(text):
    """Categorizes PDF pages based on specific insurance keywords."""
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
    """Generates a professional 1-page PDF Executive Summary."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    
    # Branded Header Bar
    p.setFillColorRGB(0, 0.29, 0.6) 
    p.rect(0, height - 80, width, 80, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(40, height - 50, "ADVENTURE SHIELD | QUOTE SUMMARY")
    
    # Account Details
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, height - 110, f"INSURED: {data['Insured']}")
    p.drawString(40, height - 130, f"PERIOD: {data['Dates']}")
    p.line(40, height - 145, width - 40, height - 145)
    
    # CGL Section
    y = height - 170
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, f"General Liability - Cost: {data['CGL_Premium']}")
    y -= 20
    p.setFont("Helvetica", 10)
    for k, v in data['CGL_Limits'].items():
        p.drawString(60, y, f"• {k}:")
        p.drawRightString(width-60, y, str(v))
        y -= 15
        
    # Auto Section
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

# --- MAIN APP INTERFACE ---
st.title("🛡️ Adventure Shield Toolset")
t1, t2 = st.tabs(["🔄 Package Assembler", "📊 Quote Summary"])

# TAB 1: ASSEMBLER
with t1:
    st.markdown("### **Reorder PDF Pages**")
    files = st.file_uploader("Upload PDFs for Reordering", type="pdf", accept_multiple_files=True, key="asm")
    if files:
        buckets = {name: [] for name in MASTER_ORDER}
        buckets["Unclassified/Misc"] = []
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                cat = classify_page(page.extract_text() or "")
                buckets[cat].append(page)
        
        if st.button("🚀 ASSEMBLE FINAL PACKAGE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            
            out = io.BytesIO()
            writer.write(out)
            st.balloons()
            st.download_button("💾 DOWNLOAD PACKAGE", out.getvalue(), "Adventure_Shield_Package.pdf")

# TAB 2: SUMMARY & EXTRACTION
with t2:
    st.markdown("### **Instant Quote Summary**")
    s_files = st.file_uploader("Upload Quote Documents", type="pdf", accept_multiple_files=True, key="sum")
    if s_files:
        s_data = {
            "Insured": "Not Found", 
            "Dates": "Not Found", 
            "CGL_Premium": "$0.00", 
            "Auto_Premium": "$0.00", 
            "CGL_Limits": {}, 
            "Auto_Limits": {}
        }
        
        for f in s_files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                t_low = text.lower()
                
                # Extract Insured & Dates
                if "name insured" in t_low: s_data["Insured"] = extract_value(text, "Name Insured")
                if "period of insurance" in t_low: s_data["Dates"] = extract_value(text, "Period of Insurance")
                
                # Extract CGL Limits
                if "general aggregate limit" in t_low:
                    s_data["CGL_Limits"]["General Aggregate"] = extract_value(text, "General Aggregate Limit")
                    s_data["CGL_Limits"]["Each Occurrence"] = extract_value(text, "Each Occurrence Limit")
                    s_data["CGL_Limits"]["Medical Expense"] = extract_value(text, "Medical Expense Limit")
                
                # Extract Auto Limits
                if "bodily injury liability per person" in t_low:
                    s_data["Auto_Limits"]["BI per Person"] = extract_value(text, "Bodily Injury Liability per Person")
                    s_data["Auto_Limits"]["BI per Accident"] = extract_value(text, "Bodily Injury Liability per Accident")
                
                # Extract Premiums
                if "paid" in t_low and "full" in t_low:
                    m = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', text)
                    if m:
                        if "commercial general liability" in t_low: s_data["CGL_Premium"] = m[0]
                        elif "annual business auto" in t_low: s_data["Auto_Premium"] = m[0]
        
        # Display Results
        st.subheader(f"Proposal Data: {s_data['Insured']}")
        c1, c2 = st.columns(2)
        c1.metric("GL Total Cost", s_data["CGL_Premium"])
        c2.metric("Auto Total Cost", s_data["Auto_Premium"])
        
        st.divider()
        if st.button("📄 GENERATE 1-PAGE SUMMARY PDF"):
            pdf_buf = create_summary_pdf(s_data)
            st.download_button("💾 DOWNLOAD EXECUTIVE SUMMARY", pdf_buf, f"Summary_{s_data['Insured']}.pdf")
