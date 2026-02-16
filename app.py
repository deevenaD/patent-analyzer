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
# CORE SEARCH - SIMPLE AND ACCURATE
# ============================================================================

def clean_text(text):
    """Normalize whitespace"""
    return ' '.join(text.split())

def search_pdf(pdf_path, keywords):
    """Simple, accurate search"""
    doc = fitz.open(str(pdf_path))
    results = {}
    
    for kw in keywords:
        results[kw] = {'found': False, 'pages': [], 'count': 0}
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text = clean_text(page.get_text().lower())
        
        for kw in keywords:
            kw_clean = clean_text(kw.lower())
            if kw_clean in text:
                results[kw]['found'] = True
                results[kw]['count'] += text.count(kw_clean)
                if page_num + 1 not in results[kw]['pages']:
                    results[kw]['pages'].append(page_num + 1)
    
    doc.close()
    
    found = sum(1 for r in results.values() if r['found'])
    match_pct = (found / len(keywords) * 100) if keywords else 0
    
    return results, match_pct

def highlight_pdf(pdf_path, output_path, keywords):
    """Simple highlighting - just search and mark"""
    doc = fitz.open(str(pdf_path))
    total = 0
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        
        for kw in keywords:
            # Search for the keyword
            areas = page.search_for(kw)
            
            # Highlight each occurrence
            for area in areas:
                page.add_highlight_annot(area)
                total += 1
    
    doc.save(str(output_path))
    doc.close()
    return total

# ============================================================================
# CLEAN UI
# ============================================================================

st.markdown("""
<style>
    .title {text-align: center; color: #1f77b4; font-size: 2.5rem; font-weight: bold; margin-bottom: 0.5rem;}
    .subtitle {text-align: center; color: #666; margin-bottom: 2rem;}
    .header {background: #1f77b4; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;}
    .result-good {background: #d4edda; padding: 10px; border-left: 4px solid #28a745; margin: 5px 0; border-radius: 3px;}
    .result-bad {background: #f8d7da; padding: 10px; border-left: 4px solid #dc3545; margin: 5px 0; border-radius: 3px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🔬 Patent Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Accurate keyword search with page numbers</div>', unsafe_allow_html=True)

if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False

col1, col2, col3 = st.columns([1, 1.2, 1.2])

# ============================================================================
# COLUMN 1: UPLOAD
# ============================================================================

with col1:
    st.markdown('<div class="header">📁 UPLOAD PDF</div>', unsafe_allow_html=True)
    
    uploaded = st.file_uploader("Choose PDF file", type=['pdf'])
    
    if uploaded:
        pdf_path = PATENTS / uploaded.name
        with open(pdf_path, 'wb') as f:
            f.write(uploaded.getbuffer())
        
        doc = fitz.open(str(pdf_path))
        st.success(f"✅ Loaded: {doc.page_count} pages")
        doc.close()
        
        st.session_state.pdf_path = pdf_path
    else:
        st.info("Upload a PDF to start")

# ============================================================================
# COLUMN 2: SEARCH
# ============================================================================

with col2:
    st.markdown('<div class="header">🔍 SEARCH</div>', unsafe_allow_html=True)
    
    if 'pdf_path' in st.session_state:
        
        keywords = st.text_area(
            "Enter keywords (one per line):",
            height=150,
            placeholder="Example:\nprotein\nbinding\nmolecular"
        )
        
        if st.button("🚀 ANALYZE", type="primary", use_container_width=True):
            if keywords.strip():
                kw_list = [k.strip() for k in keywords.split('\n') if k.strip()]
                
                with st.spinner("Searching..."):
                    results, match = search_pdf(st.session_state.pdf_path, kw_list)
                    
                    # Create highlighted version
                    out_path = HIGHLIGHTED / f"highlighted_{st.session_state.pdf_path.name}"
                    found_kw = [k for k, v in results.items() if v['found']]
                    
                    if found_kw:
                        highlights = highlight_pdf(st.session_state.pdf_path, out_path, found_kw)
                    else:
                        highlights = 0
                    
                    st.session_state.analyzed = True
                    st.session_state.results = results
                    st.session_state.match_pct = match
                    st.session_state.highlighted_path = out_path
                    st.session_state.highlights = highlights
                    
                    st.rerun()
            else:
                st.error("Enter at least one keyword")
        
        # Show results
        if st.session_state.analyzed:
            st.markdown("---")
            
            match = st.session_state.match_pct
            color = "🟢" if match >= 80 else "🟡" if match >= 50 else "🔴"
            
            st.markdown(f"### {color} {match:.0f}% Match")
            
            for kw, data in st.session_state.results.items():
                if data['found']:
                    pages = ', '.join(map(str, data['pages']))
                    st.markdown(f"""
                    <div class="result-good">
                        <b>✅ "{kw}"</b><br>
                        📄 Pages: {pages} | Found: {data['count']}x
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="result-bad">
                        <b>❌ "{kw}"</b> - Not found
                    </div>
                    """, unsafe_allow_html=True)
            
            st.info(f"🎨 {st.session_state.highlights} highlights added")
    else:
        st.info("Upload PDF first")

# ============================================================================
# COLUMN 3: VIEWER
# ============================================================================

with col3:
    st.markdown('<div class="header">📄 PDF</div>', unsafe_allow_html=True)
    
    if st.session_state.analyzed and 'highlighted_path' in st.session_state:
        pdf_path = st.session_state.highlighted_path
        
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "⬇️ Download",
                    f,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    use_container_width=True
                )
            
            # Simple PDF display
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700px" type="application/pdf"></iframe>',
                unsafe_allow_html=True
            )
            
            st.caption("💡 Use Download button if preview doesn't work")
    else:
        st.info("PDF will appear after analysis")

st.markdown("---")
st.caption("🔬 Patent Analyzer | Simple & Accurate")
