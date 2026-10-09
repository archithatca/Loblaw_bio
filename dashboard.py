"""Streamlit dashboard for Parts 2-4. Reads only from the SQLite database."""
import streamlit as st

import analysis

st.set_page_config(page_title="Loblaw Bio - miraclib trial", layout="wide")
st.title("Loblaw Bio: immune cell populations in the miraclib trial")

try:
    con = analysis.connect()
except FileNotFoundError as e:
    st.error(str(e) + "  (run `make pipeline` first)")
    st.stop()


@st.cache_data
def _summary():
    return analysis.summary_table(analysis.connect())


@st.cache_data
def _response():
    return analysis.response_data(analysis.connect())


@st.cache_data
def _baseline():
    return analysis.baseline_subset(analysis.connect())


tab2, tab3, tab4 = st.tabs(["Part 2: Frequencies", "Part 3: Responders vs non-responders",
                            "Part 4: Baseline subset"])

# ---- Part 2
with tab2:
    st.subheader("Relative frequency of each cell population per sample")
    df = _summary()
    c1, c2 = st.columns(2)
    pops = c1.multiselect("Population", analysis.POPULATIONS, default=analysis.POPULATIONS)
    q = c2.text_input("Sample id contains", "")
    view = df[df["population"].isin(pops)]
    if q:
        view = view[view["sample"].str.contains(q, case=False)]
    # column_config (not a pandas Styler) so large tables are not limited to ~262k cells
    st.dataframe(view, width="stretch", hide_index=True,
                 column_config={"percentage": st.column_config.NumberColumn(
                     "percentage", format="%.2f")})
    st.caption(f"{view['sample'].nunique()} samples, {len(view)} rows")
    st.download_button("Download CSV", view.to_csv(index=False), "summary_table.csv")

# ---- Part 3
with tab3:
    st.subheader("Melanoma patients on miraclib (PBMC samples)")
    resp = _response()
    times = sorted(resp["time"].unique())
    choice = st.selectbox("Time from treatment start", ["All time points"] + [str(t) for t in times])
    sel = resp if choice == "All time points" else resp[resp["time"] == int(choice)]
    level = st.radio("Unit of analysis", ["sample", "subject"], horizontal=True,
                     help="'subject' averages each patient's samples first, so every patient counts once.")
    res = analysis.compare_populations(sel, level)
    st.plotly_chart(analysis.boxplot_figure(sel, res), width="stretch")
    st.dataframe(
        res[["population", "n_responder", "n_non_responder", "median_responder",
             "median_non_responder", "cliffs_delta", "p_value", "p_adj_BH", "significant"]]
        .style.format({"median_responder": "{:.2f}", "median_non_responder": "{:.2f}",
                       "cliffs_delta": "{:.3f}", "p_value": "{:.4g}", "p_adj_BH": "{:.4g}"}),
        width="stretch", hide_index=True)
    sig = res.loc[res["significant"], "population"].tolist()
    st.markdown(
        "**Significant after multiple-testing correction (BH q < 0.05):** "
        + (", ".join(sig) if sig else "none")
    )
    st.caption("Two-sided Mann-Whitney U test per population; p-values Benjamini-Hochberg "
               "adjusted across the five populations. Cliff's delta > 0 means higher in responders.")

# ---- Part 4
with tab4:
    st.subheader("Melanoma PBMC baseline samples (time = 0), miraclib-treated")
    b = _baseline()
    m1, m2, m3 = st.columns(3)
    m1.metric("Samples", len(b["samples"]))
    m2.metric("Subjects", b["samples"]["subject_id"].nunique())
    m3.metric("Projects", b["samples"]["project"].nunique())
    c1, c2, c3 = st.columns(3)
    c1.markdown("**Samples per project**")
    c1.dataframe(b["by_project"], hide_index=True)
    c2.markdown("**Subjects by response**")
    c2.dataframe(b["by_response"], hide_index=True)
    c3.markdown("**Subjects by sex**")
    c3.dataframe(b["by_sex"], hide_index=True)
    with st.expander("Matching samples"):
        st.dataframe(b["samples"], hide_index=True, width="stretch")
