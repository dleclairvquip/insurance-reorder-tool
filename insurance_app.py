import streamlit as st
import pypdf
import io
import pandas as pd
from datetime import datetime

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Insurance PDF Builder", page_icon="🛡️", layout="wide")

# 2. YOUR TARGET SEQUENCE
MASTER_ORDER = [
    "Surplus Lines Disclosure",
    "Commercial General Liability Quote",
    "Annual Business Auto Quote",
    "Blanket Accident Quote",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost to my clients",
    "OK so how does it work",
    "Notice of Terrorism Coverage Offering", # Moved here
    "The Small Print",
    "Overall Program Binding"
]

def classify_page(text):
    t = " ".join(text.lower().split())
    
    # Surplus Lines (State Agnostic)
    if "surplus lines" in t and ("disclosure" in t or "notice" in t): 
        return "Surplus Lines Disclosure"
    
    # Notice of Terrorism (Check this BEFORE the CGL Quote)
    if "notice of terrorism" in t and "coverage offering" in t: 
        return "Notice of Terrorism Coverage Offering"
    
    # Commercial General Liability Quote
    if "commercial general liability" in t and ("limit" in t or "aggregate" in t) and "forms" not in t: 
        return "Commercial General Liability Quote"
    
    # Annual Business Auto Quote
    if "annual business auto" in t and ("quote" in t or "loss control" in t) and "forms" not in t: 
        return "Annual Business Auto Quote"
    
    # Blanket Accident
    if "blanket accident" in t and "details" in t: 
        return "Blanket Accident Quote"
    
    # Forms & Endorsements
    if "commercial general liability" in t and "forms" in t and "endorsements" in t: 
        return "Commercial General Liability Forms & Endorsements"
    if "business auto" in t and "forms" in t and "endorsements" in t: 
        return "Annual Business Auto Forms & Endorsements"
    
    # Marketing / Legal
    if "important to transfer risk" in t: return "Why its important to transfer risk and cost to my clients"
    if "how does it work" in t: return "OK so how does it work"
    if "small print" in t: return "The Small Print"
    if "program binding" in t: return "Overall Program Binding"
    
    return "Unclassified/Misc"

# --- USER INTERFACE ---
st.title("🛡️ Insurance Package Builder")
st.info("Upload your 3 PDF files. The tool will scan and arrange them into your master sequence.")

uploaded_files = st.file_uploader("Upload PDFs here", type="pdf", accept_multiple_files=True)

if uploaded_files:
    # Create buckets for each category
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    preview_list = []

    # Process each uploaded file
    for uploaded_file in uploaded_files:
        reader = pypdf.PdfReader(uploaded_file)
        for i, page in enumerate(reader.pages):
            content = page.extract_text() or ""
            category = classify_page(content)
            buckets[category].append(page)
            preview_list.append({
                "Source File": uploaded_file.name, 
                "Page Number": i + 1, 
                "Detected Category": category
            })

    # Show the preview table so you can verify the "AI" worked
    st.subheader("📋 Identification Preview")
    st.dataframe(preview_list, use_container_width=True)

    # Final Assembly Button
    if st.button("Generate Final PDF Package"):
        writer = pypdf.PdfWriter()
        
        # Add pages in the exact MASTER_ORDER sequence
        for category in MASTER_ORDER:
            for page in buckets[category]:
                writer.add_page(page)
        
        # Create the final file in memory
        output = io.BytesIO()
        writer.write(output)
        
        st.success("✨ Package created successfully!")
        
        # Provide the download link
        st.download_button(
            label="⬇️ Download Reordered PDF",
            data=output.getvalue(),
            file_name=f"Insurance_Package_{datetime.now().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf"
        )
