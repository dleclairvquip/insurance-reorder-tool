import streamlit as st
import pypdf
import io
import pandas as pd
from datetime import datetime

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Insurance PDF Builder", page_icon="🛡️", layout="wide")

# 2. THE PERFECTED MASTER SEQUENCE
MASTER_ORDER = [
    "Surplus Lines Disclosure",
    "Commercial General Liability Quote",
    "Annual Business Auto Quote",
    "Blanket Accident Quote",
    "Commercial General Liability Forms & Endorsements",  # Always first
    "Annual Business Auto Forms & Endorsements",         # Always second
    "Why its important to transfer risk and cost to my clients",
    "OK so how does it work",
    "Notice of Terrorism Coverage Offering",             # Correctly before Small Print
    "The Small Print",
    "Overall Program Binding"
]

def classify_page(text):
    """Refined matching logic to prevent misclassification."""
    t = " ".join(text.lower().split())
    
    # --- DISCLOSURES ---
    if "surplus lines" in t and ("disclosure" in t or "notice" in t): 
        return "Surplus Lines Disclosure"
    
    # --- TERRORISM (Check this early to avoid CGL confusion) ---
    if "notice of terrorism" in t and "coverage offering" in t: 
        return "Notice of Terrorism Coverage Offering"
    
    # --- FORMS & ENDORSEMENTS (Auto checked BEFORE CGL to prevent misclassification) ---
    if "annual business auto" in t and "forms" in t and "endorsements" in t: 
        return "Annual Business Auto Forms & Endorsements"
    if "commercial general liability" in t and "forms" in t and "endorsements" in t: 
        return "Commercial General Liability Forms & Endorsements"
    
    # --- QUOTES ---
    if "commercial general liability" in t and ("limit" in t or "aggregate" in t): 
        return "Commercial General Liability Quote"
    if "annual business auto" in t and ("quote" in t or "loss control" in t): 
        return "Annual Business Auto Quote"
    if "blanket accident" in t and "details" in t: 
        return "Blanket Accident Quote"
    
    # --- MARKETING & LEGAL ---
    if "important to transfer risk" in t: return "Why its important to transfer risk and cost to my clients"
    if "how does it work" in t: return "OK so how does it work"
    if "small print" in t: return "The Small Print"
    if "overall program binding" in t: return "Overall Program Binding"
    
    return "Unclassified/Misc"

# --- USER INTERFACE ---
st.title("🛡️ Insurance Package Builder")
st.info("Upload your PDF files. The tool will arrange them into your exact required sequence.")

uploaded_files = st.file_uploader("Upload PDFs here", type="pdf", accept_multiple_files=True)

if uploaded_files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    preview_list = []

    for uploaded_file in uploaded_files:
        reader = pypdf.PdfReader(uploaded_file)
        for i, page in enumerate(reader.pages):
            content = page.extract_text() or ""
            category = classify_page(content)
            buckets[category].append(page)
            preview_list.append({"File": uploaded_file.name, "Page": i+1, "Detected As": category})

    st.subheader("📋 Page Identification Preview")
    st.dataframe(preview_list, use_container_width=True)

    if st.button("Build Final PDF Package"):
        writer = pypdf.PdfWriter()
        
        # Assemble in the MASTER_ORDER sequence
        for category in MASTER_ORDER:
            for page in buckets[category]:
                writer.add_page(page)
        
        # Append Unclassified pages to the very end as a safety net
        for page in buckets["Unclassified/Misc"]:
            writer.add_page(page)
        
        output = io.BytesIO()
        writer.write(output)
        
        st.success("✨ Package reordered successfully!")
        st.download_button(
            label="⬇️ Download Final PDF",
            data=output.getvalue(),
            file_name=f"Insurance_Package_{datetime.now().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf"
        )
