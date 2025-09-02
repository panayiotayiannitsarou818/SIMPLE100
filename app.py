import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import re, ast, unicodedata

# ---------------------------
# 🔄 Restart helpers
# ---------------------------
def _restart_app():
    """Clear caches & widget states (including file_uploader) and rerun."""
    st.session_state["uploader_key"] = st.session_state.get("uploader_key", 0) + 1
    for k in list(st.session_state.keys()):
        if str(k).startswith("uploader_"):
            del st.session_state[k]
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        st.cache_resource.clear()
    except Exception:
        pass
    st.rerun()

st.set_page_config(page_title="📊 Στατιστικά & 🧩 Σπασμένες Φιλίες", page_icon="🧩", layout="wide")
st.title("📊 Στατιστικά")

# Ensure a stable uploader-key in session
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

# ---------------------------
# Sidebar: Legal / Terms + Restart
# ---------------------------
with st.sidebar:
    if st.button("🔄 Επανεκκίνηση εφαρμογής", help="Καθαρίζει μνήμη/φορτώσεις και ξεκινά από την αρχή"):
        _restart_app()
    st.markdown("### ⚖️ Όροι χρήσης")
    terms_ok = st.checkbox("Αποδέχομαι τους όρους χρήσης", value=True)
    st.markdown("© 2025 • Πνευματικά δικαιώματα • **Παναγιώτα Γιαννίτσαρου**")

with st.sidebar.expander("Κάτοχος/Δημιουργός & Άδεια", expanded=False):
    st.markdown("""
**Κάτοχος/Δημιουργός:** Παναγιώτα Γιαννίτσαρου  
**Προϊόν:** Στατιστικά/Κατανομή Μαθητών Α΄ Δημοτικού  

- Η εφαρμογή προορίζεται αποκλειστικά για **εκπαιδευτική χρήση** από σχολικές μονάδες/εκπαιδευτικούς.  
- **Πνευματικά δικαιώματα:** © 2025 Παναγιώτα Γιαννίτσαρου. **Απαγορεύεται** αντιγραφή, αναδημοσίευση ή τροποποίηση χωρίς **έγγραφη άδεια**.  
- **Μη εμπορική χρήση** επιτρέπεται σε σχολεία για εσωτερική οργάνωση.  
- Παρέχεται “**ως έχει**” χωρίς εγγυήσεις. Τα αποτελέσματα έχουν **βοηθητικό** χαρακτήρα και **δεν υποκαθιστούν** κανονιστικές αποφάσεις ή παιδαγωγική κρίση.  
- **Επικοινωνία:** panayiotayiannitsarou@gmail.com
""")

with st.sidebar.expander("🔒 Προστασία Δεδομένων (GDPR – Κύπρος)", expanded=False):
    st.markdown("""
- Τα αρχεία Excel ανεβαίνουν από τον χρήστη και χρησιμοποιούνται **μόνο** για άμεσο υπολογισμό. Η εφαρμογή δεν αποθηκεύει μόνιμα δεδομένα.  
- Ο χρήστης/σχολείο ευθύνεται για συμμόρφωση με **GDPR**.  
- **Συστάσεις:** ψευδώνυμα/κωδικοί, ελαχιστοποίηση δεδομένων, περίοδος διατήρησης, ενημέρωση DPO, έλεγχος παρόχου cloud.
""")

if not terms_ok:
    st.warning("⚠️ Για να χρησιμοποιήσεις την εφαρμογή, αποδέξου τους όρους χρήσης (αριστερά).")
    st.stop()

with st.expander("📜 Πλήρεις Όροι Χρήσης & Αποποίηση Ευθύνης", expanded=False):
    st.markdown("""
1) **Σκοπός:** Υποστήριξη εσωτερικού προγραμματισμού/στατιστικών τάξεων Α΄ Δημοτικού.  
2) **Δεδομένα:** Δεν αποθηκεύονται μόνιμα από την εφαρμογή. Ο χρήστης παραμένει υπεύθυνος για **GDPR**.  
3) **Περιορισμοί:** Απαγορεύεται εμπορική εκμετάλλευση/αναδιανομή/τροποποίηση χωρίς άδεια.  
4) **Αποποίηση:** Δεν υπάρχει ευθύνη για αποφάσεις που λαμβάνονται αποκλειστικά με βάση τα αποτελέσματα.  
5) **Τροποποιήσεις:** Η εφαρμογή μπορεί να ενημερώνεται χωρίς προειδοποίηση.
""")

