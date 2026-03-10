import streamlit as st
import pypdf
import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# 1. PAGE CONFIG
st.set_page_config(page_title="Adventure Shield Proposal Builder", page_icon="🛡️", layout="wide")

# 2. MASTER SEQUENCE
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


# 3. CLASSIFICATION
def classify_page(text):
    t = " ".join(text.lower().split())

    if "surplus lines" in t and "disclosure" in t:
        return "Surplus Lines Disclosure"
    if "terrorism" in t and "coverage offering" in t:
        return "Notice of Terrorism Coverage Offering"
    if "small print" in t:
        return "The Small Print"
    if "overall program binding" in t:
        return "Overall Program Binding"
    if "transfer risk" in t:
        return "Why its important to transfer risk and cost"
    if "how does it work" in t:
        return "OK so how does it work"
    if "blanket accident" in t and "details" in t:
        return "Blanket Accident - Full Details"
    if "forms" in t and "endorsements" in t and "auto" in t:
        return "Annual Business Auto Forms & Endorsements"
    if "forms" in t and "endorsements" in t:
        return "Commercial General Liability Forms & Endorsements"
    if "annual business auto" in t and "quote" in t:
        return "Annual Business Auto Quote"
    if "commercial general liability" in t and "limit" in t:
        return "Commercial General Liability Quote"

    return "Unclassified/Misc"


