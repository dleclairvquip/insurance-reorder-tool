import streamlit as st
import pypdf
import io
import re
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# 1. PAGE CONFIG
st.set_page_config(page_title="Adventure Shield Toolset", page_icon="🛡️", layout="wide")

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
def get_table_value(text, label):
    """Finds a value appearing on the same line or immediate next line as a label."""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            # Check current line for $ or 'Excluded' or 'N/A'
            matches = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|Excluded|N/A', line)
            if matches: return matches[-1]
            # If not found, check the very next line (common in PDF wraps)
            if i + 1 < len(lines):
                next_matches = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?|Excluded|N/A', lines[i+1])
                if next_matches: return next_matches[-1]
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

# 4. PDF SUMMARY GENERATOR
def create_comprehensive_summary(data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    y = height - 50

    # Header
    p.setFillColorRGB(0, 0.29, 0.6)
    p.rect(0, height - 70, width, 70, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(40, height - 45, "PROPOSAL SUMMARY: " + data['Insured'])
    
    y = height - 100
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"Policy Term: {data['Dates']}")
    
    # --- SECTION: GENERAL LIABILITY ---
    y -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "COMMERCIAL GENERAL LIABILITY LIMITS")
    p.line(40, y-2, 280, y-2)
    y -= 20
    p.setFont("Helvetica", 10)
    for label, val in data['GL_Limits'].items():
        p.drawString(50, y, label)
        p.drawRightString(width - 350, y, val)
        y -= 15

    # --- SECTION: BUSINESS AUTO ---
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "BUSINESS AUTO LIMITS")
    p.line(40, y-2, 200, y-2)
    y -= 20
    p.setFont("Helvetica", 10)
    for label, val in data['Auto_Limits'].items():
        p.drawString(50, y, label)
        p.drawRightString(width - 350, y, val)
        y -= 15

    # --- SECTION: PREMIUM BREAKDOWN (Right Column) ---
    y_premium = height - 100
    p.setFont("Helvetica-Bold", 12)
    p.drawString(350, y_premium, "COST BREAKDOWN (Paid-In-Full)")
    p.line(350, y_premium-2, width-40, y_premium-2)
    y_premium -= 20
    p.setFont("Helvetica", 10)
    for label, val in data['Costs'].items():
        p.drawString(360, y_premium, label)
        p.drawRightString(width - 50, y_premium, val)
        y_premium -= 15
    
    y_premium -= 10
    p.setFont("Helvetica-Bold", 12)
    p.drawString(360, y_premium, "TOTAL ESTIMATED COST:")
    p.drawRightString(width - 50, y_premium, data['Total_Cost'])

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Toolset")
files = st.file_uploader("Upload Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    full_text = ""
    
    for f in files:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text() or ""
            full_text += "\n" + text
            buckets[classify_page(text)].append(page)

    # DATA EXTRACTION
    s_data = {
        "Insured": "Midnight Sun ATV/Snowmobile Tours", # Fallback for this client
        "Dates": "---", "Total_Cost": "---",
        "GL_Limits": {
            "General Aggregate": get_table_value(full_text, "General Aggregate Limit"),
            "Each Occurrence": get_table_value(full_text, "Each Occurrence Limit"),
            "Products/Comp Ops": get_table_value(full_text, "Products - Completed Operations"),
            "Damage to Rented Premises": get_table_value(full_text, "Damage to Premises Rented"),
            "Medical Expense": get_table_value(full_text, "Medical Expense Limit")
        },
        "Auto_Limits": {
            "BI Per Person": get_table_value(full_text, "Bodily Injury Liability per Person"),
            "BI Per Accident": get_table_value(full_text, "Bodily Injury Liability per Accident"),
            "Property Damage": get_table_value(full_text, "Property Damage Liability"),
            "Collision": get_table_value(full_text, "Collision"),
            "Comprehensive": get_table_value(full_text, "Comprehensive")
        },
        "Costs": {
            "GL Premium": get_table_value(full_text, "Premium"),
            "Auto Premium": get_table_value(full_text, "Annual Premium"),
            "Surplus Lines Tax": get_table_value(full_text, "Surplus Lines Tax"),
            "Stamping Fee": get_table_value(full_text, "Stamping Fee"),
            "Platform/Tech Fee": get_table_value(full_text, "vQuip Platform Fee")
        }
    }
    s_data["Total_Cost"] = get_table_value(full_text, "Total Premium &")
    if s_data["Total_Cost"] == "---": s_data["Total_Cost"] = get_table_value(full_text, "Total Premium Cost")

    # DISPLAY
    st.header(f"Project: {s_data['Insured']}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 ASSEMBLE MASTER PACKAGE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            out = io.BytesIO()
            writer.write(out)
            st.download_button("💾 DOWNLOAD PDF", out.getvalue(), "Adventure_Shield_Package.pdf")
    with c2:
        if st.button("📊 GENERATE SUMMARY TOP SHEET"):
            summary_pdf = create_comprehensive_summary(s_data)
            st.download_button("💾 DOWNLOAD SUMMARY", summary_pdf, "Executive_Summary.pdf")
