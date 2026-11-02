import html
import json
import os
import re
from collections import Counter

import streamlit as st
from groq import Groq
from pypdf import PdfReader

MODEL = "openai/gpt-oss-120b"
MAX_CHARS = 12000
W_TYPE = {"must": 3, "nice": 1}
W_STATUS = {"met": 1.0, "partial": 0.5, "missing": 0.0}
LABEL = {"met": "MATCH", "partial": "PARTIAL", "missing": "MISSING"}
CODE = {"met": "m", "partial": "p", "missing": "x"}
ORDER = {"missing": 0, "partial": 1, "met": 2}
TONES = {
    "Punchy": "short, active, specific. Cut filler.",
    "Formal": "polished and professional.",
    "Technical": "precise, tool-and-stack heavy.",
}

st.set_page_config(page_title="Redline", page_icon="🟩", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;700&display=swap');
:root{--bg:#0D100E;--sf:#151915;--ln:#2A322B;--tx:#E8ECE2;--mu:#8A9488;--lime:#D4FF3F;--amb:#FFB347;--red:#FF5A5A;--mono:'IBM Plex Mono',monospace;--disp:'Bricolage Grotesque',sans-serif;}
.stApp{background-color:var(--bg);background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:44px 44px;color:var(--tx);font-family:'IBM Plex Sans',sans-serif;}
.stApp p,.stApp li,.stApp label,.stApp span.st-emotion-cache-ue6h4q{color:var(--tx);}
[data-testid="stHeader"]{background:transparent;}
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden;}
.block-container{max-width:1180px;padding-top:2rem;}
[data-testid="stSidebar"]{background:var(--sf);border-right:1px solid var(--ln);}
.stTextArea textarea,.stTextInput input{background:var(--sf)!important;color:var(--tx)!important;border-radius:0!important;font-family:var(--mono);font-size:.82rem;}
[data-baseweb="textarea"],[data-baseweb="base-input"]{background:var(--sf)!important;border-color:var(--ln)!important;border-radius:0!important;}
[data-testid="stFileUploaderDropzone"]{background:var(--sf);border:1px dashed var(--ln);border-radius:0;}
.stTabs [data-baseweb="tab"]{font-family:var(--mono);text-transform:uppercase;font-size:.72rem;letter-spacing:.08em;color:var(--mu);}
.stTabs [aria-selected="true"]{color:var(--lime);}
.stTabs [data-baseweb="tab-highlight"]{background:var(--lime);}
.stRadio label p{font-family:var(--mono);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;}
[data-testid="stAlert"]{border-radius:0;border:1px solid var(--ln);}
.stButton>button,.stDownloadButton>button{border:1px solid var(--lime);border-radius:0;background:transparent;color:var(--lime);font-family:var(--mono);font-weight:700;text-transform:uppercase;letter-spacing:.08em;padding:.6rem 1.4rem;transition:.12s;}
.stButton>button p,.stDownloadButton>button p{color:inherit!important;}
.stButton>button:hover,.stDownloadButton>button:hover{background:var(--lime);color:#0D100E;border-color:var(--lime);}
button[kind="primary"],button[data-testid="stBaseButton-primary"]{background:var(--lime)!important;color:#0D100E!important;box-shadow:5px 5px 0 rgba(212,255,63,.25);}
button[data-testid="stBaseButton-primary"]:hover{transform:translate(2px,2px);box-shadow:3px 3px 0 rgba(212,255,63,.25);}

.mast{padding:6px 0 22px;border-bottom:1px solid var(--ln);margin-bottom:6px;}
.kick{font-family:var(--mono);font-size:.72rem;letter-spacing:.22em;color:var(--mu);}
.h{font-family:var(--disp);font-weight:800;font-size:clamp(4rem,12vw,8.5rem);line-height:.9;letter-spacing:-.04em;margin:.5rem 0 .9rem;}
.h em{font-style:normal;background:var(--lime);color:#0D100E;padding:0 .1em;display:inline-block;transform:rotate(-1.5deg);margin-left:.04em;}
.sub{max-width:580px;color:var(--mu);font-size:1.02rem;}
.sec{display:flex;align-items:baseline;gap:14px;margin:2.8rem 0 1rem;}
.sec .n{font-family:var(--mono);color:var(--lime);font-size:.8rem;}
.sec .t{font-family:var(--disp);font-weight:800;font-size:1.7rem;letter-spacing:-.02em;}
.sec .r{margin-left:auto;font-family:var(--mono);font-size:.68rem;color:var(--mu);letter-spacing:.1em;text-transform:uppercase;}
.dt{font-family:var(--mono);font-size:.7rem;letter-spacing:.16em;color:var(--mu);margin-bottom:6px;}

.vd{display:grid;grid-template-columns:auto 1fr;gap:40px;align-items:end;margin-bottom:24px;}
.score{font-family:var(--disp);font-weight:800;font-size:clamp(6rem,17vw,12rem);line-height:.8;letter-spacing:-.06em;}
.score small{font-size:.28em;letter-spacing:0;margin-left:.1em;opacity:.7;}
.m{color:var(--lime);}.p{color:var(--amb);}.x{color:var(--red);}
.vl{font-family:var(--disp);font-weight:800;font-size:clamp(1.5rem,3vw,2.3rem);line-height:1.05;letter-spacing:-.02em;}
.vs{max-width:580px;margin:.6rem 0 .9rem;}
.warn{font-family:var(--mono);font-size:.76rem;color:var(--red);margin:0 0 .8rem;}
.cnt span{font-family:var(--mono);font-size:.75rem;margin-right:18px;text-transform:uppercase;letter-spacing:.08em;}
.cnt span:before{content:"";display:inline-block;width:10px;height:10px;margin-right:7px;background:currentColor;}
.cnt span.x:before{background:transparent;border:1.5px dashed currentColor;}
.strip{display:flex;gap:4px;height:30px;margin:6px 0 4px;}
.seg{flex:var(--w) 1 0;min-width:10px;}
.seg.m{background:var(--lime);}.seg.p{background:var(--amb);}.seg.x{border:1.5px dashed var(--red);}
.sl{font-family:var(--mono);font-size:.64rem;color:var(--mu);letter-spacing:.08em;text-transform:uppercase;}

.grp{font-family:var(--mono);font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;color:var(--mu);margin:20px 0 8px;border-bottom:1px solid var(--ln);padding-bottom:5px;}
.rq{display:grid;grid-template-columns:84px 1fr;gap:16px;background:var(--sf);border:1px solid var(--ln);border-left:4px solid var(--c);padding:12px 14px;margin-bottom:8px;animation:in .4s both;}
.rq.m{--c:var(--lime);}.rq.p{--c:var(--amb);}.rq.x{--c:var(--red);}
.pill{font-family:var(--mono);font-weight:700;font-size:.68rem;letter-spacing:.1em;color:var(--c);padding-top:3px;}
.rn{font-weight:600;font-size:1rem;}
.ty{font-family:var(--mono);font-size:.6rem;border:1px solid var(--mu);color:var(--mu);padding:1px 6px;margin-left:8px;letter-spacing:.1em;vertical-align:middle;}
.jq,.ev,.nt{font-size:.86rem;margin-top:5px;}
.jq{color:var(--mu);font-style:italic;}
.ev{font-family:var(--mono);font-size:.78rem;color:var(--c);}
.nt{opacity:.85;}
.uv{color:var(--amb);font-family:var(--mono);font-size:.66rem;letter-spacing:.08em;}

.doc{background:var(--sf);border:1px solid var(--ln);padding:16px 18px;max-height:560px;overflow:auto;font-family:var(--mono);font-size:.78rem;line-height:1.7;word-break:break-word;}
mark{color:inherit;padding:0 1px;}
mark.m{background:rgba(212,255,63,.2);border-bottom:2px solid var(--lime);}
mark.p{background:rgba(255,179,71,.2);border-bottom:2px solid var(--amb);}
mark.x{background:rgba(255,90,90,.18);border-bottom:2px dashed var(--red);}
mark.rw{background:transparent;text-decoration:underline wavy #FF7AD9;text-underline-offset:4px;}
.lg{margin-top:8px;font-family:var(--mono);font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;}
.lg span{margin-right:16px;}

.rl{background:var(--sf);border:1px solid var(--ln);padding:14px 16px;margin-bottom:12px;animation:in .4s both;}
.rt{font-family:var(--mono);font-size:.66rem;letter-spacing:.16em;color:var(--mu);margin-bottom:8px;}
.old{color:var(--red);text-decoration:line-through;text-decoration-thickness:1.5px;font-size:.9rem;opacity:.9;}
.new{margin-top:8px;border-left:3px solid var(--lime);padding-left:12px;font-weight:500;font-size:.98rem;}
.ph{background:var(--amb);color:#0D100E;padding:0 4px;font-family:var(--mono);font-size:.82em;}
.why{font-family:var(--mono);font-size:.74rem;color:var(--mu);margin-top:8px;}
.gp{border:1px dashed var(--red);padding:12px 14px;margin-bottom:10px;}
.gn{font-family:var(--mono);color:var(--red);font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;}
.ga{margin-top:5px;font-size:.92rem;}
.empty{border:1px dashed var(--ln);padding:14px;color:var(--mu);font-style:italic;}
@keyframes in{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
@media (max-width:760px){.vd{grid-template-columns:1fr;gap:12px;}.rq{grid-template-columns:1fr;gap:4px;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------- helpers ----------
def esc(x):
    # '$' escaped so Streamlit never treats "$50k ... $80k" as LaTeX
    return html.escape(str(x)).replace("$", "&#36;")


def sec(n, title, right=""):
    st.markdown(
        f'<div class="sec"><span class="n">{n}</span><span class="t">{esc(title)}</span>'
        f'<span class="r">{esc(right)}</span></div>',
        unsafe_allow_html=True,
    )


def get_api_key():
    key = os.getenv("GROQ_API_KEY", "")
    try:
        key = key or st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        pass
    return key


def read_upload(f):
    if f.name.lower().endswith(".pdf"):
        reader = PdfReader(f)
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    return f.getvalue().decode("utf-8", "ignore").strip()


def clean(q):
    q = (q or "").strip().strip("\"'“”‘’")
    parts = [p.strip() for p in re.split(r"\.\.\.|…", q) if p.strip()]
    return max(parts, key=len) if parts else ""


def locate(text, quote):
    toks = quote.split()
    if not toks:
        return None
    m = re.search(r"\s+".join(re.escape(t) for t in toks), text, re.I)
    return (m.start(), m.end()) if m else None


def mark(text, spans):
    out, pos = [], 0
    for a, b, cls, tip in sorted(spans, key=lambda s: s[0]):
        if a < pos:
            continue
        out.append(esc(text[pos:a]))
        out.append(f'<mark class="{cls}" title="{esc(tip)}">{esc(text[a:b])}</mark>')
        pos = b
    out.append(esc(text[pos:]))
    return "".join(out).replace("\n", "<br>")


# ---------- analysis ----------
def analyze(api_key, resume, jd, tone):
    client = Groq(api_key=api_key)
    system = (
        "You compare a resume to a job post. Be honest and specific. Never flatter. "
        "Extract 8-16 concrete requirements from the JOB POST (skills, tools, experience, qualifications). "
        "type = 'must' if the post says required/must/minimum/years of X, else 'nice' (preferred/bonus). "
        "status = 'met' ONLY if the resume explicitly shows it; 'partial' if there is adjacent or weaker "
        "evidence; 'missing' otherwise. "
        "jd_quote and resume_quote MUST be copied EXACTLY, character for character, from the given text, "
        "under 20 words each. resume_quote is an empty string when status is missing. "
        "Then pick 4-7 weak or vague resume lines worth rewriting. 'original' must be copied exactly from the resume. "
        "'improved' must keep every fact true, use stronger verbs, and mirror the job post's wording ONLY where the "
        "resume truthfully supports it. NEVER invent skills, employers, titles or numbers. "
        "If a number would help but the resume doesn't give one, insert a placeholder like [X%] or [N users]. "
        f"Rewrite tone: {TONES[tone]} "
        "For each missing or partial requirement give honest gap advice: if the person likely has it, where to add it; "
        "if not, a realistic way to close or address the gap. Never tell them to fake it. "
        'Return ONLY valid JSON: {"summary":"2 blunt sentences","requirements":[{"requirement":"short name",'
        '"type":"must|nice","status":"met|partial|missing","jd_quote":"","resume_quote":"","note":"one sentence"}],'
        '"rewrites":[{"original":"","improved":"","why":"one sentence"}],'
        '"gaps":[{"requirement":"","advice":""}]}'
    )
    user = f"JOB POST:\n{jd[:MAX_CHARS]}\n\n-----\n\nRESUME:\n{resume[:MAX_CHARS]}"
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=6000,
    )
    return json.loads(resp.choices[0].message.content)


def enrich(data, resume, jd):
    reqs = []
    for r in data.get("requirements", []):
        status = r.get("status") if r.get("status") in W_STATUS else "missing"
        typ = "must" if r.get("type") == "must" else "nice"
        rq, jq = clean(r.get("resume_quote")), clean(r.get("jd_quote"))
        rs = locate(resume, rq) if rq else None
        js = locate(jd, jq) if jq else None
        unverified = False
        if status in ("met", "partial") and rs is None:
            unverified = True
            status = "partial"
        if status == "missing":
            rs, rq = None, ""
        reqs.append(
            {
                "requirement": str(r.get("requirement", "")).strip() or "Unnamed requirement",
                "type": typ,
                "status": status,
                "jq": jq if js else "",
                "rq": rq if rs else "",
                "rs": rs,
                "js": js,
                "note": str(r.get("note", "")),
                "unverified": unverified,
            }
        )
    rewrites = []
    for w in data.get("rewrites", []):
        o, n = str(w.get("original", "")).strip(), str(w.get("improved", "")).strip()
        if o and n:
            rewrites.append({"original": o, "improved": n, "why": str(w.get("why", "")), "span": locate(resume, clean(o))})
    gaps = [
        {"requirement": str(g.get("requirement", "")), "advice": str(g.get("advice", ""))}
        for g in data.get("gaps", [])
        if g.get("requirement") and g.get("advice")
    ]
    return {"summary": str(data.get("summary", "")), "reqs": reqs, "rewrites": rewrites, "gaps": gaps}


def fit_score(reqs):
    total = sum(W_TYPE[r["type"]] for r in reqs)
    earned = sum(W_TYPE[r["type"]] * W_STATUS[r["status"]] for r in reqs)
    return round(earned / total * 100) if total else 0


def verdict(score):
    if score >= 80:
        return "m", "Strong fit. Apply."
    if score >= 65:
        return "m", "Solid. Fix the gaps, then apply."
    if score >= 45:
        return "p", "Stretch. Doable if you tailor hard."
    return "x", "Long shot. Be honest with yourself."


# ---------- html builders (single line on purpose: blank lines/indents break st.markdown HTML) ----------
def verdict_html(res, score):
    reqs = res["reqs"]
    tone, label = verdict(score)
    c = Counter(r["status"] for r in reqs)
    must_missing = sum(1 for r in reqs if r["type"] == "must" and r["status"] == "missing")
    warn = (
        f'<div class="warn">{must_missing} must-have{"s" if must_missing != 1 else ""} missing. Those are what the screen is built around.</div>'
        if must_missing
        else ""
    )
    segs = "".join(
        f'<div class="seg {CODE[r["status"]]}" style="--w:{W_TYPE[r["type"]]}" title="{esc(r["requirement"])} · {LABEL[r["status"]]}"></div>'
        for r in sorted(reqs, key=lambda r: (-ORDER[r["status"]], r["type"] != "must"))
    )
    return (
        f'<div class="vd"><div class="score {tone}">{score}<small>%</small></div>'
        f'<div><div class="vl {tone}">{esc(label)}</div><p class="vs">{esc(res["summary"])}</p>{warn}'
        f'<div class="cnt"><span class="m">{c["met"]} match</span><span class="p">{c["partial"]} partial</span><span class="x">{c["missing"]} missing</span></div></div></div>'
        f'<div class="strip">{segs}</div>'
        f'<div class="sl">each block is one requirement · wide = must-have · hover for names</div>'
    )


def reqs_html(reqs, flt):
    shown = [r for r in reqs if flt == "All" or r["status"] == flt.lower()]
    if not shown:
        return '<div class="empty">Nothing in this filter.</div>'
    out = []
    for typ, title in (("must", "Must-haves"), ("nice", "Nice-to-haves")):
        grp = sorted([r for r in shown if r["type"] == typ], key=lambda r: ORDER[r["status"]])
        if not grp:
            continue
        out.append(f'<div class="grp">{title} · {len(grp)}</div>')
        for r in grp:
            cls = CODE[r["status"]]
            jq = f'<div class="jq">“{esc(r["jq"])}”</div>' if r["jq"] else ""
            if r["rq"]:
                ev = f'<div class="ev">Your resume: “{esc(r["rq"])}”</div>'
            elif r["status"] == "missing":
                ev = '<div class="ev">No evidence in your resume.</div>'
            else:
                ev = ""
            uv = '<div class="uv">UNVERIFIED · couldn\'t find the AI\'s quote in your resume, so this was downgraded</div>' if r["unverified"] else ""
            nt = f'<div class="nt">{esc(r["note"])}</div>' if r["note"] else ""
            out.append(
                f'<div class="rq {cls}"><div class="pill">{LABEL[r["status"]]}</div>'
                f'<div><div class="rn">{esc(r["requirement"])}<span class="ty">{typ.upper()}</span></div>{jq}{ev}{uv}{nt}</div></div>'
            )
    return "".join(out)


def rewrites_html(rewrites):
    if not rewrites:
        return '<div class="empty">No rewrite targets found. Either your bullets are solid or the model whiffed. Rerun to check.</div>'
    out = []
    for i, w in enumerate(rewrites, 1):
        imp = re.sub(r"\[[^\]]{1,24}\]", lambda m: f'<span class="ph">{m.group(0)}</span>', esc(w["improved"]))
        out.append(
            f'<div class="rl" style="animation-delay:{i * 60}ms"><div class="rt">REDLINE {i:02d}</div>'
            f'<div class="old">{esc(w["original"])}</div><div class="new">{imp}</div>'
            f'<div class="why">{esc(w["why"])}</div></div>'
        )
    return "".join(out)


def gaps_html(gaps):
    if not gaps:
        return '<div class="empty">No gaps flagged. Suspiciously clean. Check section 02.</div>'
    return "".join(
        f'<div class="gp"><div class="gn">{esc(g["requirement"])}</div><div class="ga">{esc(g["advice"])}</div></div>'
        for g in gaps
    )


def report_md(res, score):
    lines = [f"# Redline report: fit {score}%", "", res["summary"], "", "## Requirements"]
    for r in sorted(res["reqs"], key=lambda r: (r["type"] != "must", ORDER[r["status"]])):
        lines.append(f"- [{LABEL[r['status']]}] ({r['type']}) {r['requirement']}: {r['note']}")
    lines += ["", "## Rewrites"]
    for w in res["rewrites"]:
        lines += [f"- Before: {w['original']}", f"  After: {w['improved']}", f"  Why: {w['why']}"]
    lines += ["", "## Gaps"]
    lines += [f"- {g['requirement']}: {g['advice']}" for g in res["gaps"]]
    return "\n".join(lines)


# ---------- state ----------
st.session_state.setdefault("res", None)

# ---------- sidebar ----------
with st.sidebar:
    st.markdown("### Setup")
    api_key = st.text_input("Groq API key", value=get_api_key(), type="password")
    tone = st.selectbox("Rewrite tone", list(TONES.keys()))
    st.caption("Your text goes to Groq's API for the analysis. Nothing else is saved anywhere.")

# ---------- masthead ----------
st.markdown(
    '<div class="mast"><div class="kick">RESUME × JOB POST · GAP REPORT</div>'
    '<div class="h">Red<em>line</em></div>'
    '<div class="sub">Paste the resume. Paste the job post. Get marked-up proof of what matches, what\'s missing, and which lines are costing you the interview.</div></div>',
    unsafe_allow_html=True,
)

# ---------- input ----------
sec("01", "Feed it")
left, right = st.columns(2, gap="large")
with left:
    st.markdown('<div class="dt">YOUR RESUME</div>', unsafe_allow_html=True)
    t_paste, t_up = st.tabs(["Paste text", "Upload PDF / TXT"])
    with t_paste:
        resume_paste = st.text_area(
            "resume", height=320, label_visibility="collapsed", placeholder="Paste your resume as plain text..."
        )
    with t_up:
        up = st.file_uploader("resume file", type=["pdf", "txt"], label_visibility="collapsed")
        st.caption("If a file is uploaded, it wins over the pasted text.")
with right:
    st.markdown('<div class="dt">THE JOB POST</div>', unsafe_allow_html=True)
    jd_in = st.text_area(
        "job post", height=372, label_visibility="collapsed", placeholder="Paste the full job description..."
    )

resume_text = resume_paste
if up is not None:
    try:
        resume_text = read_upload(up)
        if not resume_text:
            st.error("No text in that file. Scanned PDF? Paste the text instead.")
        else:
            st.caption(f"Using {up.name} · {len(resume_text):,} characters")
    except Exception as e:
        st.error(f"Couldn't read that file: {e}")
        resume_text = ""

if st.button("Run the check", type="primary"):
    if not api_key:
        st.error("No API key. Paste it in the sidebar.")
    elif len(resume_text.strip()) < 200:
        st.error("Resume is too short to judge. Paste the whole thing.")
    elif len(jd_in.strip()) < 150:
        st.error("Job post is too short. Paste the full description, not the title.")
    else:
        with st.spinner("Reading your resume like a tired recruiter..."):
            try:
                resume_clean, jd_clean = resume_text.strip(), jd_in.strip()
                res = enrich(analyze(api_key, resume_clean, jd_clean, tone), resume_clean, jd_clean)
                if not res["reqs"]:
                    st.error("Model found no requirements. Rerun, or paste a fuller job post.")
                else:
                    res["resume"], res["jd"] = resume_clean, jd_clean
                    st.session_state.res = res
            except Exception as e:
                st.error(f"Analysis failed: {e}")

# ---------- results ----------
res = st.session_state.res
if res:
    reqs = res["reqs"]
    score = fit_score(reqs)

    sec("02", "The verdict", "computed from verified matches")
    st.markdown(verdict_html(res, score), unsafe_allow_html=True)

    sec("03", "Requirement by requirement")
    flt = st.radio("Filter", ["All", "Missing", "Partial", "Met"], horizontal=True, label_visibility="collapsed")
    st.markdown(reqs_html(reqs, flt), unsafe_allow_html=True)

    sec("04", "Both documents, marked up", "hover a highlight for the requirement")
    r_spans = [(r["rs"][0], r["rs"][1], CODE[r["status"]], r["requirement"]) for r in reqs if r["rs"]]
    for w in res["rewrites"]:
        if w["span"] and not any(w["span"][0] < e and s < w["span"][1] for s, e, _, _ in r_spans):
            r_spans.append((w["span"][0], w["span"][1], "rw", "redline target"))
    j_spans = [
        (r["js"][0], r["js"][1], CODE[r["status"]], f'{r["requirement"]} · {LABEL[r["status"]]}') for r in reqs if r["js"]
    ]
    d1, d2 = st.columns(2, gap="large")
    with d1:
        st.markdown('<div class="dt">THE JOB POST</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="doc">{mark(res["jd"], j_spans)}</div>', unsafe_allow_html=True)
    with d2:
        st.markdown('<div class="dt">YOUR RESUME</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="doc">{mark(res["resume"], r_spans)}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="lg"><span class="m">■ match</span><span class="p">■ partial</span>'
        '<span class="x">■ missing</span><span style="color:#FF7AD9">~ redline target</span></div>',
        unsafe_allow_html=True,
    )

    sec("05", "Redlines", "your line → better line")
    st.markdown(rewrites_html(res["rewrites"]), unsafe_allow_html=True)
    st.caption("Amber [brackets] mean a number belongs there. Fill in the real one or cut the claim. Don't invent it.")
    if res["rewrites"]:
        with st.expander("Copy-ready rewrites"):
            st.code("\n\n".join(w["improved"] for w in res["rewrites"]), language=None)

    sec("06", "The gaps", "what to do about them")
    st.markdown(gaps_html(res["gaps"]), unsafe_allow_html=True)
    st.caption("Done it for real? Put it on the page. Haven't? Don't fake it. They'll test you on it in the interview.")

    st.download_button("Download report (.md)", report_md(res, score), file_name="redline_report.md", mime="text/markdown")
