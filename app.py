import json
import streamlit as st
import difflib
import requests
from collections import defaultdict

# ---- PAGE CONFIG ----
st.set_page_config(
    page_title="Text Correction Viewer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Text Correction Viewer")

# ---- Helper function to load JSON ----
def load_json_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load JSON from URL: {e}")
        return None

# ---- Check query param for gist ----
query_params = st.query_params
json_url = query_params.get("file")
if isinstance(json_url, list):
    json_url = json_url[0]
    
if json_url:
    data = load_json_from_url(json_url)
else:
    # ---- File uploader fallback ----
    uploaded_file = st.file_uploader("📁 Upload JSON file with corrections", type="json")
    if uploaded_file is not None:
        data = json.load(uploaded_file)
    else:
        data = None

if not data:
    st.info("Please upload a JSON file or use a link with ?file=<gist_raw_url> to view text corrections.")
    st.stop()

# ---- Collect keywords ----
all_keywords = sorted(set(k.strip() for entry in data for k in entry['keywords'].split(',')))

# ---- Keyword filter ----
selected_keywords = st.multiselect(
    "🔎 Filter by keywords (select None for all)",
    all_keywords,
    default=[]
)
if selected_keywords:
    filtered_data = [entry for entry in data if any(
        k.strip() in selected_keywords for k in entry['keywords'].split(',')
    )]
else:
    filtered_data = data

if not filtered_data:
    st.warning("No entries match your filter.")
    st.stop()

# ---- Define priority order ----
priority_order = ["grammar", "spelling", "capitalization", "punctuation"]

def get_priority(entry):
    entry_keywords = [k.strip().lower() for k in entry['keywords'].split(',')]
    for i, kw in enumerate(priority_order):
        if kw in entry_keywords:
            return i
    return len(priority_order)

# ---- Organize entries by filename and sort inside each file ----
files_dict = defaultdict(list)
for idx, entry in enumerate(filtered_data):
    files_dict[entry['filename']].append((idx, entry))

for filename in files_dict:
    files_dict[filename].sort(key=lambda x: get_priority(x[1]))

# ---- Step 1: select a file ----
filenames = list(files_dict.keys())
selected_file = st.selectbox("📂 Select a file", filenames)

entries = files_dict[selected_file]
num_entries = len(entries)

# ---- Initialize session state ----
if "entry_idx" not in st.session_state:
    st.session_state.entry_idx = 0
if "last_file" not in st.session_state:
    st.session_state.last_file = selected_file

# Reset index if switching file
if st.session_state.last_file != selected_file:
    st.session_state.entry_idx = 0
    st.session_state.last_file = selected_file

# ---- Layout: prev button | dropdown | next button ----
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if st.button("⬅️ Prev") and st.session_state.entry_idx > 0:
        st.session_state.entry_idx -= 1
with col3:
    if st.button("Next ➡️") and st.session_state.entry_idx < num_entries - 1:
        st.session_state.entry_idx += 1
with col2:
    options = [f"Entry {i+1}" for i in range(num_entries)]
    # Use key instead of index
    selected_option = st.selectbox(
        "📑 Select correction entry",
        options,
        key=f"select_entry_{selected_file}"
    )
    st.session_state.entry_idx = options.index(selected_option)

# ---- Retrieve the currently selected entry ----
entry = entries[st.session_state.entry_idx][1]

# ---- Custom CSS for diff view ----
custom_css = """
<style>
table.diff {width: 100%; border-collapse: collapse; font-family: monospace;}
table.diff th {background: #222; color: white; padding: 6px;}
table.diff td {padding: 4px; color: cyan;}
td.diff_add {background-color: #004d00; color: #00ff00;}
td.diff_sub {background-color: #660000; color: #ff6666;}
td.diff_chg {background-color: #664d00; color: #ffcc00;}
span.diff_add {background-color: #00ff00; color: black; font-weight: bold;}
span.diff_sub {background-background: #ff6666; color: black; font-weight: bold;}
span.diff_chg {background-color: #ffcc00; color: black; font-weight: bold;}
</style>
"""

# ---- Render chosen entry ----
st.markdown("### ℹ️ Explanation and Keywords")
st.markdown(f"**Keywords:** {entry['keywords']}")
st.markdown(f"**Explanation:** {entry['explanation']}")

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Original")
    st.code(entry['original_txt'], language="markdown")
with col2:
    st.markdown("### Corrected")
    st.code(entry['correction'], language="markdown")

# ---- Diff view ----
st.markdown("### 🔍 Diff View")
diff_html = difflib.HtmlDiff(wrapcolumn=80).make_table(
    entry['original_txt'].splitlines(),
    entry['correction'].splitlines(),
    fromdesc='Original',
    todesc='Corrected',
    context=True,
    numlines=3
)
st.components.v1.html(custom_css + diff_html, height=400, scrolling=True)
