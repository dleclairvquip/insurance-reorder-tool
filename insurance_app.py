import streamlit as st
import pypdf
import io
import re
from datetime import datetime

# 1. THEME & PAGE CONFIG
st.set_page_config(page_title="Adventure Shield Toolset", page_icon="🛡️", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div.stButton > button:first-child { background-color: #004a99; color: white; font-weight: bold; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# 2. HELPER FUNCTIONS
def extract_value(text, marker, end_marker="\n"):
    """Finds text between two points."""
    try:
        if marker.lower() in text.lower():
            start = text.lower().find(marker.lower()) + len(marker)
            end = text.find(end_marker, start)
            return text[start:end].strip()
    except:
        return "Not Found"
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

# --- MAIN APP LAYOUT ---
st.title("🛡️ Adventure Shield Toolset")
t1, t2 = st.tabs(["🔄 Package Assembler", "📊 Quote Summary"])

# --- TAB 1: ASSEMBLER ---
with t1:
    st.markdown("### **Reorder PDF Pages**")
    files = st.file_uploader("Upload PDFs for Reordering", type="pdf", accept_multiple_files=True, key="assembler")
    
    if files:
        MASTER_ORDER = ["Surplus Lines Disclosure", "Commercial General Liability Quote", "Annual Business Auto Quote", "Blanket Accident Quote", "Commercial General Liability Forms & Endorsements", "Annual Business Auto Forms & Endorsements", "Why its important to transfer risk and cost to my clients", "OK so how does it work", "Notice of Terrorism Coverage Offering", "The Small Print", "Overall Program Binding"]
        buckets = {name: [] for name in MASTER_ORDER}
        buckets["Unclassified/Misc"] = []
        
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                cat = classify_page(page.extract_text() or "")
                buckets[cat].append(page)

        if st.button("🚀 ASSEMBLE PACKAGE"):
            writer = pypdf.PdfWriter()
            for cat in MASTER_ORDER:
                for p in buckets[cat]: writer.add_page(p)
            for p in buckets["Unclassified/Misc"]: writer.add_page(p)
            
            final_pdf = io.BytesIO()
            writer.write(final_pdf)
            st.balloons()
            st.download_button("💾 DOWNLOAD COMPLETED PACKAGE", data=final_pdf.getvalue(), file_name=f"Reordered_Package.pdf")

# --- TAB 2: SUMMARY ---
with t2:
    st.markdown("### **Instant Quote Summary**")
    st.info("Upload your quote documents here to automatically extract key details.")
    summary_files = st.file_uploader("Upload Quote PDFs", type="pdf", accept_multiple_files=True, key="summary")

    if summary_files:
        summary_data = {"Insured": "Unknown", "Address": "Unknown", "Dates": "Unknown", "CGL Premium": "$0.00", "Auto Premium": "$0.00"}
        
        for f in summary_files:
            full_text = ""
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                full_text += text
                
                # Logic to grab Insured Name
                if "Name Insured" in text:
                    summary_data["Insured"] = extract_value(text, "Name Insured")
                
                # Logic to grab Premiums (looking for the Paid-in-Full amounts)
                if "Commercial General Liability" in text and "Paid-in-Full" in text:
                    # Look for the first $ amount after the premium table start
                    matches = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', text)
                    if matches: summary_data["CGL Premium"] = matches[0]

                if "Annual Business Auto" in text and "Paid in Full" in text:
                    matches = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', text)
                    if matches: summary_data["Auto Premium"] = matches[0]
                    
                if "Period of Insurance" in text:
                    summary_data["Dates"] = extract_value(text, "Period of Insurance")

        # Display the Summary Card
        st.subheader(f"Summary for: {summary_data['Insured']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Insured Address", summary_data["Insured"], delta="Verified")
        c2.metric("Effective Dates", summary_data["Dates"])
        
        st.divider()
        
        c4, c5 = st.columns(2)
        c4.subheader("🛡️ General Liability")
        c4.write(f"**Total Cost:** {summary_data['CGL Premium']}")
        
        c5.subheader("🚐 Business Auto")
        c5.write(f"**Total Cost:** {summary_data['Auto Premium']}")
