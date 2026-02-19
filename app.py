import streamlit as st
import fitz
import re
from pathlib import Path
import base64

st.set_page_config(page_title="Patent Analyzer", page_icon="🔬", layout="wide")

# Setup
BASE = Path.cwd()
PATENTS = BASE / "Patents"
HIGHLIGHTED = BASE / "highlighted"
PATENTS.mkdir(exist_ok=True)
HIGHLIGHTED.mkdir(exist_ok=True)

# ============================================================================
# CORE SEARCH - HANDLES PUNCTUATION
# ============================================================================

def search_pdf(pdf_path, keywords):
    """Search that ignores punctuation"""
    doc = fitz.open(str(pdf_path))
    results = {}
    
    for kw in keywords:
        results[kw] = {'found': False, 'pages': [], 'count': 0}
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text = page.get_text().lower()
        
        # Strip punctuation from page text
        text_no_punct = re.sub(r'[^\w\s]', ' ', text)
        text_clean = ' '.join(text_no_punct.split())
        
        for kw in keywords:
            # Strip punctuation from keyword
            kw_no_punct = re.sub(r'[^\w\s]', ' ', kw.lower())
            kw_clean = ' '.join(kw_no_punct.split())
            
            if kw_clean in text_clean:
                results[kw]['found'] = True
                results[kw]['count'] += text_clean.count(kw_clean)
                if page_num + 1 not in results[kw]['pages']:
                    results[kw]['pages'].append(page_num + 1)
    
    doc.close()
    
    found = sum(1 for r in results.values() if r['found'])
    match_pct = (found / len(keywords) * 100) if keywords else 0
    
    return results, match_pct

def highlight_pdf(pdf_path, output_path, keywords):
    """Highlight with punctuation handling"""
    doc = fitz.open(str(pdf_path))
    total = 0
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        
        for kw in keywords:
            # Try exact match
            areas = page.search_for(kw)
            
            # Try with punctuation variations
            if not areas:
                variations = [
                    f'"{kw}"', f'"{kw}', f'{kw}"',
                    f'"{kw},"', f'"{kw}.',
                    f'{kw},', f'{kw}.', f'{kw};',
                    f'({kw})', f'({kw},', f'({kw}.',
                    f"'{kw}'", f"'{kw},", f"'{kw}.",
                ]
                
                for var in variations:
                    areas = page.search_for(var)
                    if areas:
                        break
            
            # Highlight
            for area in areas:
                highlight = page.add_highlight_annot(area)
                highlight.set_colors(stroke=[1, 1, 0])
                highlight.set_opacity(0.4)
                highlight.update()
                total += 1
    
    doc.save(str(output_path))
    doc.close()
    return total

# ============================================================================
# UI
# ============================================================================

