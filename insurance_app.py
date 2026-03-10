import streamlit as st
import pypdf
import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── 1. PAGE CONFIG
st.set_page_config(page_title="AdventureShield Proposal Builder", page_icon="🛡️", layout="wide")

# ── 2. CUSTOM CSS
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0F1923; }
    [data-testid="stSidebar"] { background-color: #0F1923; }
    section[data-testid="stMain"] { background-color: #0F1923; }
    .hero-banner {
        background: linear-gradient(135deg, #1B2A4A 0%, #2E7D8C 100%);
        border-radius: 16px; padding: 40px 48px; margin-bottom: 32px; border: 1px solid #2E7D8C;
    }
    .hero-title { font-size: 42px; font-weight: 800; color: #FFFFFF; letter-spacing: -1px; margin: 0; line-height: 1.1; }
    .hero-subtitle { font-size: 16px; color: #A8C4C8; margin-top: 8px; font-weight: 400; }
    .hero-badge { display: inline-block; background: rgba(255,255,255,0.15); color: #FFFFFF; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; padding: 4px 12px; border-radius: 20px; margin-bottom: 16px; }
    [data-testid="stFileUploader"] { background: #1A2535; border: 2px dashed #2E7D8C; border-radius: 12px; padding: 12px; }
    [data-testid="stFileUploader"]:hover { border-color: #C9A84C; }
    .section-header { font-size: 11px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: #2E7D8C; margin: 32px 0 16px 0; }
    .status-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; margin-bottom: 24px; }
    .status-card { background: #1A2535; border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; gap: 12px; border: 1px solid #263548; }
    .status-card.success { border-left: 3px solid #2E7D8C; }
    .status-card.warning { border-left: 3px solid #C9A84C; opacity: 0.6; }
    .status-card.error   { border-left: 3px solid #E05555; }
    .status-icon  { font-size: 18px; min-width: 24px; }
    .status-label { font-size: 13px; font-weight: 600; color: #FFFFFF; }
    .status-count { font-size: 12px; color: #6B8A9A; margin-top: 2px; }
    [data-testid="stButton"] > button { background: linear-gradient(135deg, #2E7D8C, #1B5E6E) !important; color: white !important; font-weight: 700 !important; font-size: 15px !important; letter-spacing: 1px !important; border: none !important; border-radius: 10px !important; padding: 14px 32px !important; width: 100% !important; }
    [data-testid="stButton"] > button:hover { background: linear-gradient(135deg, #C9A84C, #A8872E) !important; }
    [data-testid="stDownloadButton"] > button { background: #1A2535 !important; color: #FFFFFF !important; font-weight: 600 !important; font-size: 14px !important; border: 2px solid #2E7D8C !important; border-radius: 10px !important; padding: 12px 24px !important; width: 100% !important; }
    [data-testid="stDownloadButton"] > button:hover { background: #2E7D8C !important; }
    [data-testid="stSuccess"] { background: #1A2535 !important; border: 1px solid #2E7D8C !important; border-radius: 10px !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    p, li, span, label { color: #A8C4C8; }
    h1, h2, h3 { color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)

# ── 3. MASTER SEQUENCE
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


# ── 4. CLASSIFICATION
def classify_page(text):
    t = " ".join(text.lower().split())
    if "surplus lines" in t and "disclosure" in t:              return "Surplus Lines Disclosure"
    if "terrorism" in t and "coverage offering" in t:           return "Notice of Terrorism Coverage Offering"
    if "small print" in t:                                       return "The Small Print"
    if "overall program binding" in t:                           return "Overall Program Binding"
    if "transfer risk" in t:                                     return "Why its important to transfer risk and cost"
    if "how does it work" in t:                                  return "OK so how does it work"
    if "blanket accident" in t and "details" in t:               return "Blanket Accident - Full Details"
    if "forms" in t and "endorsements" in t and "auto" in t:     return "Annual Business Auto Forms & Endorsements"
    if "forms" in t and "endorsements" in t:                     return "Commercial General Liability Forms & Endorsements"
    if "annual business auto" in t and "forms" not in t and "endorsements" not in t:
        return "Annual Business Auto Quote"
    if "commercial general liability" in t and "forms" not in t and "terrorism" not in t:
        return "Commercial General Liability Quote"
    return "Unclassified/Misc"


# ── 5. DATA EXTRACTION
def extract_coverage_data(buckets):
    def get_text(pages):
        return "\n".join(p.extract_text() or "" for p in pages)

    def search(text, *patterns):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return "—"

    gl_text   = get_text(buckets.get("Commercial General Liability Quote", []))
    auto_text = get_text(buckets.get("Annual Business Auto Quote", []))
    all_text  = gl_text + "\n" + auto_text

    return {
        "insured":           search(all_text,  r"Name(?:d)? Insured\s+([^\n]+?)\s+Date Quoted",
                                               r"Name(?:d)? Insured\s*\n([^\n]+)"),
        "effective_date":    search(all_text,  r"(\d{2}/\d{2}/\d{4})\s+to\s+\d{2}/\d{2}/\d{4}"),
        "expiry_date":       search(all_text,  r"\d{2}/\d{2}/\d{4}\s+to\s+(\d{2}/\d{2}/\d{4})"),
        "gl_carrier":        search(gl_text,   r"Carrier\s+([^\n]+)"),
        "gl_aggregate":      search(gl_text,   r"General Aggregate Limit[^$]*\$([0-9,]+)"),
        "gl_occurrence":     search(gl_text,   r"Each Occurrence Limit[:\s]+\$([0-9,]+)"),
        "gl_products":       search(gl_text,   r"Products\s*-?\s*Completed Operations[^$\n]*\$([0-9,]+)"),
        "gl_pi":             search(gl_text,   r"Personal and Advertising Injury Limit[:\s]+\$([0-9,]+)"),
        "gl_premises":       search(gl_text,   r"Damage to Premises Rented[^$\n]*\$([0-9,]+)"),
        "gl_med_exp":        search(gl_text,   r"Medical Expense Limit\s+\$([0-9,]+)"),
        "gl_premium":        search(gl_text,   r"^Premium\s+\$([0-9,]+\.\d{2})"),
        "gl_surplus_tax":    search(gl_text,   r"Surplus\s*\n?Lines\s*Tax[:\s]+\$([0-9,]+\.\d{2})"),
        "gl_stamp_fee":      search(gl_text,   r"Stamping Fee\s+\$([0-9,]+\.\d{2})"),
        "gl_platform_fee":   search(gl_text,   r"Platform Fee\s+\$([0-9,]+\.\d{2})"),
        "gl_total_premium":  search(gl_text,   r"Total Premium\s*&?\s*\n?Taxes\s*/\s*Fees\s+\$([0-9,]+\.\d{2})"),
        "auto_carrier":      search(auto_text, r"Carrier\s+([^\n]+)"),
        "auto_bi_person":    search(auto_text, r"Bodily Injury Liability per Person\s+\d+\s+\$([0-9,]+)"),
        "auto_bi_acc":       search(auto_text, r"Bodily Injury Liability per Accident\s+\d+\s+\$([0-9,]+)"),
        "auto_pd":           search(auto_text, r"Property Damage Liability per Accident\s+\d+\s+\$([0-9,]+)"),
        "auto_premium":      search(auto_text, r"Annual Premium\s+\$([0-9,]+\.\d{2})"),
        "auto_surplus_tax":  search(auto_text, r"Surplus Lines Tax\s+\$([0-9,]+\.\d{2})"),
        "auto_stamp_fee":    search(auto_text, r"Stamping Fee\s+\$([0-9,]+\.\d{2})"),
        "auto_tech_fee":     search(auto_text, r"Technology Transaction Fee[^\n]*\n[^\$]*\$([0-9,]+\.\d{2})"),
        "auto_total":        search(auto_text, r"^Total\s+\$([0-9,]+\.\d{2})"),
    }


# ── 6. SUMMARY PDF GENERATOR
def generate_summary_pdf(data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=0.5*inch, leftMargin=0.5*inch,
        topMargin=0.45*inch,  bottomMargin=0.45*inch,
    )

    DARK  = colors.HexColor("#1B2A4A")
    TEAL  = colors.HexColor("#2E7D8C")
    GOLD  = colors.HexColor("#C9A84C")
    LIGHT = colors.HexColor("#F4F6FA")
    WHITE = colors.white
    BLACK = colors.HexColor("#222222")
    GREY  = colors.HexColor("#888888")

    def parse_float(val):
        try:    return float(str(val).replace(',','').replace('$',''))
        except: return 0.0

    def fmt(val, currency=False):
        if not val or val == "—": return "—"
        if currency:
            try:    return f"${float(str(val).replace(',','').replace('$','')):,.2f}"
            except: return str(val)
        v = str(val)
        return f"${v}" if not v.startswith("$") else v

    grand_total     = parse_float(data.get("gl_total_premium","0")) + parse_float(data.get("auto_total","0"))
    grand_total_fmt = f"${grand_total:,.2f}" if grand_total > 0 else "—"

    PW    = 7.5 * inch
    GAP   = 0.1 * inch
    PANEL = (PW - GAP) / 2
    L_COL = PANEL * 0.62
    V_COL = PANEL * 0.38

    def p(text, bold=False, size=8, color=BLACK, align=TA_LEFT):
        return Paragraph(str(text), ParagraphStyle("_",
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size, textColor=color, alignment=align, leading=size+3))

    def build_table(rows, total_row=False):
        cmds = [
            ("BACKGROUND",    (0,0), (-1,0),  DARK),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 7),
            ("RIGHTPADDING",  (0,0), (-1,-1), 7),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
            ("ALIGN",         (1,0), (1,-1),  "RIGHT"),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]
        if total_row:
            cmds += [
                ("BACKGROUND", (0,-1), (-1,-1), TEAL),
            ]
        for i in range(1, len(rows) - (1 if total_row else 0)):
            cmds.append(("BACKGROUND", (0,i), (-1,i), LIGHT if i%2==1 else WHITE))
        tbl = Table(rows, colWidths=[L_COL, V_COL])
        tbl.setStyle(TableStyle(cmds))
        return tbl

    def side_by_side(left, right):
        tbl = Table([[left, right]], colWidths=[PANEL, PANEL])
        tbl.setStyle(TableStyle([
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
            ("TOPPADDING",   (0,0),(-1,-1), 0),
            ("BOTTOMPADDING",(0,0),(-1,-1), 0),
            ("VALIGN",       (0,0),(-1,-1), "TOP"),
            ("RIGHTPADDING", (0,0),(0,0),   int(GAP/2)),
            ("LEFTPADDING",  (1,0),(1,0),   int(GAP/2)),
        ]))
        return tbl

    story = []

    # ── Header
    hdr = Table([
        [p("AdventureShield", bold=True, size=20, color=WHITE, align=TA_CENTER)],
        [p("COVERAGE &amp; PREMIUM SUMMARY", size=8, color=colors.HexColor("#A8C4C8"), align=TA_CENTER)],
    ], colWidths=[PW])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK),
        ("TOPPADDING",    (0,0),(-1,0),  10),
        ("BOTTOMPADDING", (0,0),(-1,0),  3),
        ("TOPPADDING",    (0,1),(-1,1),  2),
        ("BOTTOMPADDING", (0,1),(-1,1),  10),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6))

    # ── Policy info
    info = Table([
        [p("NAMED INSURED", size=7, color=GREY), p("POLICY PERIOD", size=7, color=GREY)],
        [p(data.get("insured","—"), bold=True, size=9),
         p(f"{data.get('effective_date','—')}  →  {data.get('expiry_date','—')}", bold=True, size=9)],
    ], colWidths=[PW/2, PW/2])
    info.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("LINEBELOW",     (0,0),(-1,0),  0.5, colors.lightgrey),
    ]))
    story.append(info)
    story.append(Spacer(1, 6))

    # ── Coverage tables
    gl_cov = build_table([
        [p("Commercial General Liability", bold=True, color=WHITE), p("Limit", bold=True, color=WHITE, align=TA_CENTER)],
        [p("General Aggregate"),           p(fmt(data.get("gl_aggregate",  "—")), align=TA_CENTER)],
        [p("Each Occurrence"),             p(fmt(data.get("gl_occurrence", "—")), align=TA_CENTER)],
        [p("Products-Completed Ops"),      p(fmt(data.get("gl_products",   "—")), align=TA_CENTER)],
        [p("Personal/Advertising Injury"), p(fmt(data.get("gl_pi",         "—")), align=TA_CENTER)],
        [p("Damage to Premises Rented"),   p(fmt(data.get("gl_premises",   "—")), align=TA_CENTER)],
        [p("Medical Expense"),             p(fmt(data.get("gl_med_exp",    "—")), align=TA_CENTER)],
    ])

    auto_cov = build_table([
        [p("Business Auto", bold=True, color=WHITE), p("Limit", bold=True, color=WHITE, align=TA_CENTER)],
        [p("BI per Person"),                p(fmt(data.get("auto_bi_person","—")), align=TA_CENTER)],
        [p("BI per Accident"),              p(fmt(data.get("auto_bi_acc",   "—")), align=TA_CENTER)],
        [p("Property Damage per Accident"), p(fmt(data.get("auto_pd",       "—")), align=TA_CENTER)],
        [p("Collision"),                    p("Excluded", align=TA_CENTER)],
        [p("Comprehensive"),                p("Excluded", align=TA_CENTER)],
        [p(""),                             p("")],
    ])

    story.append(side_by_side(gl_cov, auto_cov))
    story.append(Spacer(1, 6))

    # ── Premium tables
    gl_prem = build_table([
        [p("GL Premium Summary", bold=True, color=WHITE), p("Paid in Full", bold=True, color=WHITE, align=TA_CENTER)],
        [p("Premium"),           p(fmt(data.get("gl_premium",      "—"), currency=True), align=TA_CENTER)],
        [p("Surplus Lines Tax"), p(fmt(data.get("gl_surplus_tax",  "—"), currency=True), align=TA_CENTER)],
        [p("Stamping Fee"),      p(fmt(data.get("gl_stamp_fee",    "—"), currency=True), align=TA_CENTER)],
        [p("Platform Fee"),      p(fmt(data.get("gl_platform_fee", "—"), currency=True), align=TA_CENTER)],
        [p("Total & Taxes / Fees", bold=True, color=WHITE), p(fmt(data.get("gl_total_premium","—"), currency=True), bold=True, color=WHITE, align=TA_CENTER)],
    ], total_row=True)

    auto_prem = build_table([
        [p("Auto Premium Summary", bold=True, color=WHITE), p("Paid in Full", bold=True, color=WHITE, align=TA_CENTER)],
        [p("Annual Premium"),    p(fmt(data.get("auto_premium",     "—"), currency=True), align=TA_CENTER)],
        [p("Surplus Lines Tax"), p(fmt(data.get("auto_surplus_tax", "—"), currency=True), align=TA_CENTER)],
        [p("Stamping Fee"),      p(fmt(data.get("auto_stamp_fee",   "—"), currency=True), align=TA_CENTER)],
        [p("Technology Fee"),    p(fmt(data.get("auto_tech_fee",    "—"), currency=True), align=TA_CENTER)],
        [p("Total", bold=True, color=WHITE), p(fmt(data.get("auto_total","—"), currency=True), bold=True, color=WHITE, align=TA_CENTER)],
    ], total_row=True)

    story.append(side_by_side(gl_prem, auto_prem))
    story.append(Spacer(1, 10))

    # ── Grand total
    grand = Table([[
        p("TOTAL ANNUAL COST — ALL COVERAGES", bold=True, color=WHITE, size=11),
        p(grand_total_fmt, bold=True, color=WHITE, size=14, align=TA_CENTER),
    ]], colWidths=[PW * 0.68, PW * 0.32])
    grand.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GOLD),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",         (1,0),(1,0),   "RIGHT"),
    ]))
    story.append(grand)

    doc.build(story)
    return buffer.getvalue()


# ── MAIN APP
st.markdown("""
<div class="hero-banner">
    <div class="hero-badge">🛡️ Insurance</div>
    <div class="hero-title">AdventureShield</div>
    <div class="hero-title" style="color: #2E7D8C;">Proposal Builder</div>
    <div class="hero-subtitle">Upload your carrier documents — we'll sort, reorder, and package them automatically.</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-header">📂 Upload Documents</div>', unsafe_allow_html=True)
files = st.file_uploader(
    "Drop your quote PDFs here or click to browse",
    type="pdf", accept_multiple_files=True, label_visibility="collapsed"
)

if files:
    buckets = {name: [] for name in MASTER_ORDER}
    buckets["Unclassified/Misc"] = []

    with st.spinner("🔍 Analyzing and classifying pages..."):
        for f in files:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text() or ""
                category = classify_page(text)
                buckets[category].append(page)

    st.markdown('<div class="section-header">📋 Document Classification</div>', unsafe_allow_html=True)

    cards_html = '<div class="status-grid">'
    for category in MASTER_ORDER:
        count = len(buckets[category])
        if count > 0:
            cards_html += f"""<div class="status-card success"><div class="status-icon">✅</div><div><div class="status-label">{category}</div><div class="status-count">{count} page{"s" if count != 1 else ""} found</div></div></div>"""
        else:
            cards_html += f"""<div class="status-card warning"><div class="status-icon">⚠️</div><div><div class="status-label">{category}</div><div class="status-count">No pages found</div></div></div>"""

    misc_count = len(buckets["Unclassified/Misc"])
    if misc_count > 0:
        cards_html += f"""<div class="status-card error"><div class="status-icon">❓</div><div><div class="status-label">Unclassified / Misc</div><div class="status-count">{misc_count} page{"s" if misc_count != 1 else ""} — will append at end</div></div></div>"""
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown('<div class="section-header">🚀 Generate Package</div>', unsafe_allow_html=True)
    if st.button("GENERATE ORDERED PACKAGE + COVERAGE SUMMARY"):
        with st.spinner("Building your package..."):
            writer = pypdf.PdfWriter()
            for category in MASTER_ORDER:
                for page in buckets[category]:
                    writer.add_page(page)
            for page in buckets["Unclassified/Misc"]:
                writer.add_page(page)
            output_buffer = io.BytesIO()
            writer.write(output_buffer)

            coverage_data = extract_coverage_data(buckets)
            summary_pdf_bytes = generate_summary_pdf(coverage_data)

        st.success("✅ Package ready — download your files below!")
        st.markdown('<div class="section-header">💾 Downloads</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📦 Download Ordered Package",
                data=output_buffer.getvalue(),
                file_name="AdventureShield_Proposal_Package.pdf",
                mime="application/pdf"
            )
        with col2:
            st.download_button(
                label="📄 Download Coverage Summary",
                data=summary_pdf_bytes,
                file_name="AdventureShield_Coverage_Summary.pdf",
                mime="application/pdf"
            )
