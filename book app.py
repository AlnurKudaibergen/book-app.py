# bookapp.py — Apple Books AI (Improved)
import streamlit as st
from openai import OpenAI
import textwrap
import uuid

# ------------------ CONFIG / STYLES ------------------
st.set_page_config(page_title="📚 Apple Books AI", page_icon="📘", layout="wide")

st.markdown(
    """
    <style>
    :root{
        --bg: #f6f8fb;
        --card: #ffffff;
        --muted: #6b7280;
        --accent: #4f46e5;
    }
    .app-header { text-align:center; padding:6px 0 2px 0; }
    .app-title { font-size:30px; margin:0; color: #111827; }
    .app-sub { color: var(--muted); margin:0 0 12px 0; }
    .card { background:var(--card); padding:12px; border-radius:12px; box-shadow: 0 6px 18px rgba(15,23,42,0.06); }
    .book-cover { border-radius:8px; }
    .muted { color: var(--muted); }
    .ai-box { background:#eef2ff; padding:12px; border-radius:8px; }
    .small { font-size:13px; color:var(--muted); }
    .pill { background:#eef2ff; color:var(--accent); padding:6px 8px; border-radius:999px; font-weight:600; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-header"><h1 class="app-title">📚 Apple Books AI</h1><div class="app-sub">Summaries · Interactive chat · Quizzes · Personal library</div></div>', unsafe_allow_html=True)

# ------------------ OPENAI CLIENT & KEY CHECK ------------------
def get_openai_client():
    # prefer st.secrets, fallback to env var OPENAI_API_KEY
    try:
        key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        import os
        key = os.environ.get("OPENAI_API_KEY", None)
    if not key:
        return None
    return OpenAI(api_key=key)

client = get_openai_client()
if client is None:
    st.warning("OpenAI API key not found. Put it in `.streamlit/secrets.toml` as `OPENAI_API_KEY = \"...\"` or set env var OPENAI_API_KEY.")
    st.info("AI features will be disabled until key is provided.")
# ------------------ SESSION INIT ------------------
if "library" not in st.session_state:
    # Pre-populate with sample books (no full text)
    st.session_state.library = [
        {"id": str(uuid.uuid4()), "title": "Atomic Habits", "author": "James Clear", "isbn": "9780735211292", "content": "", "tags": ["self-help"], "cover": "https://covers.openlibrary.org/b/isbn/9780735211292-L.jpg"},
        {"id": str(uuid.uuid4()), "title": "The Alchemist", "author": "Paulo Coelho", "isbn": "9780061122415", "content": "", "tags": ["fiction"], "cover": "https://covers.openlibrary.org/b/isbn/9780061122415-L.jpg"},
        {"id": str(uuid.uuid4()), "title": "1984", "author": "George Orwell", "isbn": "9780451524935", "content": "", "tags": ["dystopia"], "cover": "https://covers.openlibrary.org/b/isbn/9780451524935-L.jpg"},
    ]

if "my_books" not in st.session_state:
    st.session_state.my_books = []

if "ui_font_size" not in st.session_state:
    st.session_state.ui_font_size = 14

# ------------------ SIDEBAR: SETTINGS & QUICK ACTIONS ------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    fs = st.slider("UI font size", min_value=12, max_value=20, value=st.session_state.ui_font_size, step=1)
    st.session_state.ui_font_size = fs
    theme = st.selectbox("Card style", ["Light (default)", "Soft Shadow", "Minimal"])
    st.markdown("---")
    st.markdown("### 🔎 Quick search")
    q_hint = st.text_input("Search library (title / author / tag):", value="")
    st.markdown("---")
    st.markdown("### 📥 Add book (paste text)")
    if st.button("Add demo book with sample text"):
        demo_book = {
            "id": str(uuid.uuid4()),
            "title": "Sample Book — AI Demo",
            "author": "Team",
            "isbn": "",
            "content": "This is a sample text for demo. It contains ideas about habits, learning, and productivity. Use the AI Assistant to summarize or generate exercises.",
            "tags": ["demo"],
            "cover": "https://via.placeholder.com/200x300.png?text=Book"
        }
        st.session_state.library.append(demo_book)
        st.success("Demo book added to library.")
    st.markdown("### ℹ️ OpenAI")
    if client is None:
        st.caption("AI disabled — no API key")
    else:
        st.success("✅ OpenAI connected")

# small dynamic style injection for font size
st.markdown(f"<style>body {{ font-size: {st.session_state.ui_font_size}px; }}</style>", unsafe_allow_html=True)

# ------------------ HELPERS ------------------
def find_book(book_id):
    for b in st.session_state.library:
        if b["id"] == book_id:
            return b
    return None

def search_library(q):
    q = q.strip().lower()
    if not q:
        return st.session_state.library
    res = []
    for b in st.session_state.library:
        if q in b["title"].lower() or q in b["author"].lower() or any(q in t.lower() for t in b.get("tags", [])):
            res.append(b)
    return res

# Chat + AI wrappers
def ai_chat_completion(prompt, max_tokens=600):
    if client is None:
        return "AI not available (missing API key)."
    try:
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=max_tokens)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"AI error: {e}"

# ------------------ LAYOUT ------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📚 Library")
    # Search input from sidebar propagated
    query = q_hint if q_hint else st.text_input("Search library here:", value="")
    results = search_library(query)

    # Add new book form
    with st.expander("➕ Add new book (title, author, paste text)"):
        new_title = st.text_input("Title", key="new_title")
        new_author = st.text_input("Author", key="new_author")
        new_tags = st.text_input("Tags (comma separated)", key="new_tags")
        new_cover = st.text_input("Cover image URL (optional)", key="new_cover")
        new_text = st.text_area("Paste full text / excerpt (optional)", key="new_content", height=200)
        if st.button("Add to library"):
            book = {
                "id": str(uuid.uuid4()),
                "title": new_title or "Untitled",
                "author": new_author or "Unknown",
                "isbn": "",
                "content": new_text or "",
                "tags": [t.strip() for t in (new_tags or "").split(",") if t.strip()],
                "cover": new_cover or "https://via.placeholder.com/200x300.png?text=Book"
            }
            st.session_state.library.insert(0, book)
            st.success(f"Added '{book['title']}' to library.")
            # clear inputs (simple)
            st.experimental_rerun()

    # Display search results as grid
    if not results:
        st.info("No books found in the library.")
    else:
        # show cards in rows of 3
        cols = st.columns(3)
        for i, b in enumerate(results):
            c = cols[i % 3]
            with c:
                st.markdown(f"<div class='card' style='text-align:center'>", unsafe_allow_html=True)
                st.image(b.get("cover"), width=140, use_column_width=False)
                st.markdown(f"**{b['title']}**")
                st.markdown(f"<div class='small'>{b['author']}</div>", unsafe_allow_html=True)
                if st.button("Open", key=f"open_{b['id']}"):
                    st.session_state.selected_book = b["id"]
                    st.experimental_rerun()
                if st.button("Add to My Books", key=f"save_{b['id']}"):
                    # ensure no duplicates by id
                    if b["id"] not in [x["id"] for x in st.session_state.my_books]:
                        st.session_state.my_books.append(b)
                        st.success("Saved to My Books.")
                    else:
                        st.info("Already in My Books.")
                st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("### 📘 My Books")
    if not st.session_state.my_books:
        st.info("Your shelf is empty — add books from library.")
    else:
        for mb in st.session_state.my_books:
            st.markdown(f"- **{mb['title']}** — {mb['author']}")
            rowcol = st.columns([1,3])
            if rowcol[0].button("Open", key=f"open_my_{mb['id']}"):
                st.session_state.selected_book = mb["id"]
                st.experimental_rerun()
            if rowcol[0].button("Remove", key=f"remove_my_{mb['id']}"):
                st.session_state.my_books = [x for x in st.session_state.my_books if x["id"] != mb["id"]]
                st.success("Removed from My Books.")
    st.markdown("---")
    st.markdown("### 🛠️ Tools")
    if client:
        st.markdown("- ✅ AI available")
    else:
        st.markdown("- ⚠️ AI unavailable (set OpenAI key)")
    st.caption("Tip: use the library search to find a book and click Open to go to its workspace.")

# ------------------ BOOK WORKSPACE ------------------
book_id = st.session_state.get("selected_book", None)

if book_id:
    book = find_book(book_id)
    if book is None:
        st.error("Selected book not found in library.")
    else:
        st.markdown("---")
        st.markdown(f"## {book['title']}  <span class='small'>by {book['author']}</span>", unsafe_allow_html=True)
        bcol1, bcol2 = st.columns([1,2])
        with bcol1:
            st.image(book.get("cover"), width=180)
            st.markdown(f"**Tags:** {', '.join(book.get('tags',[])) or '-'}")
            if st.button("Add/Remove My Books", key=f"toggle_my_{book['id']}"):
                ids = [x["id"] for x in st.session_state.my_books]
                if book["id"] in ids:
                    st.session_state.my_books = [x for x in st.session_state.my_books if x["id"] != book["id"]]
                    st.success("Removed from My Books.")
                else:
                    st.session_state.my_books.append(book)
                    st.success("Added to My Books.")
            if st.button("Back to Library"):
                st.session_state.selected_book = None
                st.experimental_rerun()

        with bcol2:
            st.markdown("### Content / Excerpt")
            content = st.text_area("Book content (editable). Paste excerpt or full chapter here:", value=book.get("content",""), height=240, key=f"content_{book['id']}")
            if st.button("Save content", key=f"save_content_{book['id']}"):
                book["content"] = content
                st.success("Content saved to library entry.")

        # AI assistant and quiz area
        st.markdown("### 🤖 AI Assistant — work with this book")
        as_col1, as_col2 = st.columns([1,1])
        with as_col1:
            if not client:
                st.warning("AI not available. Add OpenAI key to use summary/translate/analyze/quiz generation.")
            else:
                # quick actions
                if st.button("Generate concise summary", key=f"gen_sum_{book['id']}"):
                    prompt = f"Read the following text and provide a concise, clear summary (~5-8 sentences). Text:\n\n{book.get('content','')}"
                    out = ai_chat_completion(prompt)
                    st.session_state[f"summary_{book['id']}"] = out
                if st.button("Extract keywords & themes", key=f"keys_{book['id']}"):
                    prompt = f"Extract the top 8 keywords and main themes from the text below as a comma-separated list and then one-line explanation for each:\n\n{book.get('content','')}"
                    out = ai_chat_completion(prompt)
                    st.session_state[f"keywords_{book['id']}"] = out
                if st.button("Translate excerpt", key=f"trans_{book['id']}"):
                    lang = st.selectbox("Translate to:", ["Russian","Kazakh","French","German","Spanish"], key=f"lang_{book['id']}")
                    prompt = f"Translate the following text into {lang} preserving meaning and readability:\n\n{book.get('content','')}"
                    out = ai_chat_completion(prompt)
                    st.session_state[f"translate_{book['id']}"] = out

        with as_col2:
            # Chat with the book — freeform
            st.markdown("Chat with the book (ask questions about content):")
            chat_q = st.text_input("Ask a question about this book excerpt:", key=f"chat_q_{book['id']}")
            if st.button("Send to AI", key=f"chat_send_{book['id']}"):
                prompt = f"You are an assistant that answers questions based on the provided book excerpt. Excerpt:\n\n{book.get('content','')}\n\nQuestion: {chat_q}\nAnswer concisely and cite lines if useful."
                out = ai_chat_completion(prompt)
                # maintain simple chat history
                hist_key = f"chat_hist_{book['id']}"
                hist = st.session_state.get(hist_key, [])
                hist.append({"q": chat_q, "a": out})
                st.session_state[hist_key] = hist

        # show AI outputs
        if st.session_state.get(f"summary_{book['id']}", None):
            st.markdown("**Summary (AI):**")
            st.info(st.session_state[f"summary_{book['id']}"])

        if st.session_state.get(f"keywords_{book['id']}", None):
            st.markdown("**Keywords & Themes (AI):**")
            st.write(st.session_state[f"keywords_{book['id']}"])

        if st.session_state.get(f"translate_{book['id']}", None):
            st.markdown("**Translation (AI):**")
            st.write(st.session_state[f"translate_{book['id']}"])

        # chat history
        hist_key = f"chat_hist_{book['id']}"
        hist = st.session_state.get(hist_key, [])
        if hist:
            st.markdown("**Chat History:**")
            for item in reversed(hist[-6:]):
                st.markdown(f"**Q:** {item['q']}")
                st.markdown(f"**A:** {item['a']}")
                st.markdown("---")

        # ------------------ QUIZ GENERATION & PLAY ------------------
        st.markdown("### 🎮 Generate Quiz (MCQ) from this book")
        with st.expander("Create & Customize Quiz"):
            num_q = st.slider("Number of questions", min_value=1, max_value=8, value=3, key=f"numq_{book['id']}")
            difficulty = st.selectbox("Difficulty (guideline)", ["Easy", "Medium", "Hard"], key=f"diff_{book['id']}")
            if st.button("Generate Quiz", key=f"genquiz_{book['id']}"):
                # craft prompt to generate MCQs with choices and correct answer
                prompt = f"Create {num_q} multiple-choice questions (4 choices each) based on the following text. Provide output in JSON array form where each element has 'question','choices' (list of 4) and 'answer' (text of correct choice). Difficulty: {difficulty}.\n\nText:\n{book.get('content','')}"
                out = ai_chat_completion(prompt, max_tokens=900)
                # naive attempt to parse JSON-like output; we will just store plain text if parsing fails
                st.session_state[f"quiz_raw_{book['id']}"] = out
                st.success("Quiz generated and saved in session (check below).")

        # show generated quiz and allow playing
        raw = st.session_state.get(f"quiz_raw_{book['id']}", None)
        if raw:
            st.markdown("**Generated quiz (raw AI output)**")
            st.code(raw, language=None)
            st.markdown("You can now play the quiz (simple mode):")
            if st.button("Start Quiz", key=f"start_quiz_{book['id']}"):
                # attempt to parse simple numbered Q format; fallback: build single question
                # For robustness, ask AI to reformat into simple plain text with markers if previous parse is messy
                re_prompt = f"Reformat the following quiz into a simple numbered list. For each question provide: Q:..., A:[choice text], Choices:[choice1|choice2|choice3|choice4]. Keep exact formatting and separate questions with '###'.\n\n{raw}"
                neat = ai_chat_completion(re_prompt, max_tokens=900)
                st.session_state[f"quiz_play_{book['id']}"] = neat
                st.session_state[f"quiz_answers_{book['id']}"] = {}
                st.experimental_rerun()

        # play quiz if prepared
        playing = st.session_state.get(f"quiz_play_{book['id']}", None)
        if playing:
            st.markdown("**Quiz (Play mode)**")
            # naive parsing: split by "###" blocks or by double newlines
            blocks = [b.strip() for b in playing.split("###") if b.strip()]
            user_answers = st.session_state.get(f"quiz_answers_{book['id']}", {})
            for qi, block in enumerate(blocks):
                # try extract question, choices, answer
                lines = [l.strip() for l in block.splitlines() if l.strip()]
                q_text = lines[0].lstrip("Q:").strip() if lines else f"Question {qi+1}"
                # find Choices:
                choices_line = next((l for l in lines if l.lower().startswith("choices")), None)
                # attempt splitting
                choices = []
                if choices_line:
                    # choices: [a|b|c|d] or Choices: a | b | c | d
                    rawc = choices_line.split(":",1)[1].strip()
                    if "|" in rawc:
                        choices = [c.strip() for c in rawc.split("|") if c.strip()]
                    else:
                        choices = [c.strip() for c in rawc.split(",") if c.strip()]
                if not choices:
                    # fallback: take subsequent lines as choices
                    for l in lines[1:]:
                        if l and len(choices) < 4:
                            # remove leading letters "A)" or "1."
                            ch = l
                            if ch[0].isalpha() and ch[1] in ").":
                                ch = ch[2:].strip()
                            choices.append(ch)
                if not choices:
                    choices = ["Option 1","Option 2","Option 3","Option 4"]
                # render
                st.markdown(f"**{qi+1}. {q_text}**")
                # radio
                ans_key = f"quiz_sel_{book['id']}_{qi}"
                choice = st.radio("", options=choices, index=0, key=ans_key)
                user_answers[qi] = choice
                st.session_state[f"quiz_answers_{book['id']}"] = user_answers
            if st.button("Submit Quiz", key=f"submit_quiz_{book['id']}"):
                # try to extract correct answers from 'playing' (look for 'A:' or 'Answer:')
                score = 0
                total = len(blocks)
                correct_map = {}
                for qi, block in enumerate(blocks):
                    # try find 'A:[' or 'Answer:' lines
                    ans_line = None
                    for l in block.splitlines():
                        if l.lower().startswith("a:") or l.lower().startswith("answer:"):
                            ans_line = l.split(":",1)[1].strip()
                            break
                    if ans_line:
                        # match to one of choices
                        chosen = user_answers.get(qi, "")
                        if ans_line and chosen and ans_line.lower() in chosen.lower():
                            score += 1
                    else:
                        # can't determine, skip
                        pass
                st.success(f"Quiz finished — score: {score}/{total} (auto-check best-effort).")

# ------------------ FOOTER / REFERENCES ------------------
st.markdown("---")
st.markdown("**Notes:** This is an MVP-style app for demos. For production, store books in a database, handle user auth, and add robust parsing/validation of AI quiz JSON.")
st.markdown("**References:** Ries (2011) — MVP approach; Nielsen & Molich (1990) — usability heuristics.")