# ---------------------------
# Canonicalization / Renaming
# ---------------------------
def _canon(s: str) -> str:
    return "".join((s or "").replace("_"," ").split()).upper()

CANON_TARGETS = {
    "ΟΝΟΜΑ": {"ΟΝΟΜΑ"},
    "ΦΥΛΟ": {"ΦΥΛΟ"},
    "ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ": {"ΠΑΙΔΙΕΚΠΑΙΔΕΥΤΙΚΟΥ", "ΠΑΙΔΙ-ΕΚΠΑΙΔΕΥΤΙΚΟΥ"},
    "ΖΩΗΡΟΣ": {"ΖΩΗΡΟΣ"},
    "ΙΔΙΑΙΤΕΡΟΤΗΤΑ": {"ΙΔΙΑΙΤΕΡΟΤΗΤΑ"},
    "ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ": {"ΚΑΛΗΓΝΩΣΗΕΛΛΗΝΙΚΩΝ", "ΓΝΩΣΗΕΛΛΗΝΙΚΩΝ"},
    "ΦΙΛΟΙ": {"ΦΙΛΟΙ", "ΦΙΛΙΑ", "ΦΙΛΟΣ"},
    "ΣΥΓΚΡΟΥΣΗ": {"ΣΥΓΚΡΟΥΣΗ", "ΣΥΓΚΡΟΥΣΕΙΣ"},
    "ΤΜΗΜΑ": {"ΤΜΗΜΑ"},
}
REQUIRED_COLS = ["ΟΝΟΜΑ","ΦΥΛΟ","ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ","ΖΩΗΡΟΣ","ΙΔΙΑΙΤΕΡΟΤΗΤΑ","ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ","ΦΙΛΟΙ","ΣΥΓΚΡΟΥΣΗ","ΤΜΗΜΑ"]

def auto_rename_columns(df: pd.DataFrame):
    """Map κοινές ελληνικές στήλες σε κανονική μορφή. Αν δεν βρεθούν, δημιουργούνται/συνενώνονται όπου χρειάζεται."""
    mapping, seen = {}, set()
    for col in df.columns:
        c = _canon(col)
        for target, keys in CANON_TARGETS.items():
            if c in keys and target not in seen:
                mapping[col] = target
                seen.add(target)
                break
    renamed = df.rename(columns=mapping)

    # ΦΙΛΟΙ fallback
    friends_cols = [c for c in renamed.columns if c in ("ΦΙΛΟΙ","ΦΙΛΙΑ","ΦΙΛΟΣ")]
    if not friends_cols:
        candidates = []
        for col in df.columns:
            c = _canon(col)
            if "ΦΙΛ" in c or "FRIEND" in c:
                candidates.append(col)
        if candidates:
            combined = []
            for _, row in df[candidates].astype(str).iterrows():
                vals = [str(v).strip() for v in row.tolist() if str(v).strip() and str(v).strip().upper() not in ("-","NA","NAN")]
                combined.append(", ".join(vals))
            renamed["ΦΙΛΟΙ"] = combined

    # ΤΜΗΜΑ fallback
    if "ΤΜΗΜΑ" not in renamed.columns:
        best = None
        for col in df.columns[::-1]:
            s = df[col].dropna().astype(str).str.strip()
            if not len(s):
                continue
            if s.str.len().median() <= 4 and s.nunique() <= 10:
                best = col
                break
        if best:
            renamed = renamed.rename(columns={best:"ΤΜΗΜΑ"})

    # ΣΥΓΚΡΟΥΣΗ fallback
    if "ΣΥΓΚΡΟΥΣΗ" not in renamed.columns:
        if "ΣΥΓΚΡΟΥΣΕΙΣ" in renamed.columns:
            renamed = renamed.rename(columns={"ΣΥΓΚΡΟΥΣΕΙΣ": "ΣΥΓΚΡΟΥΣΗ"})
        else:
            renamed["ΣΥΓΚΡΟΥΣΗ"] = ""
    return renamed, mapping

# ---------------------------
# Name canonicalization helpers
# ---------------------------

