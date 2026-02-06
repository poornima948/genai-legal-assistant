import streamlit as st
from PyPDF2 import PdfReader
import docx
from langdetect import detect
import re
import json
from datetime import datetime

# ================= PAGE CONFIG =================
st.set_page_config(page_title="GenAI Legal Assistant", layout="wide")

# ================= SIDEBAR =================
st.sidebar.title("⚖️ Legal AI Assistant")
st.sidebar.markdown("""
**For Small & Medium Businesses**

Upload a contract to:
- Identify legal risks
- Understand clauses
- Get simple explanations
""")
st.sidebar.markdown("---")
st.sidebar.info("Supports PDF, DOCX, TXT\n🇮🇳 English & Hindi")

# ================= MAIN UI =================
st.title("GenAI Legal Assistant for SMEs")
st.write("Upload a contract file (PDF, DOCX, or TXT)")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["pdf", "docx", "txt"]
)

# ================= FILE READER =================
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

# ================= CLAUSE SPLITTER =================
def split_into_clauses(text):
    text = text.replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    sentences = re.split(r'(?<=[.!?।])\s+', text)

    clauses, buffer = [], ""
    triggers = [
        "shall","must","may","terminate","indemnify","penalty",
        "arbitration","jurisdiction","renew","confidential",
        "non-compete","वेतन","समाप्त","क्षतिपूर्ति","दंड","मध्यस्थता"
    ]

    for sent in sentences:
        if len(sent) < 30:
            continue
        if any(k in sent.lower() for k in triggers):
            if buffer:
                clauses.append(buffer.strip())
            buffer = sent
        else:
            buffer += " " + sent

    if buffer.strip():
        clauses.append(buffer.strip())

    return clauses if clauses else [text]

# ================= NLP HELPERS =================
def classify_clause(text):
    t = text.lower()
    if "shall not" in t or "must not" in t:
        return "Prohibition"
    elif "shall" in t or "must" in t:
        return "Obligation"
    elif "may" in t:
        return "Right"
    return "General"

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
        risks.append("Arbitration or jurisdiction may increase legal cost.")
    if "auto" in t and "renew" in t:
        risks.append("Auto-renewal may lock parties into agreement.")
    return risks

def score_clause(risks):
    if not risks:
        return "Low"
    return "Medium" if len(risks) == 1 else "High"

def explain_clause(risks):
    if not risks:
        return "This clause appears standard and low risk."
    return "This clause may be risky because: " + " ".join(risks)

def detect_ambiguity(text):
    ambiguous = [
        "reasonable","as required","from time to time",
        "at discretion","as deemed fit","as applicable"
    ]
    return [a for a in ambiguous if a in text.lower()]

def mitigation_advice(risks):
    advice = []
    for r in risks:
        if "termination" in r.lower():
            advice.append("Add mutual notice period for termination.")
        if "non-compete" in r.lower():
            advice.append("Limit non-compete scope and duration.")
        if "indemnity" in r.lower():
            advice.append("Cap indemnity liability to a reasonable amount.")
        if "auto-renew" in r.lower():
            advice.append("Add opt-out clause before renewal.")
    return advice

def extract_entities(text):
    return {
        "Dates": re.findall(r'\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b', text),
        "Amounts": re.findall(r'₹\s?\d+|INR\s?\d+', text),
        "Jurisdiction": re.findall(
            r'\b(India|Delhi|Mumbai|Bangalore|Chennai)\b', text, re.I
        ),
        "Parties": re.findall(
            r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b', text
        )
    }

# ================= AUDIT LOG =================
def log_audit(contract_type, overall_risk):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "contract_type": contract_type,
        "overall_risk": overall_risk
    }
    with open("audit_log.json", "a") as f:
        f.write(json.dumps(entry) + "\n")

# ================= TEMPLATES =================
TEMPLATES = {
    "Employment Agreement": "Balanced employment agreement with mutual termination notice and limited non-compete.",
    "Vendor Contract": "Vendor agreement with capped indemnity and clear payment terms.",
    "Lease Agreement": "Lease with fixed lock-in and explicit renewal consent.",
    "Service Contract": "Service contract defining deliverables and liability caps."
}

# ================= MAIN LOGIC =================
if uploaded_file:
    text = read_file(uploaded_file)

    try:
        lang = detect(text)
    except:
        lang = "unknown"

    t = text.lower()
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

    clauses = split_into_clauses(text)

    clause_data = []
    high_risk_count = 0

    for clause in clauses:
        risks = detect_risks(clause)
        risk_level = score_clause(risks)
        if risk_level == "High":
            high_risk_count += 1
        clause_data.append(
            (clause, classify_clause(clause), risks, risk_level)
        )

    if high_risk_count >= 3:
        overall_risk = "HIGH RISK"
    elif high_risk_count >= 1:
        overall_risk = "MEDIUM RISK"
    else:
        overall_risk = "LOW RISK"

    log_audit(contract_type, overall_risk)

    # ---------- OVERVIEW ----------
    st.markdown("## 📄 Contract Overview")
    c1, c2, c3 = st.columns(3)

    c1.success("Hindi" if lang == "hi" else "English")
    c2.info(contract_type)

    with c3:
        if overall_risk == "HIGH RISK":
            st.error("HIGH RISK")
        elif overall_risk == "MEDIUM RISK":
            st.warning("MEDIUM RISK")
        else:
            st.success("LOW RISK")

    # ---------- ENTITIES ----------
    st.markdown("## 🏷️ Extracted Entities")
    for k, v in extract_entities(text).items():
        st.write(f"**{k}:** {', '.join(set(v)) if v else 'Not found'}")

    # ---------- CLAUSE ANALYSIS ----------
    st.markdown("## 🔍 Clause-by-Clause Analysis")
    for i, (c, ct, r, s) in enumerate(clause_data, start=1):
        with st.expander(f"Clause {i}"):
            st.write(c)
            st.write(f"**Clause Type:** {ct}")
            st.write(f"**Risk Level:** {s}")
            st.write(f"**Explanation:** {explain_clause(r)}")

            amb = detect_ambiguity(c)
            if amb:
                st.warning(f"Ambiguous terms detected: {', '.join(amb)}")

            advice = mitigation_advice(r)
            if advice:
                st.write("**Suggested Mitigation:**")
                for a in advice:
                    st.write(f"- {a}")

    # ---------- PLAIN-LANGUAGE SUMMARY ----------
    st.markdown("## 🧾 Plain-Language Contract Summary")

    summary_lines = [
        f"This is a **{contract_type}**.",
        f"The overall legal risk of this contract is **{overall_risk}**.",
        f"A total of **{len(clauses)} clauses** were analyzed."
    ]

    if high_risk_count > 0:
        summary_lines.append(
            f"There are **{high_risk_count} high-risk clauses** that may require renegotiation."
        )
    else:
        summary_lines.append(
            "No high-risk clauses were detected. The contract appears relatively safe."
        )

    for line in summary_lines:
        st.write("- " + line)

    # ---------- TEMPLATE ----------
    st.markdown("## 📑 SME-Friendly Contract Template")
    st.info(TEMPLATES.get(contract_type, "Template not available"))

    # ---------- DOWNLOAD ----------
    report_text = "\n".join(summary_lines)
    st.download_button(
        "📄 Download Contract Risk Summary",
        data=report_text,
        file_name="contract_risk_summary.txt",
        mime="text/plain"
    )

    st.caption("⚖️ Informational tool only. Not legal advice.")
