import json
import streamlit as st
import difflib
import requests
from collections import defaultdict
from urllib.parse import unquote

# ---- PAGE CONFIG ----
st.set_page_config(
    page_title="PR Correction Viewer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("PR Correction Viewer")

# ---- Helper function to load JSON ----
def load_json_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to load JSON from URL: {e}")
        return None


# ---- Check query param for s3 ----
s3_key = st.query_params.get("key")
if isinstance(s3_key, list):
    s3_key = s3_key[0]

data = None
if s3_key:
    s3_key = unquote(s3_key)
    # Backend redirect endpoint
    BACKEND_BASE_URL = st.secrets["BACKEND_BASE_URL"]
    json_url = f"{BACKEND_BASE_URL}/get-corrections/{s3_key}"
    try:
        response = requests.get(json_url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        st.error(f"Failed to load JSON from backend: {e}")
else:
    uploaded_file = st.file_uploader("📁 Upload JSON file with corrections", type="json")
    if uploaded_file:
        try:
            data = json.load(uploaded_file)
        except Exception as e:
            st.error(f"Error reading uploaded file: {e}")

# Guard against None
if not data:
    st.warning("No data loaded. Please provide a key in the URL or upload a JSON file.")
    st.stop()
from collections import defaultdict
import difflib
import streamlit as st

# ---- Organize entries by filename and sort inside each file ----
priority_order = ["grammar", "spelling", "capitalization", "punctuation"]

def get_priority(entry):
    entry_keywords = [k.strip().lower() for k in entry['keywords'].split(',')]
    for i, kw in enumerate(priority_order):
        if kw in entry_keywords:
            return i
    return len(priority_order)

files_dict = defaultdict(list)
for idx, entry in enumerate(data):
    files_dict[entry['filename']].append((idx, entry))

for filename in files_dict:
    files_dict[filename].sort(key=lambda x: get_priority(x[1]))

filenames = list(files_dict.keys())

# ---- Initialize session state ----
if "entry_idx" not in st.session_state:
    st.session_state.entry_idx = 0
if "selected_file" not in st.session_state:
    st.session_state.selected_file = filenames[0]

# ---- File selector (reusable) ----
def file_selector(location="top"):
    st.session_state.selected_file = st.selectbox(
        "📂 Select a file",
        filenames,
        index=filenames.index(st.session_state.selected_file),
        key=f"file_select_{location}"
    )

# ---- Navigation block (reusable) ----
def navigation_controls(entries, location="top"):
    num_entries = len(entries)
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("⬅️ Prev", key=f"prev_{location}") and st.session_state.entry_idx > 0:
            st.session_state.entry_idx -= 1
    with col3:
        if st.button("Next ➡️", key=f"next_{location}") and st.session_state.entry_idx < num_entries - 1:
            st.session_state.entry_idx += 1
    with col2:
        options = [f"Entry {i+1}" for i in range(num_entries)]
        st.session_state.entry_idx = st.selectbox(
            "📑 Select correction entry",
            range(num_entries),
            format_func=lambda i: options[i],
            key=f"select_entry_{location}_{st.session_state.selected_file}",
            index=st.session_state.entry_idx
        )

# ---- First set of file selector + controls ----
file_selector("top")
entries = files_dict[st.session_state.selected_file]
navigation_controls(entries, "top")

# ---- Retrieve the currently selected entry ----
if st.session_state.entry_idx >= len(entries):
    st.session_state.entry_idx = 0
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
span.diff_sub {background-color: #ff6666; color: black; font-weight: bold;}
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

# ---- Second set of file selector + controls ----
file_selector("bottom")
entries = files_dict[st.session_state.selected_file]
navigation_controls(entries, "bottom")

