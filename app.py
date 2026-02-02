import streamlit as st
from PyPDF2 import PdfReader
import docx
from langdetect import detect
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="GenAI Legal Assistant", layout="wide")

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚖️ Legal AI Assistant")
st.sidebar.markdown(
    """
    **For Small & Medium Businesses**

    Upload a contract to:
    - Identify legal risks
    - Understand clauses
    - Get simple explanations
    """
)
st.sidebar.markdown("---")
st.sidebar.info("Supports PDF, DOCX, TXT\n\n🇮🇳 English & Hindi")

# ---------------- MAIN UI ----------------
st.title("GenAI Legal Assistant for SMEs")
st.write("Upload a contract file (PDF, DOCX, or TXT)")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "docx", "txt"]
)

# ---------------- FILE READER ----------------
def read_file(file):
    if file.name.endswith(".pdf"):
        reader = PdfReader(file)
        return "".join(page.extract_text() or "" for page in reader.pages)

    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join(p.text for p in doc.paragraphs)

    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")

    return ""

# ---------------- CLAUSE SPLITTER ----------------
def split_into_clauses(text):
    """
    Improved clause splitter for English + Hindi.
    Handles long unstructured legal text.
    """

    # Normalize whitespace
    text = text.replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())

    # Split on English + Hindi sentence markers
    sentences = re.split(r'(?<=[.!?।])\s+', text)

    clauses = []
    buffer = ""

    legal_triggers = [
        # English
        "shall", "must", "may", "will",
        "terminate", "termination",
        "indemnify", "indemnity",
        "penalty", "fine",
        "arbitration", "jurisdiction",
        "renew", "auto",
        "confidential", "non-compete",

        # Hindi (key legal verbs & nouns)
        "नियुक्त", "वेतन", "समाप्त",
        "क्षतिपूर्ति", "दंड",
        "गोपनीय", "मध्यस्थता",
        "अधिकार क्षेत्र", "नवीनीकरण",
        "प्रतिस्पर्धा", "उल्लंघन"
    ]

    def has_legal_intent(sentence):
        s = sentence.lower()
        return any(k in s for k in legal_triggers)

    for sent in sentences:
        sent = sent.strip()

        if len(sent) < 30:
            continue

        if has_legal_intent(sent):
            if buffer:
                clauses.append(buffer.strip())
            buffer = sent
        else:
            if buffer:
                buffer += " " + sent

    if buffer.strip():
        clauses.append(buffer.strip())

    return clauses if clauses else [text]


# ---------------- CLAUSE CLASSIFICATION ----------------
def classify_clause(text):
    t = text.lower()
    if "shall not" in t or "must not" in t:
        return "Prohibition"
    elif "shall" in t or "must" in t:
        return "Obligation"
    elif "may" in t:
        return "Right"
    return "General"

# ---------------- RISK DETECTION ----------------
def detect_risks(text):
    t = text.lower()
    risks = []

    if "penalty" in t or "fine" in t:
        risks.append("Penalty clause may impose financial burden.")
    if "indemnify" in t:
        risks.append("Indemnity clause shifts legal liability.")
    if "non-compete" in t:
        risks.append("Non-compete restricts future work or business.")
    if "terminate without notice" in t or "sole discretion" in t:
        risks.append("Unilateral termination favors one party.")
    if "arbitration" in t or "jurisdiction" in t:
        risks.append("Arbitration or jurisdiction clause may increase legal cost.")
    if "auto" in t and "renew" in t:
        risks.append("Auto-renewal may lock parties into agreement.")

    return risks

def score_clause(risks):
    if not risks:
        return "Low"
    elif len(risks) == 1:
        return "Medium"
    return "High"

def explain_clause(risks):
    if not risks:
        return "This clause appears standard and low risk."
    return "This clause may be risky because: " + " ".join(risks)

# ---------------- MAIN LOGIC ----------------
if uploaded_file is not None:

    original_text = read_file(uploaded_file)

    try:
        lang = detect(original_text)
    except:
        lang = "unknown"

    normalized_text = original_text

    t = normalized_text.lower()
    if "employee" in t or "salary" in t:
        contract_type = "Employment Agreement"
    elif "lease" in t or "rent" in t:
        contract_type = "Lease Agreement"
    elif "vendor" in t:
        contract_type = "Vendor Contract"
    elif "partner" in t:
        contract_type = "Partnership Deed"
    else:
        contract_type = "Service Contract"

    clauses = split_into_clauses(normalized_text)

    # -------- ANALYZE CLAUSES --------
    high_risk_count = 0
    clause_results = []

    for clause in clauses:
        risks = detect_risks(clause)
        risk_level = score_clause(risks)
        clause_type = classify_clause(clause)

        if risk_level == "High":
            high_risk_count += 1

        clause_results.append((clause, clause_type, risks, risk_level))

    # -------- OVERALL RISK --------
    if high_risk_count >= 3:
        overall_risk = "HIGH RISK"
    elif high_risk_count >= 1:
        overall_risk = "MEDIUM RISK"
    else:
        overall_risk = "LOW RISK"

    # -------- OVERVIEW --------
    st.markdown("## Contract Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        lang_label = "Hindi" if lang == "hi" else "English" if lang == "en" else "Unknown"
        st.success(f"{lang_label}")
        if lang == "hi":
            st.info("Hindi contract detected. Analysis performed on original text.")

    with col2:
        st.info(f" {contract_type}")

    with col3:
        if overall_risk == "HIGH RISK":
            st.error("HIGH RISK")
        elif overall_risk == "MEDIUM RISK":
            st.warning("MEDIUM RISK")
        else:
            st.success("LOW RISK")

    # -------- CLAUSE ANALYSIS --------
    st.markdown("## Clause-by-Clause Analysis")

    for i, (clause, clause_type, risks, risk_level) in enumerate(clause_results, start=1):
        with st.expander(f"Clause {i}"):
            st.write(clause)
            st.write(f"**Clause Type:** {clause_type}")
            st.write(f"**Risk Level:** {risk_level}")
            st.write(f"**Explanation:** {explain_clause(risks)}")

    # -------- SUMMARY --------
    st.markdown("## Overall Contract Risk Summary")
    st.write(f"**Overall Risk Level:** {overall_risk}")
    st.write(f"**Total Clauses Analyzed:** {len(clauses)}")
    st.write(f"**High-Risk Clauses:** {high_risk_count}")

    st.markdown("---")
    st.caption("⚖️ This tool provides informational insights only and does not constitute legal advice.")
