import streamlit as st
import pickle
import requests
import difflib
import re

# =============== CONFIG ===============
st.set_page_config(page_title="🎬 Movie Recommender", page_icon="🎬", layout="wide")

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500/"
TMDB_FALLBACK = "https://via.placeholder.com/500x750.png?text=No+Poster"

# =============== LOAD DATA ===============
@st.cache_resource
def load_artifacts():
    movies = pickle.load(open("movie_list.pkl", "rb"))
    similarity = pickle.load(open("similarity.pkl", "rb"))
    return movies, similarity

movies, similarity = load_artifacts()
if len(movies) != len(similarity):
    st.warning("⚠️ Movies and similarity shapes differ. Recommendations may be limited.")

# =============== HELPERS ===============
def fetch_poster(movie_id: int) -> str:
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US"
        data = requests.get(url, timeout=10).json()
        path = data.get("poster_path")
        return TMDB_IMAGE_BASE + path if path else TMDB_FALLBACK
    except Exception:
        return TMDB_FALLBACK

def normalize(s: str) -> str:
    return (s or "").strip().lower()

def tokenize(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", normalize(text)))

GENRE_SYNONYMS = {
    "Action": ["action"],
    "Adventure": ["adventure"],
    "Animation": ["animation", "animated"],
    "Comedy": ["comedy", "comedies"],
    "Crime": ["crime"],
    "Drama": ["drama", "dramatic"],
    "Family": ["family"],
    "Fantasy": ["fantasy"],
    "History": ["history", "historical"],
    "Horror": ["horror"],
    "Music": ["music", "musical"],
    "Mystery": ["mystery"],
    "Romance": ["romance", "romantic"],
    "Sci-Fi": ["sci", "scifi", "sci-fi", "science", "sciencefiction", "science_fiction"],
    "Thriller": ["thriller", "suspense"],
    "War": ["war"],
    "Western": ["western"],
}

PILL_GENRES = list(GENRE_SYNONYMS.keys())

def matches_any_selected_genre(tags_text: str, selected_genres: list[str]) -> bool:
    if not selected_genres:
        return True
    tags_text = normalize(tags_text).replace(",", " ")
    tokens = tokenize(tags_text)
    for g in selected_genres:
        for syn in GENRE_SYNONYMS.get(g, []):
            if syn in tokens or syn in tags_text:
                return True
    return False

def find_best_title_index(query: str):
    q = normalize(query)
    titles = movies["title"].astype(str).tolist()
    norm_titles = [t.lower() for t in titles]
    if q in norm_titles:
        return norm_titles.index(q), titles[norm_titles.index(q)]
    best = difflib.get_close_matches(q, norm_titles, n=1, cutoff=0.6)
    if best:
        idx = norm_titles.index(best[0])
        return idx, titles[idx]
    return None, None

def recommend(query_title: str, selected_genres: list[str]) -> tuple[list[str], list[str], list[str]]:
    rec_names, rec_posters, rec_genres = [], [], []

    if query_title.strip():
        idx, matched_title = find_best_title_index(query_title)
        if idx is None:
            return [], [], []

        distances = list(enumerate(similarity[idx]))
        distances.sort(key=lambda x: x[1], reverse=True)

        for j, _score in distances[1:400]:
            row = movies.iloc[j]
            tags_text = str(row.get("tags", ""))
            if not matches_any_selected_genre(tags_text, selected_genres):
                continue
            rec_names.append(str(row.title))
            rec_posters.append(fetch_poster(int(row.movie_id)))
            rec_genres.append(tags_text)
            if len(rec_names) == 20:
                break
    else:
        for j, row in movies.iterrows():
            tags_text = str(row.get("tags", ""))
            if not matches_any_selected_genre(tags_text, selected_genres):
                continue
            rec_names.append(str(row.title))
            rec_posters.append(fetch_poster(int(row.movie_id)))
            rec_genres.append(tags_text)
            if len(rec_names) == 20:
                break

    return rec_names, rec_posters, rec_genres

# =============== STYLES ===============
st.markdown("""
<style>
body, 
[data-testid="stAppViewContainer"], 
[data-testid="stAppViewContainer"] > .main, 
[data-testid="stBlock"] > .block-container {
    background-color: #1E1E2F !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] {
    background-color: #1E1E2F !important;
}
.chat-title {
    font-size: 38px;
    font-weight: 900;
    font-family: 'Impact', 'Arial Black', sans-serif;
    color: #E50914;
    margin-bottom: 1rem;
    text-align: center;
}
.user-msg {
    background-color: #2F80ED;
    color: #fff;
    padding: 10px 14px;
    border-radius: 14px;
    margin: 10px 0;
    max-width: 70%;
    float: right;
    clear: both;
    font-size: 15px;
    font-weight: 500;
}
.bot-msg {
    background-color: #333447;
    color: #fff;
    padding: 10px 14px;
    border-radius: 14px;
    margin: 10px 0;
    max-width: 80%;
    float: left;
    clear: both;
    font-size: 15px;
    font-weight: 500;
}
.pill-wrap {
    display:flex;
    flex-wrap:wrap;
    gap:8px;
    margin: 6px 0 12px 0;
}
.pill, .pill-selected {
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid #565869;
    background: #444654;
    cursor: pointer;
    font-size: 14px;
    color: #fff;
}
.pill-selected {
    background:#2F80ED;
    border-color:#2F80ED;
}
.poster-wrapper {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    transition: transform 0.3s, box-shadow 0.3s;
}
.poster-wrapper:hover {
    transform: scale(1.05);
    box-shadow: 0 8px 20px rgba(0,0,0,0.5);
}
.poster-overlay {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(0,0,0,0.7);
    color: #fff;
    font-size: 12px;
    padding: 4px 6px;
    text-align: center;
    opacity: 0;
    transition: opacity 0.3s;
}
.poster-wrapper:hover .poster-overlay {
    opacity: 1;
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='chat-title'>NETFLIX</div>", unsafe_allow_html=True)

# =============== UI STATE ===============
if "selected_genres" not in st.session_state:
    st.session_state.selected_genres = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# =============== INPUTS ===============
query = st.text_input("Type a movie name", placeholder="e.g., Avatar, Inception, Batman ...")

st.subheader("Select Genre(s) 🎭")
pill_cols = st.columns(6)
for i, g in enumerate(PILL_GENRES):
    selected = g in st.session_state.selected_genres
    label = f"✓ {g}" if selected else g
    if pill_cols[i % 6].button(label, key=f"pill_{g}"):
        if selected:
            st.session_state.selected_genres.remove(g)
        else:
            st.session_state.selected_genres.append(g)

cols_top = st.columns([1,1,6])
with cols_top[0]:
    if st.button("Clear Genres"):
        st.session_state.selected_genres = []
with cols_top[1]:
    if st.button("Clear Chat"):
        st.session_state.messages = []

# =============== ACTION ===============
if st.button("Get Recommendations"):
    if not query.strip() and not st.session_state.selected_genres:
        st.warning("Please type a movie name or select a genre first.")
    else:
        st.session_state.messages = [{"role":"user","text":query or "Genre-based recommendations"}]
        with st.spinner("Finding great movies for you..."):
            names, posters, genres_list = recommend(query, st.session_state.selected_genres)
        if not names:
            st.warning("No recommendations found for the selected criteria.")
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "text": "",
                "names": names,
                "posters": posters,
                "genres": genres_list
            })

# =============== RENDER CHAT ===============
for m in st.session_state.messages:
    if m["role"] == "user":
        st.markdown(f"<div class='user-msg'>{m['text']}</div>", unsafe_allow_html=True)
    else:
        if m.get("names"):
            per_row = 5
            for start in range(0, len(m["names"]), per_row):
                row_cols = st.columns(per_row)
                for i, col in enumerate(row_cols):
                    k = start + i
                    if k < len(m["names"]):
                        name = m["names"][k]
                        poster = m["posters"][k]
                        genres_text = m["genres"][k]
                        with col:
                            st.markdown(f"""
                            <div class='poster-wrapper'>
                                <img src="{poster}" style='width:100%; border-radius:8px;'/>
                                <div class='poster-overlay'>{genres_text}</div>
                            </div>
                            <div style='text-align:center; color:#fff; font-size:16px; font-weight:700'>{name}</div>
                            """, unsafe_allow_html=True)
