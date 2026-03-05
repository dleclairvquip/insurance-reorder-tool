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
    div.stButton > button:first-child { background-color: #004a99; color: white; font-weight: bold; width: 100%; border-radius: 5px; height: 3.5em; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e1e4e8; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONSTANTS
MASTER_ORDER = [
    "Surplus Lines Disclosure", "Commercial General Liability Quote",
    "Annual Business Auto Quote", "Blanket Accident Quote",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost to my clients",
    "OK so how does it work", "Notice of Terrorism Coverage Offering",
    "The Small Print", "Overall Program Binding"
]

# 3. EXTRACTION ENGINES
def get_amount_near(text, label):
    """Finds a dollar amount within a 100-character window of a label."""
    idx = text.lower().find(label.lower())
    if idx == -1: return "---"
    # Look 50 characters before and 100 characters after the label
    window = text[max(0, idx-60) : min(len(text), idx+120)]
    amounts = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', window)
    return amounts[0] if amounts else "---"

def extract_label_value(text, marker):
    """Standard extraction for non-currency text fields."""
    try:
        if marker.lower() in text.lower():
            start = text.lower().find(marker.lower()) + len(marker)
            end = text.find("\n", start)
            return text[start:end].strip().replace(":", "").replace("[", "").replace("]", "")
    except: return "Not Found"
    return "Not Found"

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

# 4. PDF SUMMARY GENERATOR
def create_executive_summary(data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER

    p.setFont("Helvetica-Bold", 18)
    p.drawString(40, height - 50, "INSURANCE QUOTATION SUMMARY")
    p.setFont("Helvetica", 10)
    p.drawString(40, height - 65, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    
    p.setStrokeColorRGB(0, 0.29, 0.6)
    p.rect(40, height - 120, width - 80, 45, stroke=1, fill=0)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, height - 95, f"INSURED: {data['Insured']}")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 110, f"TERM: {data['Dates']}")

    sections = [
        ("COMMERCIAL GENERAL LIABILITY", data['GL_Limits'], data['GL_Premium']),
        ("ANNUAL BUSINESS AUTO / ACCIDENT", data['Auto_Limits'], data['Auto_Premium'])
    ]

    y = height - 150
    for title, limits, prem in sections:
        y -= 25
        p.setFont("Helvetica-Bold", 12)
        p.setFillColorRGB(0, 0.29, 0.6)
        p.drawString(40, y, title)
        p.setFillColor(colors.black)
        y -= 20
        p.setFont("Helvetica", 10)
        for label, val in limits.items():
            p.drawString(60, y, label)
            p.drawRightString(width - 60, y, str(val))
            y -= 15
        p.setFont("Helvetica-Bold", 10)
        p.drawString(60, y, "Estimated Section Premium:")
        p.drawRightString(width - 60, y, prem)
        y -= 15

    y -= 40
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, "TOTAL ESTIMATED PACKAGE COST")
    p.line(40, y - 5, width - 40, y - 5)
    p.drawRightString(width - 60, y, data['Total_Cost'])

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Toolset")
files = st.file_uploader("Upload all Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    
    s_data = {
        "Insured": "---", "Dates": "---", "Total_Cost": "---",
        "GL_Premium": "---", "Auto_Premium": "---",
        "GL_Limits": {}, "Auto_Limits": {}
    }

    with st.spinner("Analyzing Architecture & Extracting Data..."):
        full_text = ""
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                full_text += " " + text
                cat = classify_page(text)
                buckets[cat].append(page)

        # Unified Extraction Logic
        # 1. Identity
        if "for:" in full_text.lower(): s_data["Insured"] = extract_label_value(full_text, "For:")
        elif "name insured" in full_text.lower(): s_data["Insured"] = extract_label_value(full_text, "Name Insured")
        
        if "policy term:" in full_text.lower(): s_data["Dates"] = extract_label_value(full_text, "Policy Term:")
        elif "period of insurance" in full_text.lower(): s_data["Dates"] = extract_label_value(full_text, "Period of Insurance")

        # 2. GL Data
        s_data["GL_Limits"]["General Aggregate"] = get_amount_near(full_text, "General Aggregate")
        s_data["GL_Limits"]["Each Occurrence"] = get_amount_near(full_text, "Each Occurrence")
        s_data["GL_Premium"] = get_amount_near(full_text, "General Liability")

        # 3. Auto/Accident Data
        if "maximum medical expense" in full_text.lower():
            s_data["Auto_Limits"]["Max Medical"] = get_amount_near(full_text, "Maximum Medical Expense Benefit")
            s_data["Auto_Limits"]["Deductible"] = get_amount_near(full_text, "Deductible Amount per Claim")
            s_data["Auto_Premium"] = get_amount_near(full_text, "Accident Medical")
        else:
            s_data["Auto_Limits"]["BI per Person"] = get_amount_near(full_text, "Bodily Injury Liability per Person")
            s_data["Auto_Premium"] = get_amount_near(full_text, "Annual Business Auto")

        # 4. Total Cost
        s_data["Total_Cost"] = get_amount_near(full_text, "TOTAL PREMIUM COST")
        if s_data["Total_Cost"] == "---":
            s_data["Total_Cost"] = get_amount_near(full_text, "Total Premium Including")

    # DASHBOARD
    st.header(f"Account: {s_data['Insured']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Package Cost", s_data["Total_Cost"])
    c2.metric("Term", s_data["Dates"])
    c3.metric("Pages Sorted", sum(len(p) for p in buckets.values()))

    st.divider()
    
    colL, colR = st.columns(2)
    with colL:
        if st.button("🚀 ASSEMBLE 11-PAGE MASTER PACKAGE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            out = io.BytesIO()
            writer.write(out)
            st.download_button("💾 DOWNLOAD MASTER PDF", out.getvalue(), f"Package_{s_data['Insured']}.pdf")

    with colR:
        if st.button("📊 GENERATE EXECUTIVE TOP SHEET"):
            summary_pdf = create_executive_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY PDF", summary_pdf, f"Summary_{s_data['Insured']}.pdf")
