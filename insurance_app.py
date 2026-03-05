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

# 2. HELPER FUNCTIONS
def get_amount_near(text, label):
    """Finds a dollar amount within a 100-character window of a label."""
    idx = text.lower().find(label.lower())
    if idx == -1: return "$0.00"
    window = text[max(0, idx-60) : min(len(text), idx+120)]
    amounts = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', window)
    return amounts[0] if amounts else "$0.00"

def extract_label_value(text, marker):
    """Extracts text following a marker up to the next newline."""
    try:
        if marker.lower() in text.lower():
            start = text.lower().find(marker.lower()) + len(marker)
            end = text.find("\n", start)
            return text[start:end].strip().replace(":", "")
    except: return "---"
    return "---"

# 3. EXECUTIVE PDF GENERATOR (Styled for your screenshots)
def create_executive_summary(data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    
    # Header Section
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, height - 60, "Name Insured")
    p.setFont("Helvetica", 14)
    p.drawString(200, height - 60, data['Insured']) # Styled like image_30dcef.png 
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, height - 90, "Address")
    p.setFont("Helvetica", 14)
    p.drawString(200, height - 90, data['Address']) # Styled like image_30dcef.png 
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, height - 150, "Period of Insurance")
    p.setFont("Helvetica", 14)
    p.drawString(40, height - 180, data['Dates']) # Styled like image_30dcef.png 

    # --- GL PREMIUM SUMMARY (Styled like image_30dd4c.png) ---
    y = height - 240
    p.setFillColorRGB(0.05, 0.18, 0.23) # Dark Blue Header
    p.rect(40, y, width - 80, 20, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y + 6, "General Liability Premium Summary")
    p.drawRightString(width - 50, y + 6, "Paid in Full")
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    gl_costs = [
        ("Premium", data['GL_Prem']),
        ("Surplus Lines Tax:", data['GL_Tax']),
        ("Stamping Fee", data['GL_Stamp']),
        ("vQuip Platform Fee", data['GL_Fee'])
    ]
    
    for label, val in gl_costs:
        y -= 20
        p.drawString(50, y, label)
        p.drawRightString(width - 50, y, val)
    
    y -= 25
    p.setFillColorRGB(0.24, 0.58, 0.65) # Teal Total Bar
    p.rect(40, y, width - 80, 25, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y + 8, "Total Premium & Taxes / Fees")
    p.drawRightString(width - 50, y + 8, data['GL_Total'])

    # --- AUTO PREMIUM SUMMARY (Styled like image_30dd84.png) ---
    y -= 50
    p.setFillColorRGB(0.05, 0.18, 0.23)
    p.rect(40, y, width - 80, 20, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y + 6, "Business Auto Premium Summary")
    p.drawRightString(width - 50, y + 6, "Paid in Full")
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    auto_costs = [
        ("Annual Premium", data['Auto_Prem']),
        ("Surplus Lines Tax", data['Auto_Tax']),
        ("Stamping Fee", data['Auto_Stamp']),
        ("Technology Transaction Fee - Annual", data['Auto_Fee'])
    ]
    
    for label, val in auto_costs:
        y -= 20
        p.drawString(50, y, label)
        p.drawRightString(width - 50, y, val)
        
    y -= 25
    p.setFillColorRGB(0.24, 0.58, 0.65)
    p.rect(40, y, width - 80, 25, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y + 8, "Total")
    p.drawRightString(width - 50, y + 8, data['Auto_Total'])

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Executive Toolset")
files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)

if files:
    full_text = ""
    for f in files:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            full_text += "\n" + (page.extract_text() or "")

    # DATA EXTRACTION
    s_data = {
        "Insured": extract_label_value(full_text, "Name Insured"), # 
        "Address": extract_label_value(full_text, "Address"), # 
        "Dates": extract_label_value(full_text, "Period of Insurance"), # 
        
        # GL Data (Image_30dd4c.png context)
        "GL_Prem": get_amount_near(full_text, "Premium"), # 
        "GL_Tax": get_amount_near(full_text, "Surplus Lines Tax:"), # 
        "GL_Stamp": get_amount_near(full_text, "Stamping Fee"), # 
        "GL_Fee": get_amount_near(full_text, "vQuip Platform Fee"), # 
        "GL_Total": get_amount_near(full_text, "Total Premium & Taxes / Fees"), # 
        
        # Auto Data (Image_30dd84.png context)
        "Auto_Prem": get_amount_near(full_text, "Annual Premium"), # 
        "Auto_Tax": get_amount_near(full_text, "Surplus Lines Tax"), # 
        "Auto_Stamp": get_amount_near(full_text, "Stamping Fee"), # 
        "Auto_Fee": get_amount_near(full_text, "Technology Transaction Fee - Annual"), # 
        "Auto_Total": get_amount_near(full_text, "Total") # 
    }

    # PREVIEW & DOWNLOAD
    st.subheader(f"Summary Preview for {s_data['Insured']}")
    if st.button("🚀 GENERATE EXECUTIVE SUMMARY PDF"):
        sum_pdf = create_executive_summary(s_data)
        st.download_button("💾 DOWNLOAD SUMMARY", sum_pdf, "Executive_Summary.pdf")
