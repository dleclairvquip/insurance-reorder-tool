import streamlit as st
import pypdf
import io
from datetime import datetime

# 1. THEME & PAGE CONFIG
st.set_page_config(
    page_title="Adventure Shield Assembler",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS for a clean, professional look
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div.stButton > button:first-child {
        background-color: #004a99;
        color: white;
        border: None;
        padding: 0.6rem 2rem;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #003366;
        border: None;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. SEQUENCE LOGIC
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

# --- SIDEBAR (No Logo) ---
with st.sidebar:
    st.markdown("### **Operation Control**")
    st.caption("v1.2.1 - Clean Edition")
    st.divider()
    st.write("This tool automatically scans PDF content to build the standard Adventure Shield package.")
    st.write("Upload all source documents on the right to begin.")

# --- MAIN APP ---
st.title("🛡️ Adventure Shield Assembler")
st.markdown("Drag and drop your source documents to generate a finalized quote package.")

files = st.file_uploader("", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []
    
    with st.spinner("Analyzing PDF architecture..."):
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                cat = classify_page(page.extract_text() or "")
                buckets[cat].append(page)

    # Dashboard Metrics
    m1, m2, m3 = st.columns(3)
    total = sum(len(p) for p in buckets.values())
    unclassified = len(buckets["Unclassified/Misc"])
    
    with m1: st.metric("Pages Detected", total)
    with m2: st.metric("Identification Rate", f"{((total-unclassified)/total)*100:.0f}%")
    with m3: st.metric("Manual Review Required", unclassified)

    if st.button("🚀 ASSEMBLE ADVENTURE SHIELD PACKAGE"):
        writer = pypdf.PdfWriter()
        for cat in MASTER_ORDER:
            for p in buckets[cat]: writer.add_page(p)
        for p in buckets["Unclassified/Misc"]: writer.add_page(p)
        
        final_pdf = io.BytesIO()
        writer.write(final_pdf)
        
        st.balloons()
        st.download_button(
            "💾 DOWNLOAD COMPLETED PACKAGE",
            data=final_pdf.getvalue(),
            file_name=f"Insurance_Package_{datetime.now().strftime('%m-%d-%Y')}.pdf",
            mime="application/pdf"
        )
