import streamlit as st
import pypdf
import io

# 1. PAGE CONFIG
st.set_page_config(page_title="Adventure Shield Proposal Builder", page_icon="🛡️", layout="wide")

# 2. MASTER SEQUENCE - Define the exact order you want here
MASTER_ORDER = [
    "Surplus Lines Disclosure",
    "Commercial General Liability Quote",
    "Annual Business Auto Quote",
    "Blanket Accident - Full Details",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost",
    "OK so how does it work",
    "Notice of Terrorism Coverage Offering",
    "The Small Print",
    "Overall Program Binding"
]

def classify_page(text):
    """
    Identifies the page type based on specific keyword anchors.
    Ensures classification is mutually exclusive to prevent misordering.
    """
    t = " ".join(text.lower().split())
    
    # Mapping logic
    if "surplus lines" in t and "disclosure" in t: return "Surplus Lines Disclosure"
    if "terrorism" in t and "coverage offering" in t: return "Notice of Terrorism Coverage Offering"
    if "small print" in t: return "The Small Print"
    if "commercial general liability" in t and "limit" in t and "forms" not in t: return "Commercial General Liability Quote"
    if "annual business auto" in t and "quote" in t and "forms" not in t: return "Annual Business Auto Quote"
    if "blanket accident" in t and "details" in t: return "Blanket Accident - Full Details"
    if "forms" in t and "endorsements" in t:
        return "Annual Business Auto Forms & Endorsements" if "auto" in t else "Commercial General Liability Forms & Endorsements"
    if "transfer risk" in t: return "Why its important to transfer risk and cost"
    if "how does it work" in t: return "OK so how does it work"
    if "overall program binding" in t: return "Overall Program Binding"
    
    return "Unclassified/Misc"

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Proposal Builder")
st.info("Upload your carrier documents below. The app will automatically reorder them and remove the summary page.")

files = st.file_uploader("Upload All Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    # Initialize buckets for each category in the master order
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    
    with st.spinner("Analyzing and Reordering Pages..."):
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                category = classify_page(text)
                buckets[category].append(page)

    # 3. GENERATE FINAL PACKAGE
    if st.button("🚀 GENERATE ORDERED PACKAGE"):
        writer = pypdf.PdfWriter()
        
        # Iterate through the master order to append pages in the correct sequence
        for category in MASTER_ORDER:
            for page in buckets[category]:
                writer.add_page(page)
        
        # Append any unclassified pages at the very end
        for page in buckets["Unclassified/Misc"]:
            writer.add_page(page)
            
        # Output the merged PDF
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        
        st.success("Package Generated Successfully!")
        st.download_button(
            label="💾 DOWNLOAD REORDERED PACKAGE",
            data=output_buffer.getvalue(),
            file_name="Adventure_Shield_Proposal_Package.pdf",
            mime="application/pdf"
        )
