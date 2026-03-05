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

# Custom UI Styling
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div.stButton > button:first-child { background-color: #004a99; color: white; font-weight: bold; width: 100%; }
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
    p.drawString(40, height - 130, f"DATES: {data['Dates']}")
    p.line(40, height - 145, width - 40, height - 145)
    
    y = height - 170
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, f"General Liability - Total Cost: {data['CGL_Premium']}")
    y -= 20
    p.setFont("Helvetica", 10)
    for k, v in data['CGL_Limits'].items():
        p.drawString(60, y, f"{k}:")
        p.drawRightString(width-60, y, str(v))
        y -= 15
        
    y -= 20
    p.setFont("Helvetica-Bold", 14)
    p.drawString(40, y, f"Business Auto - Total Cost: {data['Auto_Premium']}")
    y -= 20
    p.setFont("Helvetica", 10)
    for k, v in data['Auto_Limits'].items():
        p.drawString(60, y, f"{k}:")
        p.drawRightString(width-60, y, str(v))
        y -= 15
        
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Toolset")
t1, t2 = st.tabs(["🔄 Package Assembler", "📊 Quote Summary"])

with t1:
