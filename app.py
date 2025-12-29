import streamlit as st
import pandas as pd
import os

# ----------------------------------
# PAGE SETUP
# ----------------------------------
st.set_page_config(page_title="Rescoring Quality Dashboard", layout="wide")
st.title("📊 Rescoring Quality Dashboard")

# ----------------------------------
# ADMIN CONFIG
# ----------------------------------
ADMIN_PASSWORD = "admin123"        # 🔴 change this
DATA_DIR = "data"
DATA_FILE = f"{DATA_DIR}/latest.xlsx"

# ----------------------------------
# ADMIN UPLOAD (ONLY FOR YOU)
# ----------------------------------
st.sidebar.header("Admin Upload")
password = st.sidebar.text_input("Admin Password", type="password")

if password == ADMIN_PASSWORD:
    uploaded_file = st.sidebar.file_uploader("Upload Excel file", type=["xlsx"])

    if uploaded_file:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("File uploaded successfully")

# ----------------------------------
# LOAD SHARED DATA (FOR EVERYONE)
# ----------------------------------
if not os.path.exists(DATA_FILE):
    st.warning("No data uploaded yet. Admin must upload the file.")
    st.stop()

df = pd.read_excel(DATA_FILE)

# ----------------------------------
# COLUMN CONSTANTS (0-based)
# ----------------------------------
PART_COL = 11
SCORER1_ID_COL = 45
SCORER2_ID_COL = 60

# AY → BC (Scorer-2 score presence check)
S2_CHECK_COLS = [50, 51, 52, 53, 54]

# -------- Part A --------
PA_FINAL = [20, 21, 22, 23]
PA_S1 = [35, 36, 37, 38]
PA_S2 = [50, 51, 52, 53]
PA_AI = [95, 96, 97, 98]

# -------- Part B --------
PB_FINAL = [20, 21, 22, 23, 24]
PB_S1 = [35, 36, 37, 38, 39]
PB_S2 = [50, 51, 52, 53, 54]
PB_AI = [95, 96, 97, 98, 99]

# ----------------------------------
# SPLIT DATA
# ----------------------------------
part_a = df[df.iloc[:, PART_COL].astype(str).str.strip() == "A"]
part_b = df[df.iloc[:, PART_COL].astype(str).str.strip() == "B"]

# ----------------------------------
# RESCORING % HIGHLIGHT
# ----------------------------------
def highlight_rescoring_pct(val):
    try:
        if val >= 10:
            return "background-color:#FFCC99"  # light orange
    except:
        pass
    return ""

def style_rescoring_pct(df):
    if "Rescoring %" not in df.columns:
        return df
    return (
        df.style
        .applymap(highlight_rescoring_pct, subset=["Rescoring %"])
        .format({"Rescoring %": "{:.2f}%"})
    )

# ----------------------------------
# HUMAN SCORER TABLE
# ----------------------------------
def build_human_table(data, part):

    if part == "A":
        labels = ["TA1", "TA2", "Style", "Accuracy"]
        final_cols, s1_cols, s2_cols, ai_cols = PA_FINAL, PA_S1, PA_S2, PA_AI
    else:
        labels = ["GA1", "GA2", "V", "G", "O"]
        final_cols, s1_cols, s2_cols, ai_cols = PB_FINAL, PB_S1, PB_S2, PB_AI

    scorer_ids = pd.concat([
        data.iloc[:, SCORER1_ID_COL],
        data.iloc[:, SCORER2_ID_COL]
    ]).dropna().unique()

    output = []

    for sid in scorer_ids:
        rows = data[
            (data.iloc[:, SCORER1_ID_COL] == sid) |
            (data.iloc[:, SCORER2_ID_COL] == sid)
        ]

        rescored_rows = set()
        rescored_view = {k: 0 for k in labels}

        for idx, r in rows.iterrows():
            final = r.iloc[final_cols].values
            row_flag = False

            for scorer_col, score_cols in [
                (SCORER1_ID_COL, s1_cols),
                (SCORER2_ID_COL, s2_cols)
            ]:
                if r.iloc[scorer_col] != sid:
                    continue

                scored = r.iloc[score_cols].values

                if scorer_col == SCORER2_ID_COL and pd.isna(scored).all():
                    scored = r.iloc[ai_cols].values

                if part == "A":
                    for i, k in enumerate(labels):
                        if final[i] != scored[i]:
                            rescored_view[k] += 1
                            row_flag = True
                else:
                    if final[0] != scored[0]:
                        rescored_view["GA1"] += 1
                        row_flag = True
                    if final[1] != scored[1]:
                        rescored_view["GA2"] += 1
                        row_flag = True
                    if abs(sum(final[2:5]) - sum(scored[2:5])) > 1:
                        rescored_view["V"] += 1
                        rescored_view["G"] += 1
                        rescored_view["O"] += 1
                        row_flag = True

            if row_flag:
                rescored_rows.add(idx)

        total = len(rows)
        rescored = len(rescored_rows)

        row = {
            "Scorer ID": sid,
            "Total Scored": total,
            "Total Rescored": rescored,
            "Rescoring %": round((rescored / total) * 100, 2) if total else 0
        }

        for k in labels:
            row[f"Rescored {k}"] = rescored_view[k]

        output.append(row)

    return pd.DataFrame(output)

# ----------------------------------
# AI TABLE
# ----------------------------------
def build_ai_table(data, part):

    if part == "A":
        labels = ["TA1", "TA2", "Style", "Accuracy"]
        final_cols, ai_cols = PA_FINAL, PA_AI
    else:
        labels = ["GA1", "GA2", "V", "G", "O"]
        final_cols, ai_cols = PB_FINAL, PB_AI

    ai_rows = data[data.iloc[:, S2_CHECK_COLS].isna().all(axis=1)]

    rescored_rows = 0
    rescored_view = {k: 0 for k in labels}

    for _, r in ai_rows.iterrows():
        final = r.iloc[final_cols].values
        ai = r.iloc[ai_cols].values
        row_flag = False

        if part == "A":
            for i, k in enumerate(labels):
                if final[i] != ai[i]:
                    rescored_view[k] += 1
                    row_flag = True
        else:
            if final[0] != ai[0]:
                rescored_view["GA1"] += 1
                row_flag = True
            if final[1] != ai[1]:
                rescored_view["GA2"] += 1
                row_flag = True
            if abs(sum(final[2:5]) - sum(ai[2:5])) > 1:
                rescored_view["V"] += 1
                rescored_view["G"] += 1
                rescored_view["O"] += 1
                row_flag = True

        if row_flag:
            rescored_rows += 1

    row = {
        "Total Scored by AI": len(ai_rows),
        "Total Rescored": rescored_rows,
        "Rescoring %": round((rescored_rows / len(ai_rows)) * 100, 2) if len(ai_rows) else 0
    }

    for k in labels:
        row[f"Rescored {k}"] = rescored_view[k]

    return pd.DataFrame([row])

# ----------------------------------
# DASHBOARD (USE st.write FOR STYLING)
# ----------------------------------
st.subheader("🟦 Part A – Human Scorers")
st.write(style_rescoring_pct(build_human_table(part_a, "A")))

st.subheader("🟩 Part B – Human Scorers")
st.write(style_rescoring_pct(build_human_table(part_b, "B")))

st.subheader("🤖 Part A – AI")
st.write(style_rescoring_pct(build_ai_table(part_a, "A")))

st.subheader("🤖 Part B – AI")
st.write(style_rescoring_pct(build_ai_table(part_b, "B")))

