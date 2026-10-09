#Python + SQLite pipeline and a Streamlit dashboard were implemented to analyze the miraclib clinical trial data.
#Execution on GitHub Codespaces

To run:
make setup       # installs dependencies
make pipeline    # build loblaw_bio.db and write all results to outputs/
make dashboard   # serve the dashboard on http://localhost:8501

# Program Files:

schema.sql
load_data.py - #Table definitions and indices
analysis.py  - # DB creation using schema.sql and loads the csv file
analysis.py  - # SQL queries, statistics and plots for Parts 2-4
pipeline.py  - # Runs load + analysis, writes outputs/
dashboard.py - # Streamlit dashboard

OUTPUT files
#Running `make pipeline' writes to `outputs/`:
 #part2_summary_table.csv: sample, total_count, population, count, percentage
 #part3_boxplot.png, part3_stats_sample_level.csv, part3_stats_subject_level.csv
 #part4_*.csv: baseline sample list and the project/response/sex based breakdowns		

#Database design
```
projects(project_id)
subjects(subject_id, project_id, condition, age, sex, treatment, response)
samples(sample_id, subject_id, sample_type, time_from_treatment_start)
cell_counts(sample_id, population, count)        -- long format
```

#Treatment, response, sex and age belong to the subject, stored once rather
than repeated - maintains consistency
#Cell counts stored in long format
#Indexes cover the filters the analyses use (condition/treatment/response, sample type, time)


#Statistical approach used in part3
Population: melanoma patients on miraclib, PBMC samples, response `yes` vs `no`.
Test used: Two-sided Mann-Whitney U per cell population. Why? Relative frequencies need not be normal, so a rank test was used.
Multiple testing: 5 cell populations were tested, so p-values were Benjamini-Hochberg adjusted, at p < 0.05.
Effect size: Cliff's delta and the median difference are reported next to each p-value,
so a result is judged on size as well as significance.

#Part 4
Baseline = `time_from_treatment_start = 0`. Samples are counted per project; responders/
non-responders and males/females are counted as distinct subjects.

#Interactive dashboard
Live deployed app using Streamlit link: https://loblawbio-6spcjf3uka7chbh5jzkm6c.streamlit.app/


