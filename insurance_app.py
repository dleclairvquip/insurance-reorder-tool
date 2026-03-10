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

# ── 1. PAGE CONFIG
st.set_page_config(page_title="Adventure Shield Proposal Builder", page_icon="🛡️", layout="wide")

# ── 2. MASTER SEQUENCE
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


# ── 3. CLASSIFICATION
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


# ── 4. DATA EXTRACTION
def extract_coverage_data(buckets):
    def get_text(pages):
        return "\n".join(p.extract_text() or "" for p in pages)

    def search(text, *patterns):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "—"

    gl_text   = get_text(buckets.get("Commercial General Liability Quote", []))
    auto_text = get_text(buckets.get("Annual Business Auto Quote", []))
    all_text  = gl_text + "\n" + auto_text

    return {
        # Policy info
        "insured":           search(all_text,
                                r"(?:Name(?:d)? Insured|For:)\s*\n?(.+)",
                                r"Named Insured[:\s]+(.+)"),
        "effective_date":    search(all_text,
                                r"Period of Insurance\s+(\d{2}/\d{2}/\d{4})",
                                r"Policy Term[:\s]+(\w+ \d+,\s*\d{4})"),
        "expiry_date":       search(all_text,
                                r"Period of Insurance\s+\d{2}/\d{2}/\d{4}\s+to\s+(\d{2}/\d{2}/\d{4})",
                                r"Policy Term:.+to\s+(\w+ \d+,\s*\d{4})"),

        # GL limits
        "gl_carrier":        search(gl_text,  r"Provided by:\s*([^\n\(]+)"),
        "gl_aggregate":      search(gl_text,  r"General Aggregate(?:\s+Limit)?\s+\$([\d,]+)"),
        "gl_occurrence":     search(gl_text,  r"Each Occurrence(?:\s+Limit)?\s+\$([\d,]+)"),
        "gl_products":       search(gl_text,  r"Products.Completed Ops?\s+\$([\d,]+)"),
        "gl_pi":             search(gl_text,  r"Personal.{0,5}Advertising\s+\$([\d,]+)"),
        "gl_med_exp":        search(gl_text,  r"Medical Expen\w+\s+\$([\d,]+)"),

        # GL premiums
        "gl_premium":        search(gl_text,  r"^Premium\s+\$([\d,]+\.\d{2})",
                                              r"General Liability\s+\$([\d,]+\.\d{2})"),
        "gl_surplus_tax":    search(gl_text,  r"Surplus Lines Tax\s+\$([\d,]+\.\d{2})"),
        "gl_stamp_fee":      search(gl_text,  r"Stamping Fee\s+\$([\d,]+\.\d{2})"),
        "gl_total_premium":  search(gl_text,  r"Total Premium.*?\$([\d,]+\.\d{2})",
                                              r"TOTAL PREMIUM COST\*?\s+\$([\d,]+\.\d{2})"),

        # Auto limits
        "auto_carrier":      search(auto_text, r"Carrier\s+([^\n]+)"),
        "auto_bi_person":    search(auto_text, r"B\.?I\.? per Person\s+\$([\d,]+)",
                                               r"Bodily Injury Liability per Person\s+\d+\s+\$([\d,]+)"),
        "auto_bi_acc":       search(auto_text, r"B\.?I\.? per Accident\s+\$([\d,]+)",
                                               r"Bodily Injury Liability per Accident\s+\d+\s+\$([\d,]+)"),
        "auto_pd":           search(auto_text, r"Property Damage per Accident\s+\$([\d,]+)",
                                               r"Property Damage Liability per Accident\s+\d+\s+\$([\d,]+)"),

        # Auto premiums
        "auto_premium":      search(auto_text, r"Annual Premium\s+\$([\d,]+\.\d{2})"),
        "auto_surplus_tax":  search(auto_text, r"Surplus Lines Tax\s+\$([\d,]+\.\d{2})"),
        "auto_stamp_fee":    search(auto_text, r"Stamping Fee\s+\$([\d,]+\.\d{2})"),
        "auto_total_premium":search(auto_text, r"^Total\s+\$([\d,]+\.\d{2})",
                                               r"Total\s+\$([\d,]+\.\d{2})"),
    }