st.markdown("""
<style>
    .title {text-align: center; color: #1f77b4; font-size: 2.5rem; font-weight: bold; margin-bottom: 0.5rem;}
    .subtitle {text-align: center; color: #666; margin-bottom: 2rem;}
    .header {background: #1f77b4; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom: 15px;}
    .result-good {background: #d4edda; padding: 10px; border-left: 4px solid #28a745; margin: 5px 0; border-radius: 3px;}
    .result-bad {background: #f8d7da; padding: 10px; border-left: 4px solid #dc3545; margin: 5px 0; border-radius: 3px;}
    .info-box {background: #d1ecf1; padding: 10px; border-radius: 5px; margin: 10px 0;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🔬 Patent Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle"> keyword search engine </div>', unsafe_allow_html=True)

if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False

col1, col2, col3 = st.columns([1, 1.2, 1.2])

# ============================================================================
# COLUMN 1: UPLOAD
# ============================================================================

with col1:
    st.markdown('<div class="header">📁 UPLOAD</div>', unsafe_allow_html=True)
    
    uploaded = st.file_uploader("Choose PDF file", type=['pdf'])
    
    if uploaded:
        pdf_path = PATENTS / uploaded.name
        with open(pdf_path, 'wb') as f:
            f.write(uploaded.getbuffer())
        
        doc = fitz.open(str(pdf_path))
        pages = doc.page_count
        size_mb = len(uploaded.getvalue()) / (1024 * 1024)
        doc.close()
        
        st.success(f"✅ {pages} pages | {size_mb:.1f} MB")
        st.session_state.pdf_path = pdf_path
    else:
        st.info("📤 Upload a PDF")
        st.markdown("""
        <div class="info-box">
            <b>💡 Tips:</b><br>
            • Supports files up to 2GB<br>
            • Search ignores punctuation<br>
            • Finds "word" even in "word,"
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# COLUMN 2: SEARCH
# ============================================================================

with col2:
    st.markdown('<div class="header">🔍 SEARCH</div>', unsafe_allow_html=True)
    
    if 'pdf_path' in st.session_state:
        
        keywords = st.text_area(
            "Enter keywords (one per line):",
            height=170,
            placeholder="gating\nsynchronization\nimage stream",
            help="Enter keywords without quotes or punctuation"
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            analyze = st.button("🚀 ANALYZE", type="primary", use_container_width=True)
        
        with col_b:
            if st.session_state.analyzed:
                if st.button("🔄 RESET", use_container_width=True):
                    st.session_state.analyzed = False
                    st.rerun()
        
        if analyze:
            if keywords.strip():
                kw_list = [k.strip() for k in keywords.split('\n') if k.strip()]
                
                with st.spinner("Analyzing..."):
                    results, match = search_pdf(st.session_state.pdf_path, kw_list)
                    
                    out_path = HIGHLIGHTED / f"highlighted_{st.session_state.pdf_path.name}"
                    found_kw = [k for k, v in results.items() if v['found']]
                    
                    highlights = 0
                    if found_kw:
                        highlights = highlight_pdf(st.session_state.pdf_path, out_path, found_kw)
                    
                    st.session_state.analyzed = True
                    st.session_state.results = results
                    st.session_state.match_pct = match
                    st.session_state.highlighted_path = out_path
                    st.session_state.highlights = highlights
                    
                st.success("✅ Analysis complete!")
                st.rerun()
            else:
                st.error("❌ Enter at least one keyword")
        
        # Results
        if st.session_state.analyzed:
            st.markdown("---")
            
            match = st.session_state.match_pct
            
            if match >= 80:
                emoji = "🟢"
                status = "EXCELLENT"
            elif match >= 50:
                emoji = "🟡"
                status = "GOOD"
            else:
                emoji = "🔴"
                status = "NEEDS REVIEW"
            
            st.markdown(f"### {emoji} {match:.0f}% Match - {status}")
            
            for kw, data in st.session_state.results.items():
                if data['found']:
                    pages = ', '.join(map(str, data['pages']))
                    st.markdown(f"""
                    <div class="result-good">
                        <b>✅ "{kw}"</b><br>
                        📄 Pages: {pages}<br>
                        🔢 Found: {data['count']} time(s)
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="result-bad">
                        <b>❌ "{kw}"</b><br>
                        Not found in document
                    </div>
                    """, unsafe_allow_html=True)
            
            st.info(f"🎨 {st.session_state.highlights} highlights in PDF")
    else:
        st.info("👈 Upload PDF first")

# ============================================================================
# COLUMN 3: VIEWER
# ============================================================================

with col3:
    st.markdown('<div class="header">📄 PDF VIEWER</div>', unsafe_allow_html=True)
    
    if st.session_state.analyzed and 'highlighted_path' in st.session_state:
        pdf_path = st.session_state.highlighted_path
        
        if pdf_path.exists():
            # Download
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "⬇️ Download Highlighted PDF",
                    f,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    use_container_width=True
                )
            
            # Viewer
            with open(pdf_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700px" type="application/pdf"></iframe>',
                unsafe_allow_html=True
            )
            
            st.caption("💡 Best in Edge/Firefox. Use Download if preview fails.")
    else:
        st.info("📄 PDF will appear after analysis")

# Footer
st.markdown("---")
st.caption("🔬 Patent Analyzer | keyword search engine ")
