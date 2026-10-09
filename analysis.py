"""Analysis functions for Parts 2-4. Data comes from the SQLite database."""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DB_PATH = Path(__file__).resolve().parent / "loblaw_bio.db"
POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    if not Path(db_path).exists():
        raise FileNotFoundError(f"{db_path} not found - run `python load_data.py` first.")
    return sqlite3.connect(db_path)



#Part 2

SUMMARY_SQL = """
SELECT cc.sample_id                          AS sample,
       t.total_count                         AS total_count,
       cc.population                         AS population,
       cc.count                              AS count,
       100.0 * cc.count / t.total_count      AS percentage
FROM cell_counts cc
JOIN (SELECT sample_id, SUM(count) AS total_count
      FROM cell_counts GROUP BY sample_id) t USING (sample_id)
ORDER BY cc.sample_id, cc.population
"""


def summary_table(con) -> pd.DataFrame:
    """One row per sample x population with relative frequency (%)."""
    return pd.read_sql_query(SUMMARY_SQL, con)



# Part 3

RESPONSE_SQL = """
SELECT s.sample_id AS sample, s.subject_id AS subject, s.time_from_treatment_start AS time,
       sub.response, cc.population,
       100.0 * cc.count / t.total AS percentage
FROM samples s
JOIN subjects sub ON sub.subject_id = s.subject_id
JOIN cell_counts cc ON cc.sample_id = s.sample_id
JOIN (SELECT sample_id, SUM(count) AS total FROM cell_counts GROUP BY sample_id) t
     ON t.sample_id = s.sample_id
WHERE sub.condition = 'melanoma' AND sub.treatment = 'miraclib'
  AND s.sample_type = 'PBMC' AND sub.response IN ('yes', 'no')
"""


def response_data(con, time=None) -> pd.DataFrame:
    """Melanoma + miraclib + PBMC relative frequencies, labelled by response.

    `time` optionally restricts to one time_from_treatment_start value.
    """
    df = pd.read_sql_query(RESPONSE_SQL, con)
    df["response"] = df["response"].map({"yes": "responder", "no": "non-responder"})
    if time is not None:
        df = df[df["time"] == time]
    return df


