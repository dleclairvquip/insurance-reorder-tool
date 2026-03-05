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
    "Notice of Terrorism Coverage Offering",
    "The Small Print",
    "Overall Program Binding"
]

def classify_page(text):
    """Matches page text against your specific insurance headers."""
    t = text.replace('\n', ' ').strip()
    
    if "Surplus Lines Disclosure" in t: return "Surplus Lines Disclosure"
    if "Commercial General Liability" in t and "Quote" in t: return "Commercial General Liability Quote"
    if "Annual Business Auto" in t and "Quote" in t: return "Annual Business Auto Quote"
    if "Blanket Accident" in t: return "Blanket Accident Quote"
    if "Commercial General Liability Forms & Endorsements" in t: return "Commercial General Liability Forms & Endorsements"
    if "Annual Business Auto Forms & Endorsements" in t: return "Annual Business Auto Forms & Endorsements"
    if "important to transfer risk and cost" in t: return "Why its important to transfer risk and cost to my clients"
    if "OK so how does it work" in t: return "OK so how does it work"
    if "Notice of Terrorism Coverage Offering" in t: return "Notice of Terrorism Coverage Offering"
    if "The Small Print" in t: return "The Small Print"
    if "Overall Program Binding" in t: return "Overall Program Binding"
    
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
