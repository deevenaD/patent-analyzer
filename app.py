import streamlit as st
import fitz
import re
from pathlib import Path
from difflib import SequenceMatcher
import base64

st.set_page_config(
    page_title="AI Patent Analyzer",
    page_icon="🔍",
    layout="wide"
)

BASE_FOLDER = Path.cwd()
PATENTS_FOLDER = BASE_FOLDER / "Patents"
HIGHLIGHTED_FOLDER = BASE_FOLDER / "highlighted"

PATENTS_FOLDER.mkdir(exist_ok=True)
HIGHLIGHTED_FOLDER.mkdir(exist_ok=True)

def clean_text(text):
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def search_pdf(pdf_path, search_items):
    doc = fitz.open(str(pdf_path))
    results = {}
    
    for item in search_items:
        results[item] = {'count': 0, 'pages': [], 'found': False}
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        page_text = page.get_text("text")
        page_text_clean = clean_text(page_text).lower()
        
        for item in search_items:
            item_clean = clean_text(item).lower()
            
            if item_clean in page_text_clean:
                results[item]['found'] = True
                count = page_text_clean.count(item_clean)
                results[item]['count'] += count
                
                if page_num + 1 not in results[item]['pages']:
                    results[item]['pages'].append(page_num + 1)
    
    doc.close()
    
    total_items = len(search_items)
    matched_items = sum(1 for r in results.values() if r['found'])
    match_percentage = (matched_items / total_items * 100) if total_items > 0 else 0
    
    return results, match_percentage

def highlight_pdf(pdf_path, output_path, search_items):
    doc = fitz.open(str(pdf_path))
    total_highlights = 0
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        page_text = page.get_text("text")
        page_text_clean = clean_text(page_text).lower()
        
        for item in search_items:
            item_clean = clean_text(item).lower()
            
            if item_clean not in page_text_clean:
                continue
            
            words = item_clean.split()
            
            if len(words) == 1:
                instances = page.search_for(words[0], quads=True)
                for inst in instances:
                    highlight = page.add_highlight_annot(inst)
                    highlight.set_colors(stroke=[1, 0.9, 0])
                    highlight.set_opacity(0.35)
                    highlight.update()
                    total_highlights += 1
            else:
                first_instances = page.search_for(words[0], quads=True)
                
                for inst in first_instances:
                    rect = inst.rect
                    char_width = (rect.x1 - rect.x0) / len(words[0]) if len(words[0]) > 0 else 10
                    estimated_width = char_width * len(item_clean)
                    
                    expanded = fitz.Rect(
                        rect.x0, rect.y0 - 2,
                        min(rect.x0 + estimated_width * 1.4, page.rect.width),
                        rect.y1 + 2
                    )
                    
                    try:
                        rect_text = page.get_textbox(expanded)
                        rect_clean = clean_text(rect_text).lower()
                        similarity = SequenceMatcher(None, item_clean, rect_clean).ratio()
                        
                        if similarity > 0.65:
                            highlight = page.add_highlight_annot(expanded)
                            highlight.set_colors(stroke=[1, 0.9, 0])
                            highlight.set_opacity(0.35)
                            highlight.update()
                            total_highlights += 1
                    except:
                        pass
    
    doc.save(str(output_path))
    doc.close()
    return total_highlights

