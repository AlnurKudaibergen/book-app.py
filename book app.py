# bookapp.py — Apple Books AI (Wattpad-like UI + QR sharing)
import streamlit as st
import os
import uuid
import json
import io
import qrcode
from PIL import Image
import textwrap
import openai

# ------------------ CONFIG / STYLES ------------------
st.set_page_config(page_title="WattBooks AI — Apple Books AI", page_icon="📘", layout="wide")
# Wattpad-like warm orange palette + clean cards
st.markdown(
    """
    <style>
    :root{
        --bg: #fff7f0;
        --accent: #ff6a00; /* Wattpad-like orange */
        --muted: #6b6b6b;
        --card: #ffffff;
        --soft: #fff2ea;
    }
    body { background: linear-gradient(180deg,var(--bg), #fff); }
    .topbar { display:flex; align-items:center; justify-content:space-between; padding:12px 18px; background:transparent; }
    .brand { font-size:22px; font-weight:700; color:#222; display:flex; gap:10px; align-items:center;}
    .brand .logo { font-size:26px; }
    .subtitle { color:var(--muted); font-size:13px; }
    .sidebar { background:var(--card); padding:16px; border-radius:12px; box-shadow: 0 8px 20px rgba(15,23,42,0.06); }
    .card { background:var(--card); padding:12px; border-radius:12px; box-shadow: 0 6px 18px rgba(15,23,42,0.06); margin-bottom:14px; }
    .story-title { font-weight:700; font-size:18px; color:#111827; }
    .story-meta { color:var(--muted); font-size:13px; }
    .big-cta { background:var(--accent); color:white; padding:10px 14px; border-radius:10px; font-weight:700; border:none; }
    .pill { background:var(--soft); color:var(--accent); padding:6px 8px; border-radius:999px; font-weight:600; }
    .qr-box { background:#fff; padding:10px; border-radius:8px; text-align:center; }
    .muted { color:var(--muted); }
    .small { font-size:13px; color:var(--muted); }
    .cover { border-radius:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------ OPENAI SETUP ------------------
def setup_openai():
    key = None
    try:
        key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        key = os.environ.get("OPENAI_API_KEY")
    if key:
        openai.api_key = key
        return True
    return False

OPENAI_OK = setup_openai()
if not OPENAI_OK:
    st.warning("OpenAI key not found — AI features disabled. Put OPENAI_API_KEY into .streamlit/secrets.toml or env vars.")

# ------------------ SESSION INIT ------------------
if "library" not in st.session_state:
    st.session_state.library = [
        {"id": str(uuid.uuid4()), "title": "Atomic Habits", "author": "James Clear",
         "content": "Small habits compound into major results. Focus on systems, not goals.", "tags": ["self-help"], "cover": "https://covers.openlibrary.org/b/isbn/9780735211292-L.jpg"},
        {"id": str(uuid.uuid4()), "title": "The Alchemist", "author": "Paulo Coelho",
         "content": "A shepherd's journey to discover his Personal Legend across distant lands.", "tags": ["fiction","fantasy"], "cover": "https://covers.openlibrary.org/b/isbn/9780061122415-L.jpg"},
        {"id": str(uuid.uuid4()), "title": "1984", "author": "George Orwell",
         "content": "Dystopian world of surveillance and control, the perils of totalitarianism.", "tags": ["dystopia"], "cover": "https://covers.openlibrary.org/b/isbn/9780451524935-L.jpg"},
    ]

if "my_books" not in st.session_state:
    st.session_state.my_books = []

if "selected_book" not in st.session_state:
    st.session_state.selected_book = None

# ------------------ HELPERS ------------------
def ai_response(prompt, max_tokens=500, temperature=0.2):
    if not OPENAI_OK:
        return "AI not available — add OPENAI_API_KEY."
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"AI error: {e}"

def generate_qr_image(data: str, size=300):
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size, size))
    return img

def find_book(bid):
    for b in st.session_state.library:
        if b["id"] == bid:
            return b
    return None

def search_library(q):
    q = (q or "").strip().lower()
    if not q:
        return st.session_state.library
    out = []
    for b in st.session_state.library:
        if q in b["title"].lower() or q in b["author"].lower() or any(q in t.lower() for t in b.get("tags",[])):
            out.append(b)
    return out

# ------------------ LAYOUT: TOP BAR ------------------
col_t1, col_t2 = st.columns([4,1])
with col_t1:
    st.markdown('<div class="brand"><span class="logo">📚</span> <div><div style="font-weight:800">WattBooks AI</div><div class="subtitle">Read — Interact — Learn</div></div></div>', unsafe_allow_html=True)
with col_t2:
    if OPENAI_OK:
        st.markdown('<div style="text-align:right"><span class="pill">AI: Connected</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:right"><span class="pill" style="color:#ff6a00">AI: Off</span></div>', unsafe_allow_html=True)

st.markdown("")  # spacer

# ------------------ MAIN LAYOUT: left menu, center feed, right panel ------------------
left_col, center_col, right_col = st.columns([1, 2.2, 0.9])

# --- LEFT MENU ---
with left_col:
    st.markdown('<div class="sidebar">', unsafe_allow_html=True)
    st.markdown("### Menu")
    if st.button("Home"):
        st.session_state.selected_book = None
    if st.button("My Books"):
        # open a simple list view in center
        st.session_state.selected_book = "SHOW_MY_BOOKS"
    st.markdown("---")
    st.markdown("### Add / Import")
    with st.expander("➕ Add a new book"):
        nt = st.text_input("Title", key="nt_title")
        na = st.text_input("Author", key="nt_author")
        ncov = st.text_input("Cover URL (optional)", key="nt_cover")
        ntag = st.text_input("Tags (comma-separated)", key="nt_tags")
        ncontent = st.text_area("Paste excerpt or chapter (optional)", key="nt_content", height=160)
        if st.button("Add book to library"):
            newb = {"id": str(uuid.uuid4()), "title": nt or "Untitled", "author": na or "Unknown",
                    "content": ncontent or "", "tags": [t.strip() for t in (ntag or "").split(",") if t.strip()],
                    "cover": ncov or "https://via.placeholder.com/180x260.png?text=Book"}
            st.session_state.library.insert(0, newb)
            st.success(f"Added '{newb['title']}'")
            # clear inputs:
            st.session_state.nt_title = ""
            st.session_state.nt_author = ""
            st.session_state.nt_cover = ""
            st.session_state.nt_tags = ""
            st.session_state.nt_content = ""
    st.markdown("---")
    st.markdown("### Share / QR")
    share_url = st.text_input("URL or deep link to share (e.g. Telegram t.me/username):", value="")
    if st.button("Generate QR"):
        if share_url.strip():
            qr_img = generate_qr_image(share_url.strip(), size=300)
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            st.image(buf)
            st.download_button("Download QR (PNG)", data=buf.getvalue(), file_name="share_qr.png", mime="image/png")
        else:
            st.warning("Enter a URL or link to encode.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- CENTER FEED ---
with center_col:
    # search
    q = st.text_input("Search books (title, author, tag):", key="search_input")
    results = search_library(q)
    # if user clicked My Books from left menu
    if st.session_state.selected_book == "SHOW_MY_BOOKS":
        st.markdown("## 📘 My Books")
        if not st.session_state.my_books:
            st.info("Your shelf is empty — add books from the library.")
        else:
            for mb in st.session_state.my_books:
                st.markdown(f"<div class='card'><div style='display:flex;gap:12px'><img src='{mb['cover']}' width='90' class='cover'/> <div><div class='story-title'>{mb['title']}</div><div class='story-meta'>{mb['author']}</div><div style='margin-top:8px'><button onclick=\"window.open('#','_self')\" style='background:#ff6a00;color:white;border:none;padding:6px 10px;border-radius:8px' data-bookid='{mb['id']}' id='open_{mb['id']}'>Open</button></div></div></div></div>", unsafe_allow_html=True)
            # note: above buttons are descriptive; we'll also show clickable Open buttons below each item for functionality
            for mb in st.session_state.my_books:
                if st.button(f"Open: {mb['title']}", key=f"open_my_{mb['id']}"):
                    st.session_state.selected_book = mb["id"]
                    st.experimental_rerun()
        st.stop()

    # regular feed
    st.markdown("## 🔥 Trending & Library")
    # grid with 2 columns
    for i, b in enumerate(results):
        if i % 2 == 0:
            cols = st.columns(2)
        with cols[i % 2]:
            st.markdown("<div class='card' style='text-align:left'>", unsafe_allow_html=True)
            left, right = st.columns([1,3])
            with left:
                st.image(b.get("cover"), width=110)
            with right:
                st.markdown(f"<div class='story-title'>{b['title']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='story-meta'>{b['author']} · {', '.join(b.get('tags',[]))}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='margin-top:8px'><button onclick=\"window.open('#','_self')\" style='background:transparent;color:var(--accent);border:2px solid var(--accent);padding:6px 10px;border-radius:8px' id='add_{b['id']}'>Add</button> <span style='margin-left:8px'></span></div>", unsafe_allow_html=True)
                # functional Streamlit buttons:
                if st.button("Open", key=f"open_{b['id']}"):
                    st.session_state.selected_book = b["id"]
                    st.experimental_rerun()
                if st.button("Save to My Books", key=f"save_{b['id']}"):
                    if b["id"] not in [x["id"] for x in st.session_state.my_books]:
                        st.session_state.my_books.append(b)
                        st.success("Saved to My Books")
                    else:
                        st.info("Already saved")
            st.markdown("</div>", unsafe_allow_html=True)

# --- RIGHT PANEL: profile / quick AI / QR ---
with right_col:
    st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
    st.markdown("### 👤 Profile")
    st.image("https://via.placeholder.com/120x120.png?text=You", width=120)
    st.markdown("**Guest**")
    st.markdown("<div class='small'>No login — demo mode</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### ⚡ Quick AI")
    if OPENAI_OK:
        sample = st.selectbox("Quick action", ["Summarize selected book", "Extract keywords", "Generate short quiz (1q)"])
        if st.button("Run Quick AI"):
            if st.session_state.selected_book:
                sb = find_book(st.session_state.selected_book)
                if sb and sb.get("content","").strip():
                    if sample == "Summarize selected book":
                        out = ai_response(f"Summarize the text below in 5-7 concise sentences:\n\n{sb['content']}")
                        st.success("Done")
                        st.info(out)
                    elif sample == "Extract keywords":
                        out = ai_response(f"List top 8 keywords and short explanation for each from this text:\n\n{sb['content']}")
                        st.info(out)
                    else:
                        out = ai_response(f"Create 1 multiple-choice question (4 choices) from this text and mark the correct answer:\n\n{sb['content']}")
                        st.info(out)
                else:
                    st.warning("Select a book with content saved (open the book and save excerpt).")
            else:
                st.warning("Open a book first (click Open on a book).")
    else:
        st.markdown("AI disabled.")
    st.markdown("---")
    st.markdown("### 📲 Share / Connect")
    # create a Telegram deep link and QR
    tg_user = st.text_input("Telegram username (without @):", value="")
    if tg_user:
        tg_link = f"https://t.me/{tg_user}"
        qr = generate_qr_image(tg_link, size=200)
        st.image(qr)
        st.markdown(f"[Open Telegram profile]({tg_link})")
        st.download_button("Download Telegram QR", data=qr.tobytes(), file_name="telegram_qr.png", mime="image/png")
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------ BOOK WORKSPACE (full) ------------------
if st.session_state.selected_book and st.session_state.selected_book != "SHOW_MY_BOOKS":
    b = find_book(st.session_state.selected_book)
    if b:
        st.markdown("---")
        st.markdown(f"## {b['title']}  <span class='small'>by {b['author']}</span>", unsafe_allow_html=True)
        w1, w2 = st.columns([1,2])
        with w1:
            st.image(b.get("cover"), width=200)
            st.markdown(f"**Tags:** {', '.join(b.get('tags',[])) or '-'}")
            if st.button("Add/Remove My Books", key=f"toggle_{b['id']}"):
                ids = [x["id"] for x in st.session_state.my_books]
                if b["id"] in ids:
                    st.session_state.my_books = [x for x in st.session_state.my_books if x["id"] != b["id"]]
                    st.success("Removed from My Books")
                else:
                    st.session_state.my_books.append(b)
                    st.success("Added to My Books")
            # share book: create link (demo) and QR
            share_link = st.text_input("Shareable link (optional)", value=f"https://example.com/book/{b['id']}")
            if st.button("Create Book QR"):
                qr_img = generate_qr_image(share_link, size=320)
                buf = io.BytesIO(); qr_img.save(buf, format="PNG"); buf.seek(0)
                st.image(qr_img)
                st.download_button("Download Book QR", data=buf.getvalue(), file_name=f"{b['title']}_qr.png", mime="image/png")
        with w2:
            st.markdown("### Content / Excerpt")
            content = st.text_area("Edit book content (save to update):", value=b.get("content",""), height=260, key=f"content_{b['id']}")
            if st.button("Save content", key=f"save_content_{b['id']}"):
                b["content"] = content
                st.success("Saved excerpt to library entry")
            st.markdown("### AI Tools")
            ai_col1, ai_col2 = st.columns(2)
            with ai_col1:
                if st.button("Summarize this excerpt"):
                    if b.get("content","").strip():
                        out = ai_response(f"Summarize the following text in 6-8 short sentences:\n\n{b['content']}", max_tokens=350)
                        st.markdown("**Summary:**"); st.info(out)
                    else:
                        st.warning("No content — paste excerpt above and Save.")
                if st.button("Translate to Russian"):
                    if b.get("content","").strip():
                        out = ai_response(f"Translate the following text into Russian, preserving tone and readability:\n\n{b['content']}", max_tokens=500)
                        st.markdown("**Translation (RU):**"); st.write(out)
                    else:
                        st.warning("No content.")
            with ai_col2:
                if st.button("Extract keywords & themes"):
                    if b.get("content","").strip():
                        out = ai_response(f"Extract top 8 keywords and short explanation for each from the text:\n\n{b['content']}")
                        st.markdown("**Keywords & Themes:**"); st.write(out)
                    else:
                        st.warning("No content.")
                if st.button("Generate 3-question quiz"):
                    if b.get("content","").strip():
                        prompt = f"Create 3 multiple-choice questions (4 choices each) from the text below. Return output in JSON array, each element: {{'question':'...','choices':['a','b','c','d'],'answer':'correct choice text'}}.\n\nText:\n{b['content']}"
                        raw = ai_response(prompt, max_tokens=800)
                        st.markdown("**AI quiz (raw):**"); st.code(raw)
                        st.session_state[f"quiz_raw_{b['id']}"] = raw
                    else:
                        st.warning("No content.")
            # Chat with book
            st.markdown("### Chat with the book")
            chat_q = st.text_input("Ask a question about this excerpt:", key=f"chat_q_{b['id']}")
            if st.button("Ask AI", key=f"ask_{b['id']}"):
                if b.get("content","").strip():
                    prompt = f"You are an assistant answering questions based ONLY on the excerpt below. Excerpt:\n\n{b['content']}\n\nQuestion: {chat_q}\nAnswer concisely and clearly."
                    ans = ai_response(prompt, max_tokens=300)
                    hist_key = f"chat_hist_{b['id']}"
                    hist = st.session_state.get(hist_key, [])
                    hist.append({"q": chat_q, "a": ans})
                    st.session_state[hist_key] = hist
                else:
                    st.warning("No content to answer from.")
            # show chat history
            hist = st.session_state.get(f"chat_hist_{b['id']}", [])
            if hist:
                st.markdown("**Chat history:**")
                for item in reversed(hist[-6:]):
                    st.markdown(f"Q: {item['q']}")
                    st.markdown(f"A: {item['a']}")
                    st.markdown("---")

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("**Notes:** This UI is inspired by Wattpad — orange accent, story feed and profile. App retains AI features (summary/translate/quiz), per-book workspace, and QR sharing to open links on other devices or Telegram. For production: add user auth, persistent DB, and secure API key handling.")