def _bh(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values."""
    p = np.asarray(p, float)
    order = np.argsort(p)
    ranked = p[order] * len(p) / (np.arange(len(p)) + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(adj)
    out[order] = np.clip(adj, 0, 1)
    return out


def compare_populations(df: pd.DataFrame, level: str = "sample", alpha: float = 0.05) -> pd.DataFrame:

    if level == "subject":
        df = df.groupby(["subject", "response", "population"], as_index=False)["percentage"].mean()
    rows = []
    for pop in POPULATIONS:
        d = df[df["population"] == pop]
        r = d.loc[d["response"] == "responder", "percentage"].to_numpy()
        n = d.loc[d["response"] == "non-responder", "percentage"].to_numpy()
        if len(r) < 2 or len(n) < 2:
            continue
        u, p = stats.mannwhitneyu(r, n, alternative="two-sided")
        rows.append({
            "population": pop, "level": level,
            "n_responder": len(r), "n_non_responder": len(n),
            "median_responder": np.median(r), "median_non_responder": np.median(n),
            "mean_responder": r.mean(), "mean_non_responder": n.mean(),
            "median_diff": np.median(r) - np.median(n),
            "cliffs_delta": 2 * u / (len(r) * len(n)) - 1,
            "U": u, "p_value": p,
        })
    out = pd.DataFrame(rows)
    out["p_adj_BH"] = _bh(out["p_value"].to_numpy())
    out["significant"] = out["p_adj_BH"] < alpha
    return out


def boxplot_figure(df: pd.DataFrame, stats_df: pd.DataFrame | None = None):
    import plotly.express as px
    fig = px.box(
        df, x="response", y="percentage", color="response", facet_col="population",
        category_orders={"population": POPULATIONS, "response": ["responder", "non-responder"]},
        points="outliers", hover_data=["sample", "subject", "time"],
        color_discrete_map={"responder": "#2a9d8f", "non-responder": "#e76f51"},
        labels={"percentage": "Relative frequency (%)", "response": ""},
    )
    fig.update_yaxes(matches=None, showticklabels=True)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    if stats_df is not None:
        for i, pop in enumerate(POPULATIONS, start=1):
            row = stats_df[stats_df["population"] == pop]
            if len(row):
                star = "*" if bool(row["significant"].iloc[0]) else "ns"
                fig.layout.annotations[i - 1].text += f"<br>q={row['p_adj_BH'].iloc[0]:.3g} {star}"
    fig.update_layout(showlegend=False, height=460, margin=dict(t=90))
    return fig


def boxplot_png(df: pd.DataFrame, stats_df: pd.DataFrame, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(POPULATIONS), figsize=(16, 4.5))
    for ax, pop in zip(axes, POPULATIONS):
        d = df[df["population"] == pop]
        groups = [d.loc[d["response"] == g, "percentage"] for g in ("responder", "non-responder")]
        bp = ax.boxplot(groups, tick_labels=["responder", "non-responder"], patch_artist=True)
        for patch, c in zip(bp["boxes"], ("#2a9d8f", "#e76f51")):
            patch.set_facecolor(c)
        row = stats_df[stats_df["population"] == pop].iloc[0]
        ax.set_title(f"{pop}\nq={row['p_adj_BH']:.3g}" + (" *" if row["significant"] else " (ns)"))
        ax.set_ylabel("Relative frequency (%)" if pop == POPULATIONS[0] else "")
        ax.tick_params(axis="x", labelrotation=20)
    fig.suptitle("Melanoma, miraclib, PBMC: responders vs non-responders")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# Ad hoc queries
def average_count(con, population: str, condition=None, sex=None, response=None,
                  treatment=None, sample_type=None, time=None) -> tuple[float, int]:
    """Mean raw cell count for one population over samples matching the filters.

    Any filter left as None is not applied. Returns (mean, number_of_samples).
    Example: average_count(con, "b_cell", condition="melanoma", sex="M",
                           response="yes", time=0)
    """
    where, params = ["cc.population = ?"], [population]
    for clause, value in [("sub.condition = ?", condition), ("sub.sex = ?", sex),
                          ("sub.response = ?", response), ("sub.treatment = ?", treatment),
                          ("s.sample_type = ?", sample_type),
                          ("s.time_from_treatment_start = ?", time)]:
        if value is not None:
            where.append(clause)
            params.append(value)
    row = con.execute(
        "SELECT AVG(cc.count), COUNT(*) FROM cell_counts cc "
        "JOIN samples s ON s.sample_id = cc.sample_id "
        "JOIN subjects sub ON sub.subject_id = s.subject_id "
        "WHERE " + " AND ".join(where), params).fetchone()
    return row[0], row[1]


#Part 4
BASELINE_SQL = """
SELECT s.sample_id, s.subject_id, sub.project_id AS project, sub.response, sub.sex,
       sub.age, s.time_from_treatment_start AS time
FROM samples s
JOIN subjects sub ON sub.subject_id = s.subject_id
WHERE sub.condition = 'melanoma' AND sub.treatment = 'miraclib'
  AND s.sample_type = 'PBMC' AND s.time_from_treatment_start = 0
ORDER BY s.sample_id
"""


def baseline_subset(con) -> dict:
    """Melanoma PBMC baseline samples from miraclib-treated patients, plus breakdowns."""
    samples = pd.read_sql_query(BASELINE_SQL, con)
    by_project = (samples.groupby("project")["sample_id"].nunique()
                  .rename("n_samples").reset_index())
    subj = samples.drop_duplicates("subject_id")
    by_response = (subj.groupby("response", dropna=False)["subject_id"].nunique()
                   .rename("n_subjects").reset_index())
    by_sex = subj.groupby("sex")["subject_id"].nunique().rename("n_subjects").reset_index()
    return {"samples": samples, "by_project": by_project,
            "by_response": by_response, "by_sex": by_sex}
