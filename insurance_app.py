import streamlit as st
import pypdf
import io
from datetime import datetime

# 1. ENHANCED PAGE CONFIG
st.set_page_config(
    page_title="vQuip | Document Assembler",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CUSTOM CSS (The "Cool" Factor)
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #004a99;
        color: white;
        font-weight: bold;
    }
    .css-10trblm {
        color: #004a99;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# 3. MASTER ORDER (Same as before)
MASTER_ORDER = [
    "Surplus Lines Disclosure", "Commercial General Liability Quote",
    "Annual Business Auto Quote", "Blanket Accident Quote",
    "Commercial General Liability Forms & Endorsements",
    "Annual Business Auto Forms & Endorsements",
    "Why its important to transfer risk and cost to my clients",
    "OK so how does it work", "Notice of Terrorism Coverage Offering",
    "The Small Print", "Overall Program Binding"
]

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

# --- SIDEBAR HISTORY ---
with st.sidebar:
    st.image("https://vquip.com/wp-content/uploads/2022/07/vQuip-Logo-Blue.png", width=200) # Assuming vQuip logo
    st.title("Settings")
    st.write("v1.0.0 - Document Automator")
    st.divider()
    st.info("Ensure all 3 source PDFs are uploaded for a complete package.")

# --- MAIN UI ---
st.title("🛡️ Adventure Shield | Package Assembler")
st.subheader("Automated Insurance Document Reordering")

uploaded_files = st.file_uploader("", type="pdf", accept_multiple_files=True)

if uploaded_files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    
    with st.status("Analyzing documents...", expanded=True) as status:
        for uploaded_file in uploaded_files:
            reader = pypdf.PdfReader(uploaded_file)
            for i, page in enumerate(reader.pages):
                category = classify_page(page.extract_text() or "")
                buckets[category].append(page)
        status.update(label="Analysis complete!", state="complete", expanded=False)

    # SHOW DASHBOARD
    col1, col2, col3 = st.columns(3)
    total_pages = sum(len(v) for v in buckets.values())
    classified_count = total_pages - len(buckets["Unclassified/Misc"])
    
    col1.metric("Total Pages Found", total_pages)
    col2.metric("Successfully Identified", f"{classified_count}/{total_pages}")
    col3.metric("Unclassified", len(buckets["Unclassified/Misc"]))

    with st.expander("🔍 View Page-by-Page Breakdown"):
        # Build simple list for table
        data = []
        for cat, pages in buckets.items():
            if pages: data.append({"Category": cat, "Pages Found": len(pages)})
        st.table(data)

    if st.button("🚀 BUILD FINAL PACKAGE"):
        writer = pypdf.PdfWriter()
        for category in MASTER_ORDER:
            for page in buckets[category]:
                writer.add_page(page)
        for page in buckets["Unclassified/Misc"]:
            writer.add_page(page)
            
        output = io.BytesIO()
        writer.write(output)
        
        st.balloons()
        st.download_button(
            label="💾 DOWNLOAD REORDERED PACKAGE",
            data=output.getvalue(),
            file_name=f"AdventureShield_Package_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