st.markdown("""
<style>
.main-title {font-size: 2.5rem; font-weight: bold; text-align: center; color: #1f77b4; margin-bottom: 2rem;}
.column-header {font-size: 1.3rem; font-weight: bold; padding: 10px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 5px; margin-bottom: 1rem; text-align: center;}
.metric-box {background: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin: 10px 0;}
.success-box {background: #d4edda; padding: 10px; border-radius: 5px; border-left: 4px solid #28a745; margin: 5px 0;}
.warning-box {background: #fff3cd; padding: 10px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 5px 0;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🔍 AI Patent Analyzer</div>', unsafe_allow_html=True)

if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False

col1, col2, col3 = st.columns([1, 1.2, 1.3])

with col1:
    st.markdown('<div class="column-header">📁 SOURCE</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
    
    if uploaded_file:
        pdf_path = PATENTS_FOLDER / uploaded_file.name
        with open(pdf_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        doc = fitz.open(str(pdf_path))
        st.markdown(f"""
        <div class="metric-box">
            <b>📄 File:</b> {uploaded_file.name}<br>
            <b>📑 Pages:</b> {doc.page_count}<br>
            <b>💾 Size:</b> {len(uploaded_file.getvalue()) / 1024:.1f} KB
        </div>
        """, unsafe_allow_html=True)
        doc.close()
        st.session_state.current_pdf = pdf_path
    else:
        st.info("📤 Upload a PDF to begin")

with col2:
    st.markdown('<div class="column-header">🤖 AI AGENT</div>', unsafe_allow_html=True)
    
    if 'current_pdf' in st.session_state:
        keywords_input = st.text_area(
            "🔑 Enter keywords (one per line):",
            height=150,
            placeholder="Example:\nPEPTIDE-BASED PROTACs\npoly-D-arginine\nwarhead discovery"
        )
        
        if st.button("🚀 ANALYZE", use_container_width=True, type="primary"):
            if not keywords_input.strip():
                st.error("❌ Please enter keywords!")
            else:
                search_items = [k.strip() for k in keywords_input.split('\n') if k.strip()]
                
                with st.spinner('🔍 Analyzing...'):
                    results, match_pct = search_pdf(st.session_state.current_pdf, search_items)
                    highlighted_path = HIGHLIGHTED_FOLDER / f"highlighted_{st.session_state.current_pdf.name}"
                    total_highlights = highlight_pdf(
                        st.session_state.current_pdf,
                        highlighted_path,
                        [k for k, v in results.items() if v['found']]
                    )
                    
                    st.session_state.analyzed = True
                    st.session_state.results = results
                    st.session_state.match_percentage = match_pct
                    st.session_state.highlighted_pdf = highlighted_path
                    st.session_state.total_highlights = total_highlights
        
        if st.session_state.analyzed:
            st.markdown("---")
            match_pct = st.session_state.match_percentage
            color = "#28a745" if match_pct >= 80 else "#ffc107" if match_pct >= 50 else "#dc3545"
            emoji = "🟢" if match_pct >= 80 else "🟡" if match_pct >= 50 else "🔴"
            
            st.markdown(f"""
            <div class="metric-box" style="border-left-color: {color};">
                <h2 style="color: {color}; margin: 0;">{emoji} {match_pct:.1f}% Match</h2>
            </div>
            """, unsafe_allow_html=True)
            
            for item, data in st.session_state.results.items():
                if data['found']:
                    st.markdown(f"""
                    <div class="success-box">
                        <b>✅ "{item[:50]}{'...' if len(item) > 50 else ''}"</b><br>
                        📄 Pages: {', '.join(map(str, data['pages']))}<br>
                        🔢 Count: {data['count']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="warning-box"><b>❌ "{item[:50]}{'...' if len(item) > 50 else ''}"</b></div>""", unsafe_allow_html=True)
    else:
        st.info("👈 Upload a PDF first")

with col3:
    st.markdown('<div class="column-header">📄 VIEWER</div>', unsafe_allow_html=True)
    
    if st.session_state.analyzed and 'highlighted_pdf' in st.session_state:
        pdf_path = st.session_state.highlighted_pdf
        
        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Download Highlighted PDF", f, file_name=pdf_path.name, mime="application/pdf", use_container_width=True)
            
            with open(pdf_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            
            st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf" style="border: 2px solid #ddd; border-radius: 5px;"></iframe>', unsafe_allow_html=True)
    else:
        st.info("📄 PDF will appear after analysis")