# ── 5. SUMMARY PDF GENERATOR
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

    DARK  = colors.HexColor("#1B2A4A")
    TEAL  = colors.HexColor("#2E7D8C")
    LIGHT = colors.HexColor("#F9F9F9")
    WHITE = colors.white
    BLACK = colors.HexColor("#222222")

    bold_label = ParagraphStyle("bold_label", fontSize=10, fontName="Helvetica-Bold",
                                textColor=BLACK, spaceAfter=1)
    normal_val = ParagraphStyle("normal_val", fontSize=10, fontName="Helvetica",
                                textColor=BLACK, spaceAfter=6)

    def fmt_currency(val):
        if not val or val == "—":
            return "—"
        try:
            return f"${float(val.replace(',', '').replace('$', '')):,.2f}"
        except:
            return val

    def two_col_table(rows, col_widths):
        style_cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0),  DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  10),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("ALIGN",         (1, 0), (1, -1),  "RIGHT"),
        ]
        for i in range(1, len(rows)):
            bg = LIGHT if i % 2 == 1 else WHITE
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

        tbl = Table(rows, colWidths=col_widths)
        tbl.setStyle(TableStyle(style_cmds))
        return tbl

    def total_row_table(rows, col_widths):
        style_cmds = [
            ("BACKGROUND",    (0, 0),  (-1, 0),  DARK),
            ("TEXTCOLOR",     (0, 0),  (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0),  (-1, 0),  "Helvetica-Bold"),
            ("BACKGROUND",    (0, -1), (-1, -1), TEAL),
            ("TEXTCOLOR",     (0, -1), (-1, -1), WHITE),
            ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
            ("TOPPADDING",    (0, 0),  (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0),  (-1, -1), 6),
            ("LEFTPADDING",   (0, 0),  (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0),  (-1, -1), 8),
            ("GRID",          (0, 0),  (-1, -1), 0.25, colors.lightgrey),
            ("ALIGN",         (1, 0),  (1, -1),  "RIGHT"),
        ]
        for i in range(1, len(rows) - 1):
            bg = LIGHT if i % 2 == 1 else WHITE
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

        tbl = Table(rows, colWidths=col_widths)
        tbl.setStyle(TableStyle(style_cmds))
        return tbl

    CW    = [4.5 * inch, 2.5 * inch]
    story = []

    # ── Named Insured / Policy Info
    story.append(Paragraph("Name Insured", bold_label))
    story.append(Paragraph(data.get("insured", "—"), normal_val))
    story.append(Paragraph("Period of Insurance", bold_label))
    story.append(Paragraph(
        f"{data.get('effective_date', '—')} to {data.get('expiry_date', '—')}",
        normal_val
    ))
    story.append(Spacer(1, 12))

    # ── GL Coverage Table
    story.append(two_col_table([
        ["Commercial General Liability Coverage", "Limit"],
        ["General Aggregate Limit",               f"${data.get('gl_aggregate',  '—')}"],
        ["Each Occurrence Limit",                 f"${data.get('gl_occurrence', '—')}"],
        ["Products-Completed Ops",                f"${data.get('gl_products',   '—')}"],
        ["Personal/Advertising",                  f"${data.get('gl_pi',         '—')}"],
        ["Medical Expense",                       f"${data.get('gl_med_exp',    '—')}"],
    ], CW))
    story.append(Spacer(1, 14))

    # ── Auto Coverage Table
    story.append(two_col_table([
        ["Business Auto Coverage",        "Limit"],
        ["BI per Person",                 f"${data.get('auto_bi_person', '—')}"],
        ["BI per Accident",               f"${data.get('auto_bi_acc',    '—')}"],
        ["Property Damage per Accident",  f"${data.get('auto_pd',        '—')}"],
        ["Collision",                     "Excluded"],
        ["Comprehensive",                 "Excluded"],
    ], CW))
    story.append(Spacer(1, 14))

    # ── GL Premium Summary
    story.append(total_row_table([
        ["General Liability Premium Summary",  "Paid in Full"],
        ["Premium",                            fmt_currency(data.get("gl_premium",       "—"))],
        ["Surplus Lines Tax",                  fmt_currency(data.get("gl_surplus_tax",   "—"))],
        ["Stamping Fee",                       fmt_currency(data.get("gl_stamp_fee",     "—"))],
        ["Total Premium & Taxes / Fees",       fmt_currency(data.get("gl_total_premium", "—"))],
    ], CW))
    story.append(Spacer(1, 14))

    # ── Auto Premium Summary
    story.append(total_row_table([
        ["Business Auto Premium Summary",  "Paid in Full"],
        ["Annual Premium",                 fmt_currency(data.get("auto_premium",       "—"))],
        ["Surplus Lines Tax",              fmt_currency(data.get("auto_surplus_tax",   "—"))],
        ["Stamping Fee",                   fmt_currency(data.get("auto_stamp_fee",     "—"))],
        ["Total",                          fmt_currency(data.get("auto_total_premium", "—"))],
    ], CW))

    doc.build(story)
    return buffer.getvalue()


# ── MAIN APP
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