# 4. DATA EXTRACTION
def extract_coverage_data(buckets):
    def search(pages, *patterns):
        for page in pages:
            text = page.extract_text() or ""
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return "Not Found"

    gl_pages   = buckets.get("Commercial General Liability Quote", [])
    auto_pages = buckets.get("Annual Business Auto Quote", [])
    all_pages  = gl_pages + auto_pages

    return {
        "insured":        search(all_pages,  r"(?:named insured|insured)[:\s]+([A-Za-z0-9\s,\.&'-]+)"),
        "effective_date": search(all_pages,  r"(?:effective date|policy period)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
        "expiry_date":    search(all_pages,  r"(?:expir\w+ date|to)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
        "gl_carrier":     search(gl_pages,   r"(?:carrier|company|insurer)[:\s]+([A-Za-z\s,\.]+)"),
        "gl_premium":     search(gl_pages,   r"(?:total premium|annual premium|premium)[:\s]+\$?([\d,]+\.?\d*)"),
        "gl_occ_limit":   search(gl_pages,   r"(?:each occurrence|per occurrence)[:\s]+\$?([\d,]+)"),
        "gl_agg_limit":   search(gl_pages,   r"(?:general aggregate)[:\s]+\$?([\d,]+)"),
        "gl_ded":         search(gl_pages,   r"(?:deductible)[:\s]+\$?([\d,]+)"),
        "auto_carrier":   search(auto_pages, r"(?:carrier|company|insurer)[:\s]+([A-Za-z\s,\.]+)"),
        "auto_premium":   search(auto_pages, r"(?:total premium|annual premium|premium)[:\s]+\$?([\d,]+\.?\d*)"),
        "auto_csl":       search(auto_pages, r"(?:combined single limit|CSL|bodily injury)[:\s]+\$?([\d,]+)"),
        "auto_ded":       search(auto_pages, r"(?:deductible)[:\s]+\$?([\d,]+)"),
    }


# 5. SUMMARY PDF GENERATOR
def generate_summary_pdf(data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    NAVY  = colors.HexColor("#1B2A4A")
    GOLD  = colors.HexColor("#C9A84C")
    LIGHT = colors.HexColor("#F4F6FA")

    title_style   = ParagraphStyle("title",   fontSize=22, textColor=NAVY,
                                   alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4)
    sub_style     = ParagraphStyle("sub",     fontSize=11, textColor=GOLD,
                                   alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=2)
    label_style   = ParagraphStyle("label",   fontSize=9,  textColor=colors.grey,
                                   fontName="Helvetica", leading=14)
    value_style   = ParagraphStyle("value",   fontSize=11, textColor=NAVY,
                                   fontName="Helvetica-Bold", leading=14)
    section_style = ParagraphStyle("section", fontSize=13, textColor=colors.white,
                                   fontName="Helvetica-Bold", alignment=TA_CENTER)
    footer_style  = ParagraphStyle("footer",  fontSize=8,  textColor=colors.grey,
                                   alignment=TA_CENTER)

    def fmt_currency(val):
        try:
            return f"${int(val.replace(',', '')):,}"
        except:
            return val if val != "Not Found" else "—"

    def info_row(label, value):
        return [Paragraph(label, label_style), Paragraph(value or "—", value_style)]

    def coverage_section(title, rows):
        header = Table([[Paragraph(title, section_style)]], colWidths=[7 * inch])
        header.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(header)

        tbl = Table(rows, colWidths=[2.2 * inch, 4.8 * inch])
        tbl.setStyle(TableStyle([
            ("ROWBACKGROUNDS",  (0, 0), (-1, -1), [LIGHT, colors.white]),
            ("LEFTPADDING",     (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",    (0, 0), (-1, -1), 10),
            ("TOPPADDING",      (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",   (0, 0), (-1, -1), 7),
            ("GRID",            (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 14))

    story = []

    # Header
    story.append(Paragraph("Adventure Shield", title_style))
    story.append(Paragraph("COVERAGE SUMMARY", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=10))

    # Client Info
    client_data = [
        info_row("NAMED INSURED",   data["insured"]),
        info_row("EFFECTIVE DATE",  data["effective_date"]),
        info_row("EXPIRATION DATE", data["expiry_date"]),
    ]
    client_table = Table(client_data, colWidths=[2.2 * inch, 4.8 * inch])
    client_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS",  (0, 0), (-1, -1), [LIGHT, colors.white]),
        ("LEFTPADDING",     (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",    (0, 0), (-1, -1), 10),
        ("TOPPADDING",      (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",   (0, 0), (-1, -1), 7),
        ("GRID",            (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 16))

    # General Liability
    coverage_section("COMMERCIAL GENERAL LIABILITY", [
        info_row("CARRIER",           data["gl_carrier"]),
        info_row("ANNUAL PREMIUM",    fmt_currency(data["gl_premium"])),
        info_row("EACH OCCURRENCE",   fmt_currency(data["gl_occ_limit"])),
        info_row("GENERAL AGGREGATE", fmt_currency(data["gl_agg_limit"])),
        info_row("DEDUCTIBLE",        fmt_currency(data["gl_ded"])),
    ])

    # Business Auto
    coverage_section("ANNUAL BUSINESS AUTO", [
        info_row("CARRIER",               data["auto_carrier"]),
        info_row("ANNUAL PREMIUM",        fmt_currency(data["auto_premium"])),
        info_row("COMBINED SINGLE LIMIT", fmt_currency(data["auto_csl"])),
        info_row("DEDUCTIBLE",            fmt_currency(data["auto_ded"])),
    ])

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=6))
    story.append(Paragraph(
        "This summary is for proposal purposes only and does not constitute a binder or policy.",
        footer_style
    ))

    doc.build(story)
    return buffer.getvalue()


# ── MAIN APP ─────────────────────────────────────────────────────────────────

st.title("🛡️ Adventure Shield Proposal Builder")
st.info("Upload your carrier documents below. The app will automatically reorder them and generate a coverage summary.")

files = st.file_uploader("Upload All Quote PDFs", type="pdf", accept_multiple_files=True)

if files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []

    with st.spinner("Analyzing and Reordering Pages..."):
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                category = classify_page(text)
                buckets[category].append(page)

    # Classification summary
    st.subheader("📋 Classification Summary")
    for category in MASTER_ORDER:
        count = len(buckets[category])
        if count == 0:
            st.warning(f"⚠️ {category}: No pages found")
        else:
            st.success(f"✅ {category}: {count} page(s)")

    misc_count = len(buckets["Unclassified/Misc"])
    if misc_count > 0:
        st.error(f"❓ Unclassified/Misc: {misc_count} page(s) — these will be appended at the end")

    if st.button("🚀 GENERATE ORDERED PACKAGE"):
        # Build merged PDF
        writer = pypdf.PdfWriter()
        for category in MASTER_ORDER:
            for page in buckets[category]:
                writer.add_page(page)
        for page in buckets["Unclassified/Misc"]:
            writer.add_page(page)

        output_buffer = io.BytesIO()
        writer.write(output_buffer)

        # Build coverage summary PDF
        coverage_data = extract_coverage_data(buckets)
        summary_pdf_bytes = generate_summary_pdf(coverage_data)

        st.success("Package Generated Successfully!")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="💾 DOWNLOAD REORDERED PACKAGE",
                data=output_buffer.getvalue(),
                file_name="Adventure_Shield_Proposal_Package.pdf",
                mime="application/pdf"
            )
        with col2:
            st.download_button(
                label="📄 DOWNLOAD COVERAGE SUMMARY",
                data=summary_pdf_bytes,
                file_name="Adventure_Shield_Coverage_Summary.pdf",
                mime="application/pdf"
            )