def _strip_diacritics(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def _canon_name(s: str) -> str:
    s = (str(s) if s is not None else "").strip()
    s = s.strip("[]'\" ")
    s = re.sub(r"\s+", " ", s)
    s = _strip_diacritics(s).upper()
    return s

_SPLIT_RE = re.compile(r"\s*(?:,|;|/|\||\band\b|\bκαι\b|\+|\n)\s*", flags=re.IGNORECASE)

# ---------------------------
# Friends parsing & broken pairs
# ---------------------------

def _parse_friends(cell):
    raw = str(cell) if cell is not None else ""
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        try:
            val = ast.literal_eval(raw)
            if isinstance(val, (list, tuple)):
                return [_canon_name(x) for x in val if str(x).strip()]
        except Exception:
            pass
        raw2 = raw.strip("[]")
        parts = re.split(r"[;,]", raw2)
        return [_canon_name(p) for p in parts if _canon_name(p)]
    parts = [p for p in _SPLIT_RE.split(raw) if p]
    return [_canon_name(p) for p in parts if _canon_name(p)]


def list_broken_mutual_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Επιστρέφει DataFrame με κάθε **σπασμένη πλήρως αμοιβαία δυάδα** (A/B + τμήματα)."""
    fcol = None
    for candidate in ["ΦΙΛΟΙ","ΦΙΛΙΑ","ΦΙΛΟΣ"]:
        if candidate in df.columns:
            fcol = candidate
            break
    if fcol is None or "ΟΝΟΜΑ" not in df.columns or "ΤΜΗΜΑ" not in df.columns:
        return pd.DataFrame(columns=["A","A_ΤΜΗΜΑ","B","B_ΤΜΗΜΑ"])

    df = df.copy()
    df["__CAN_NAME__"] = df["ΟΝΟΜΑ"].map(_canon_name)
    name_to_original = dict(zip(df["__CAN_NAME__"], df["ΟΝΟΜΑ"].astype(str)))
    class_by_name = dict(zip(df["__CAN_NAME__"], df["ΤΜΗΜΑ"].astype(str).str.strip()))

    token_index = {}
    for full in df["__CAN_NAME__"]:
        tokens = [t for t in re.split(r"\s+", full) if t]
        for t in tokens:
            token_index.setdefault(t, set()).add(full)

    def resolve_friend(s: str):
        s = _canon_name(s)
        if not s:
            return None
        if s in name_to_original:
            return s
        toks = [t for t in re.split(r"\s+", s) if t]
        if not toks:
            return None
        if len(toks) >= 2:
            sets = [token_index.get(t, set()) for t in toks]
            inter = set.intersection(*sets) if sets else set()
            if len(inter) == 1:
                return next(iter(inter))
            union = set().union(*sets)
            if len(union) == 1:
                return next(iter(union))
            return None
        else:
            group = token_index.get(toks[0], set())
            return next(iter(group)) if len(group) == 1 else None

    friends_by_name = {}
    for _, row in df.iterrows():
        me = row["__CAN_NAME__"]
        flist_raw = _parse_friends(row[fcol])
        resolved = set()
        for fr in flist_raw:
            r = resolve_friend(fr)
            if r and r != me:
                resolved.add(r)
        friends_by_name[me] = resolved

    mutual_pairs = set()
    for a, flist in friends_by_name.items():
        for b in flist:
            if b in friends_by_name and a in friends_by_name[b]:
                mutual_pairs.add(tuple(sorted([a,b])))

    rows = []
    for a, b in sorted(mutual_pairs):
        ta = class_by_name.get(a, "")
        tb = class_by_name.get(b, "")
        if ta and tb and ta != tb:
            rows.append({
                "A": name_to_original.get(a, a), "A_ΤΜΗΜΑ": ta,
                "B": name_to_original.get(b, b), "B_ΤΜΗΜΑ": tb,
            })
    return pd.DataFrame(rows)

# ---------------------------
# Broken friendships per student (counts + names)
# ---------------------------

def compute_broken_friend_names_per_student(df: pd.DataFrame):
    """Return (counts_series, names_series) per student for σπασμένες πλήρως αμοιβαίες δυάδες."""
    if not {"ΟΝΟΜΑ", "ΤΜΗΜΑ"}.issubset(df.columns):
        return pd.Series([0]*len(df), index=df.index), pd.Series([""]*len(df), index=df.index)

    df_local = df.copy()
    df_local["__CAN_NAME__"] = df_local["ΟΝΟΜΑ"].map(_canon_name)
    canon_to_display = dict(zip(df_local["__CAN_NAME__"], df_local["ΟΝΟΜΑ"].astype(str)))

    broken_df = list_broken_mutual_pairs(df_local)
    broken_map = {cn: [] for cn in df_local["__CAN_NAME__"]}

    for _, row in broken_df.iterrows():
        a = _canon_name(row.get("A", "")) if "A" in row else ""
        b = _canon_name(row.get("B", "")) if "B" in row else ""
        if a and b:
            broken_map.setdefault(a, []).append(canon_to_display.get(b, row.get("B", "")))
            broken_map.setdefault(b, []).append(canon_to_display.get(a, row.get("A", "")))

    counts, names = [], []
    for cn in df_local["__CAN_NAME__"]:
        lst = broken_map.get(cn, []) or []
        counts.append(len(lst))
        names.append(", ".join(lst))
    return pd.Series(counts, index=df.index), pd.Series(names, index=df.index)

# ---------------------------
# Conflicts per student (NO pairs)
# ---------------------------

def _parse_conflict_targets(cell):
    raw = str(cell) if cell is not None else ""
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        try:
            val = ast.literal_eval(raw)
            if isinstance(val, (list, tuple)):
                return [_canon_name(x) for x in val if str(x).strip()]
        except Exception:
            pass
        raw2 = raw.strip("[]")
        parts = re.split(r"[;,]", raw2)
        return [_canon_name(p) for p in parts if _canon_name(p)]
    parts = [p for p in _SPLIT_RE.split(raw) if p]
    return [_canon_name(p) for p in parts if _canon_name(p)]


def _build_name_resolution(df: pd.DataFrame):
    df = df.copy()
    df["__CAN_NAME__"] = df["ΟΝΟΜΑ"].map(_canon_name)
    name_to_original = dict(zip(df["__CAN_NAME__"], df["ΟΝΟΜΑ"].astype(str)))
    class_by_name = dict(zip(df["__CAN_NAME__"], df["ΤΜΗΜΑ"].astype(str).str.strip()))
    token_index = {}
    for full in df["__CAN_NAME__"]:
        tokens = [t for t in re.split(r"\s+", full) if t]
        for t in tokens:
            token_index.setdefault(t, set()).add(full)
    def resolve_name(s: str):
        s = _canon_name(s)
        if not s:
            return None
        if s in name_to_original:
            return s
        toks = [t for t in re.split(r"\s+", s) if t]
        if not toks:
            return None
        if len(toks) >= 2:
            sets = [token_index.get(t, set()) for t in toks]
            inter = set.intersection(*sets) if sets else set()
            if len(inter) == 1:
                return next(iter(inter))
            union = set().union(*sets)
            if len(union) == 1:
                return next(iter(union))
            return None
        else:
            group = token_index.get(toks[0], set())
            return next(iter(group)) if len(group) == 1 else None
    return name_to_original, class_by_name, resolve_name


def compute_conflict_counts_and_names(df: pd.DataFrame):
    """
    Return (counts_series, names_series) per student.
    - counts_series: πόσοι από τους δηλωμένους βρίσκονται στην **ίδια τάξη** (μονόπλευρη δήλωση αρκεί).
    - names_series: ονόματα αυτών των μαθητών (comma-separated).
    """
    required = {"ΟΝΟΜΑ", "ΤΜΗΜΑ", "ΣΥΓΚΡΟΥΣΗ"}
    if not required.issubset(set(df.columns)):
        return pd.Series([0]*len(df), index=df.index), pd.Series([""]*len(df), index=df.index)

    name_to_original, class_by_name, resolve_name = _build_name_resolution(df)

    canon_names = df["ΟΝΟΜΑ"].map(_canon_name)
    counts = [0]*len(df)
    names = [""]*len(df)

    index_by_canon = {cn: i for i, cn in enumerate(canon_names)}

    for i, row in df.iterrows():
        me = _canon_name(row["ΟΝΟΜΑ"])
        my_class = class_by_name.get(me, "")
        targets = _parse_conflict_targets(row["ΣΥΓΚΡΟΥΣΗ"])
        same_class_names = []
        for t in targets:
            r = resolve_name(t)
            if r and r != me:
                if class_by_name.get(r, None) == my_class and my_class:
                    same_class_names.append(name_to_original.get(r, r))
        counts[index_by_canon.get(me, i)] = len(same_class_names)
        names[index_by_canon.get(me, i)] = ", ".join(same_class_names)

    return pd.Series(counts, index=df.index), pd.Series(names, index=df.index)

# ---------------------------
# Stats generator
# ---------------------------

def generate_stats(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ΤΜΗΜΑ" in df:
        df["ΤΜΗΜΑ"] = df["ΤΜΗΜΑ"].apply(lambda v: v.strip() if isinstance(v, str) else v)
    if "ΦΥΛΟ" in df:
        df["ΦΥΛΟ"] = df["ΦΥΛΟ"].fillna("").astype(str).str.strip().str.upper()
    for col in ["ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ","ΖΩΗΡΟΣ","ΙΔΙΑΙΤΕΡΟΤΗΤΑ","ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ"]:
        if col in df:
            s = df[col]
            if s.dtype == object:
                s = s.fillna("").astype(str).str.strip().str.upper().replace({
                    "ΝΑΙ":"Ν","NAI":"Ν","YES":"Ν","Y":"Ν",
                    "ΟΧΙ":"Ο","OXI":"Ο","NO":"Ο","N":"Ο","": "Ο"
                })
                df[col] = s.where(s.isin(["Ν","Ο"]), other="Ο")

    boys = df[df.get("ΦΥΛΟ", "").eq("Α")].groupby("ΤΜΗΜΑ").size() if "ΦΥΛΟ" in df else pd.Series(dtype=int)
    girls = df[df.get("ΦΥΛΟ", "").eq("Κ")].groupby("ΤΜΗΜΑ").size() if "ΦΥΛΟ" in df else pd.Series(dtype=int)
    educators = df[df.get("ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ", "").eq("Ν")].groupby("ΤΜΗΜΑ").size() if "ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ" in df else pd.Series(dtype=int)
    energetic = df[df.get("ΖΩΗΡΟΣ", "").eq("Ν")].groupby("ΤΜΗΜΑ").size() if "ΖΩΗΡΟΣ" in df else pd.Series(dtype=int)
    special = df[df.get("ΙΔΙΑΙΤΕΡΟΤΗΤΑ", "").eq("Ν")].groupby("ΤΜΗΜΑ").size() if "ΙΔΙΑΙΤΕΡΟΤΗΤΑ" in df else pd.Series(dtype=int)
    greek = df[df.get("ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ", "").eq("Ν")].groupby("ΤΜΗΜΑ").size() if "ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ" in df else pd.Series(dtype=int)
    total = df.groupby("ΤΜΗΜΑ").size() if "ΤΜΗΜΑ" in df else pd.Series(dtype=int)

    # Broken friendships per class
    try:
        pairs = list_broken_mutual_pairs(df)
        if pairs.empty:
            broken = pd.Series({tmima: 0 for tmima in df["ΤΜΗΜΑ"].dropna().astype(str).str.strip().unique()})
        else:
            counts = {}
            for _, row in pairs.iterrows():
                a_c = str(row["A_ΤΜΗΜΑ"]).strip(); b_c = str(row["B_ΤΜΗΜΑ"]).strip()
                counts[a_c] = counts.get(a_c, 0) + 1
                counts[b_c] = counts.get(b_c, 0) + 1
            broken = pd.Series(counts).astype(int)
    except Exception:
        broken = pd.Series(dtype=int)

    # Conflicts per class = sum of per-student counts (no pairs)
    try:
        conf_counts, _conf_names = compute_conflict_counts_and_names(df)
        if "ΤΜΗΜΑ" in df:
            cls = df["ΤΜΗΜΑ"].astype(str).str.strip()
            conflict_by_class = conf_counts.groupby(cls).sum().astype(int)
        else:
            conflict_by_class = pd.Series(dtype=int)
    except Exception:
        conflict_by_class = pd.Series(dtype=int)

    stats = pd.DataFrame({
        "ΑΓΟΡΙΑ": boys,
        "ΚΟΡΙΤΣΙΑ": girls,
        "ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ": educators,
        "ΖΩΗΡΟΙ": energetic,
        "ΙΔΙΑΙΤΕΡΟΤΗΤΑ": special,
        "ΓΝΩΣΗ ΕΛΛΗΝΙΚΩΝ": greek,
        "ΣΥΓΚΡΟΥΣΗ": conflict_by_class,
        "ΣΠΑΣΜΕΝΗ ΦΙΛΙΑ": broken,
        "ΣΥΝΟΛΟ ΜΑΘΗΤΩΝ": total,
    }).fillna(0).astype(int)

    if hasattr(stats.index, "str"):
        stats = stats.loc[stats.index.str.lower() != "nan"]
    try:
        stats = stats.sort_index(key=lambda x: x.str.extract(r"(\d+)")[0].astype(float))
    except Exception:
        stats = stats.sort_index()
    return stats

# ---------------------------
# Export helpers
# ---------------------------

def export_stats_to_excel(stats_df: pd.DataFrame) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        stats_df.to_excel(writer, index=True, sheet_name="Στατιστικά", index_label="ΤΜΗΜΑ")
        wb = writer.book
        ws = writer.sheets["Στατιστικά"]
        header_fmt = wb.add_format({"bold": True, "valign":"vcenter", "text_wrap": True, "border":1})
        for col_idx, value in enumerate(["ΤΜΗΜΑ"] + list(stats_df.columns)):
            ws.write(0, col_idx, value, header_fmt)
        for i in range(0, len(stats_df.columns)+1):
            ws.set_column(i, i, 18)
    output.seek(0)
    return output


def sanitize_sheet_name(s: str) -> str:
    s = str(s or "")
    s = re.sub(r'[:\\/?*\\[\\]]', ' ', s)
    return s[:31] if s else "SHEET"

# ---------------------------
# Upload (with resettable key)
# ---------------------------

st.markdown("### 📥 Εισαγωγή Αρχείου Excel")
uploaded = st.file_uploader(
    "Επίλεξε **Excel** με ένα ή περισσότερα sheets (σενάρια)",
    type=["xlsx","xls"],
    key=f"uploader_{st.session_state['uploader_key']}"
)

if not uploaded:
    st.info("➕ Ανέβασε ένα Excel για να συνεχίσεις.")
    st.stop()

try:
    xl = pd.ExcelFile(uploaded)
    st.success(f"✅ Επεξεργασία αρχείου: **{uploaded.name}** — Βρέθηκαν {len(xl.sheet_names)} sheet(s).")
except Exception as e:
    st.error(f"❌ Σφάλμα ανάγνωσης: {e}")
    st.stop()

# ---------------------------
# Tabs (NO conflict pairs tab)
# ---------------------------

tab_stats, tab_broken, tab_mass = st.tabs([
    "📊 Στατιστικά (1 sheet)",
    "🧩 Σπασμένες αμοιβαίες (όλα τα sheets) — Έξοδος: Πλήρες αντίγραφο + Σύνοψη",
    "📦 Μαζικές αναφορές",
])

with tab_stats:
    st.subheader("📊 Υπολογισμός Στατιστικών για Επιλεγμένο Sheet")
    sheet = st.selectbox("Διάλεξε sheet", options=xl.sheet_names, index=0)
    df_raw = xl.parse(sheet_name=sheet)
    df_norm, ren_map = auto_rename_columns(df_raw)

    # ✅ Μετρητής ΣΥΓΚΡΟΥΣΗ & ονόματα (χωρίς ζεύγη A–B)
    try:
        conflict_counts, conflict_names = compute_conflict_counts_and_names(df_norm)
        df_with = df_norm.copy()
        df_with["ΣΥΓΚΡΟΥΣΗ"] = conflict_counts.astype(int)
        df_with["ΣΥΓΚΡΟΥΣΗ_ΟΝΟΜΑ"] = conflict_names
        # 🧩 Σπασμένες αμοιβαίες ανά μαθητή (μετρητής + ονόματα)
        try:
            broken_counts_ps, broken_names_ps = compute_broken_friend_names_per_student(df_norm)
            df_with["ΣΠΑΣΜΕΝΗ_ΦΙΛΙΑ"] = broken_counts_ps.astype(int)
            df_with["ΣΠΑΣΜΕΝΗ_ΦΙΛΙΑ_ΟΝΟΜΑ"] = broken_names_ps
        except Exception:
            pass
    except Exception:
        df_with = df_norm

    missing = [c for c in REQUIRED_COLS if c not in df_norm.columns]
    with st.expander("🔎 Διάγνωση/Μετονομασίες", expanded=False):
        st.write("Αναγνωρισμένες στήλες:", list(df_norm.columns))
        if ren_map:
            st.write("Αυτόματες μετονομασίες:", ren_map)
        if missing:
            st.error("❌ Λείπουν υποχρεωτικές στήλες: " + ", ".join(missing))

    if not missing:
        with st.expander("👁️ Πίνακας μαθητών (με ΣΥΓΚΡΟΥΣΗ & ονόματα)", expanded=False):
            st.dataframe(df_with, use_container_width=True)
            # Λήψη ως Excel
            bio_conf = BytesIO()
            with pd.ExcelWriter(bio_conf, engine="xlsxwriter") as writer:
                df_with.to_excel(writer, index=False, sheet_name="Μαθητές_Σύγκρουση")
            bio_conf.seek(0)
            st.download_button(
                "⬇️ Κατέβασε πίνακα μαθητών (με ΣΥΓΚΡΟΥΣΗ & ονόματα)",
                data=bio_conf.getvalue(),
                file_name=f"students_conflicts_{sanitize_sheet_name(sheet)}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # 🧮 Στατιστικά ανά τμήμα
        stats_df = generate_stats(df_norm)
        # Διασφάλιση ύπαρξης στήλης "ΣΥΓΚΡΟΥΣΗ" στα στατιστικά
        if "ΣΥΓΚΡΟΥΣΗ" not in stats_df.columns:
            try:
                conf_counts, _conf_names = compute_conflict_counts_and_names(df_norm)
                if "ΤΜΗΜΑ" in df_norm:
                    cls = df_norm["ΤΜΗΜΑ"].astype(str).str.strip()
                    conflict_by_class = conf_counts.groupby(cls).sum().astype(int)
                else:
                    conflict_by_class = pd.Series(dtype=int)
                stats_df["ΣΥΓΚΡΟΥΣΗ"] = [int(conflict_by_class.get(str(idx).strip(), 0)) for idx in stats_df.index]
                cols = list(stats_df.columns)
                if "ΣΠΑΣΜΕΝΗ ΦΙΛΙΑ" in cols:
                    cols.insert(cols.index("ΣΠΑΣΜΕΝΗ ΦΙΛΙΑ"), cols.pop(cols.index("ΣΥΓΚΡΟΥΣΗ")))
                    stats_df = stats_df[cols]
            except Exception:
                pass

        st.dataframe(stats_df, use_container_width=True)
        st.download_button(
            "💾 Λήψη Πίνακα Στατιστικών (Excel)",
            data=export_stats_to_excel(stats_df).getvalue(),
            file_name=f"statistika_{sanitize_sheet_name(sheet)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
    else:
        st.info("Συμπλήρωσε/διόρθωσε τις στήλες που λείπουν στο Excel και ξαναφόρτωσέ το.")

with tab_broken:
    st.subheader("🧩 Αναφορά Σπασμένων Πλήρως Αμοιβαίων Δυάδων (όλα τα sheets)")
    summary_rows = []
    for sheet in xl.sheet_names:
        df_raw = xl.parse(sheet_name=sheet)
        df_norm, _ = auto_rename_columns(df_raw)
        broken_df = list_broken_mutual_pairs(df_norm)
        summary_rows.append({"Σενάριο (sheet)": sheet, "Σπασμένες Δυάδες": int(len(broken_df))})
    summary = pd.DataFrame(summary_rows).sort_values("Σενάριο (sheet)")
    st.dataframe(summary, use_container_width=True)

    # Build full report: copy originals + *_BROKEN + Σύνοψη
    def build_broken_report(xl_file: pd.ExcelFile) -> BytesIO:
        bio = BytesIO()
        rows = []
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            for sheet in xl_file.sheet_names:
                df_raw = xl_file.parse(sheet_name=sheet)
                df_raw.to_excel(writer, index=False, sheet_name=sanitize_sheet_name(sheet))
            for sheet in xl_file.sheet_names:
                df_raw = xl_file.parse(sheet_name=sheet)
                df_norm, _ = auto_rename_columns(df_raw)
                broken_df = list_broken_mutual_pairs(df_norm)
                rows.append({"Σενάριο (sheet)": sheet, "Σπασμένες Δυάδες": int(len(broken_df))})
                out_name = sanitize_sheet_name(f"{sheet}_BROKEN")
                if broken_df.empty:
                    pd.DataFrame({"info": ["— καμία σπασμένη —"]}).to_excel(writer, index=False, sheet_name=out_name)
                else:
                    broken_df.to_excel(writer, index=False, sheet_name=out_name)
            pd.DataFrame(rows).sort_values("Σενάριο (sheet)").to_excel(writer, index=False, sheet_name="Σύνοψη")
        bio.seek(0)
        return bio

    st.download_button(
        "⬇️ Κατέβασε αναφορά (Πλήρες αντίγραφο + σπασμένες + σύνοψη)",
        data=build_broken_report(xl).getvalue(),
        file_name=f"broken_friends_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    with st.expander("🔍 Προβολή αναλυτικών ζευγών & διάγνωση ανά sheet"):
        for sheet in xl.sheet_names:
            df_raw = xl.parse(sheet_name=sheet)
            df_norm, _ = auto_rename_columns(df_raw)
            broken_df = list_broken_mutual_pairs(df_norm)
            # Διάγνωση αντιστοίχισης ονομάτων
            # (προαιρετικά μπορεί να προστεθεί λεπτομερής διάγνωση όπως στο app3)
            st.markdown(f"**{sheet}**")
            if broken_df.empty:
                st.info("— Καμία σπασμένη πλήρως αμοιβαία δυάδα —")
            else:
                st.dataframe(broken_df, use_container_width=True)

# ===========================
# 📦 Mass report (all sheets): broken friendships + conflicts (per-student only)
# ===========================

with tab_mass:
    st.subheader("📦 Μαζικές αναφορές — Σπασμένες φιλίες & Συγκρούσεις (χωρίς ζεύγη σύγκρουσης)")

    def build_mass_broken_and_conflicts_report(xl_file: pd.ExcelFile) -> BytesIO:
        bio = BytesIO()
        summary_rows = []
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            for idx, sheet in enumerate(xl_file.sheet_names, start=1):
                df_raw = xl_file.parse(sheet_name=sheet)
                df_norm, _ = auto_rename_columns(df_raw)

                broken_pairs = list_broken_mutual_pairs(df_norm)
                conf_counts, conf_names = compute_conflict_counts_and_names(df_norm)

                broken_counts_ps, broken_names_ps = compute_broken_friend_names_per_student(df_norm)
                df_ps_broken = pd.DataFrame({
                    "ΟΝΟΜΑ": df_norm.get("ΟΝΟΜΑ", pd.Series(dtype=str)),
                    "ΤΜΗΜΑ": df_norm.get("ΤΜΗΜΑ", pd.Series(dtype=str)),
                    "ΣΠΑΣΜΕΝΗ_ΦΙΛΙΑ": broken_counts_ps.astype(int),
                    "ΣΠΑΣΜΕΝΗ_ΦΙΛΙΑ_ΟΝΟΜΑ": broken_names_ps,
                })
                df_ps_conf = pd.DataFrame({
                    "ΟΝΟΜΑ": df_norm.get("ΟΝΟΜΑ", pd.Series(dtype=str)),
                    "ΤΜΗΜΑ": df_norm.get("ΤΜΗΜΑ", pd.Series(dtype=str)),
                    "ΣΥΓΚΡΟΥΣΗ": conf_counts.astype(int),
                    "ΣΥΓΚΡΟΥΣΗ_ΟΝΟΜΑ": conf_names,
                })

                bp_name  = f"S{idx}_BP"   # broken pairs
                bps_name = f"S{idx}_BPS"  # broken per student
                cps_name = f"S{idx}_CPS"  # conflicts per student

                (broken_pairs if not broken_pairs.empty else pd.DataFrame({"info":["— καμία —"]})).to_excel(writer, index=False, sheet_name=bp_name)
                df_ps_broken.to_excel(writer, index=False, sheet_name=bps_name)
                df_ps_conf.to_excel(writer, index=False, sheet_name=cps_name)

                summary_rows.append({
                    "Index": idx,
                    "Original sheet name": sheet,
                    "S-code": f"S{idx}",
                    "Broken Pairs (rows)": int(len(broken_pairs)),
                    "Students with ≥1 Broken Friendship": int((broken_counts_ps.fillna(0) > 0).sum()),
                    "Students with ≥1 Conflict in Same Class": int((conf_counts.fillna(0) > 0).sum()),
                })

            pd.DataFrame(summary_rows).to_excel(writer, index=False, sheet_name="SUMMARY")
        bio.seek(0)
        return bio

    # Ζωντανή σύνοψη
    summary_rows = []
    for sheet in xl.sheet_names:
        df_raw = xl.parse(sheet_name=sheet)
        df_norm, _ = auto_rename_columns(df_raw)
        bp = list_broken_mutual_pairs(df_norm)
        bc_ps, _ = compute_broken_friend_names_per_student(df_norm)
        conf_counts, _ = compute_conflict_counts_and_names(df_norm)
        summary_rows.append({
            "Σενάριο (sheet)": sheet,
            "Σπασμένες Δυάδες (pairs)": int(len(bp)),
            "Μαθητές με Σπασμένη Φιλία (>=1)": int((bc_ps.fillna(0) > 0).sum()),
            "Μαθητές με Σύγκρουση στην ίδια τάξη (>=1)": int((conf_counts.fillna(0) > 0).sum()),
        })
    st.dataframe(pd.DataFrame(summary_rows).sort_values("Σενάριο (sheet)"), use_container_width=True)

    st.download_button(
        "⬇️ Κατέβασε ΜΑΖΙΚΗ αναφορά (όλα τα sheets)",
        data=build_mass_broken_and_conflicts_report(xl).getvalue(),
        file_name=f"mass_broken_conflicts_names_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
