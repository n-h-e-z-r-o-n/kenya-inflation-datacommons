# Learning Log — Kenya Inflation Data Pipeline

*Fill in the approximate durations from your own work before submitting. The events below are drawn from the project and troubleshooting record; exact time spent is not documented.*

| What I needed to learn | How I learned it / what I tried | Approx. time |
|---|---|---|
| Extracting the CBK HTML inflation table reliably | CBK saved HTML and Python exceptions; `pandas.read_html()` heading match failed, so I used BeautifulSoup with year/month row validation. | **[fill in]** |
| Python packages and local file paths | Virtual environment/pip errors (`lxml` missing); corrected source-relative paths after files were created outside the repository. | **[fill in]** |
| Running Docker on Windows | Docker Desktop error about Virtual Machine Platform; configured Windows/WSL 2 and learned bind mounts and absolute host paths. | **[fill in]** |
| Data Commons CSV, MCF and config | [Custom Data documentation](https://docs.datacommons.org/custom_dc/custom_data.html), the assignment brief and importer logs; fixed `Unsupported import type: variables` by using `observations`. | **[fill in]** |
| Verifying data and managing repeats | Compared source, generated CSV and SQLite with `readback.py`; documented the identical April 2019 duplicate and confirmed 282 matched observations. | **[fill in]** |

**Tools and AI disclosure:** Used Python, pandas, requests, BeautifulSoup, Docker Desktop, SQLite, Data Commons documentation, and ChatGPT for explanations, code suggestions, troubleshooting and documentation drafting. I checked the outputs by running the scripts and inspecting the saved CBK source, the loader success report and the independent SQLite readback (`PASS`, zero differences). No inflation values were supplied by AI.

**Total hands-on time:** **[enter actual total]**. If any task remained unfinished when work stopped, record it honestly in `docs/handover.md` and describe what you would do next.
