#!/usr/bin/env python3
"""End-to-end pipeline: load the database, then write all Part 2-4 outputs to outputs/."""
from pathlib import Path

import analysis
import load_data

OUT = Path(__file__).resolve().parent / "outputs"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    load_data.main()
    con = analysis.connect()

    # Part 2
    summary = analysis.summary_table(con)
    summary.to_csv(OUT / "part2_summary_table.csv", index=False)
    print(f"Part 2: {len(summary)} rows -> outputs/part2_summary_table.csv")

    # Part 3
    df = analysis.response_data(con)
    by_sample = analysis.compare_populations(df, "sample")
    by_subject = analysis.compare_populations(df, "subject")
    by_sample.to_csv(OUT / "part3_stats_sample_level.csv", index=False)
    by_subject.to_csv(OUT / "part3_stats_subject_level.csv", index=False)
    analysis.boxplot_png(df, by_sample, OUT / "part3_boxplot.png")
    cols = ["population", "median_responder", "median_non_responder", "p_value", "p_adj_BH", "significant"]
    print("\nPart 3 (sample level, Mann-Whitney U, BH-adjusted):")
    print(by_sample[cols].round(4).to_string(index=False))
    print("\nPart 3 (subject-mean sensitivity analysis):")
    print(by_subject[cols].round(4).to_string(index=False))

    # Part 4
    res = analysis.baseline_subset(con)
    res["samples"].to_csv(OUT / "part4_baseline_samples.csv", index=False)
    res["by_project"].to_csv(OUT / "part4_by_project.csv", index=False)
    res["by_response"].to_csv(OUT / "part4_by_response.csv", index=False)
    res["by_sex"].to_csv(OUT / "part4_by_sex.csv", index=False)
    print(f"\nPart 4: {len(res['samples'])} baseline samples")
    for k in ("by_project", "by_response", "by_sex"):
        print(f"\n{k}:\n{res[k].to_string(index=False)}")
    # Extra question: mean B cells, melanoma males, responders, baseline (all sample/treatment types)
    mean_b, n = analysis.average_count(con, "b_cell", condition="melanoma", sex="M",
                                       response="yes", time=0)
    line = f"Mean b_cell, melanoma males, responders, time=0: {mean_b:.2f} (n={n} samples)"
    (OUT / "extra_mean_b_cell.txt").write_text(line + "\n")
    print("\n" + line)
    con.close()


if __name__ == "__main__":
    main()
