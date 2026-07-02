# Third-Party Notices



This project is licensed under the **MIT License** (see [LICENSE](LICENSE)).



It uses the following open-source software. License names below are taken from

each package's PyPI metadata at the time of documentation (2026-07).



## Direct dependencies (`requirements.txt`)



| Package | Version | License | Notes |

|---------|---------|---------|-------|

| Django | 6.0.6 | BSD-3-Clause | Web framework |

| django-htmx | 1.27.0 | MIT | Django integration for HTMX |

| openpyxl | 3.1.5 | MIT | Excel export |

| python-dotenv | 1.2.2 | BSD-3-Clause | `.env` file loading (dev) |

| whitenoise | 6.9.0 | MIT | Static file serving (exe build) |

| xhtml2pdf | 0.2.17 | Apache-2.0 | PDF export |



## Frontend (bundled in static for offline exe)



| Library | Version | License |

|---------|---------|---------|

| [htmx](https://htmx.org/) | 2.0.4 | BSD-2-Clause |



## Build-only dependencies (`requirements-build.txt`)



| Package | License | Notes |

|---------|---------|-------|

| PyInstaller | GPL-2.0+ with exception | Used only to build the Windows exe; not distributed as part of the app runtime in source form |



## Transitive dependencies (selected)



| Package | License |

|---------|---------|

| asgiref | BSD-3-Clause |

| reportlab | BSD-3-Clause |

| html5lib | MIT |

| sqlparse | BSD-3-Clause |

| tzdata | Apache-2.0 |



To regenerate the dependency license list locally:



```bash

pip install pip-licenses

pip-licenses --format=markdown

```


