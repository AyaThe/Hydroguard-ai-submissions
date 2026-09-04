# Data sources — HydroGuard AI (Durban / eThekwini forecasting build)

**Project:** HydroGuard AI — Water Crisis Prediction for Durban/eThekwini Municipality  
**Lineage:** Lesson 16 HydroGuard snapshot EDA (`legacy/`) → dated four-week forecast (this build)  
**Date accessed:** 2 September 2026  
**Compiler:** research notes from official public pages, catalogues, and publications listed below  

This file records candidate datasets. The **submitted model uses two real public downloads only**: DWS HyData reservoir Point levels, and NASA POWER Daily catchment weather. CHIRPS was researched here as optional rainfall QA and is **not** used in training. No synthetic observations.

---

## 1. Geographical and system scope (verified)

eThekwini does **not** run a single local dam as its bulk supply. More than 98% of treated water is purchased from uMngeni-uThukela Water (UUW), formerly Umgeni Water (eThekwini Water Security / PWSeT dashboard, May 2026).

### 1.1 Primary system: Mgeni / uMngeni Water Supply System (WSS)

Official sources that name this as the bulk source for Durban–Pietermaritzburg:

| Source | What it states |
| --- | --- |
| UUW Infrastructure Master Plan 2026, Vol. 2 | The Durban–Pietermaritzburg region’s main potable source is the uMngeni System: four storage dams on the uMngeni River plus Mooi River storage/transfer. Lower uMngeni serves coastal eThekwini; Upper uMngeni serves inland municipalities and eThekwini Outer West. |
| DWS uMkhomazi Water Project feasibility summary | The Mgeni WSS is the main source for eThekwini, uMgungundlovu and Msunduzi. |
| DWS “Status of Drought in KZN” (Angela Masefield, 3 March 2016) | Defines **Mgeni WSS** as Spring Grove, Midmar, Albert Falls, Nagle and Inanda; users include eThekwini, iLembe, Ugu and uMgungundlovu (Howick, Pietermaritzburg, Durban, Upper South Coast). |
| DWS Weekly State of Dams (`Weekly.pdf`) | Reports a combined **UM / Umgeni** water-supply-system total (full-supply capacity about 920.90 million m³). |

**Dams in the Mgeni WSS (recommended modelling universe):**

| Dam | River | DWS station | Role for eThekwini | Full-supply capacity (approx., current DWS) | Verified level record (DWS reservoir catalogue) |
| --- | --- | --- | --- | --- | --- |
| Midmar | uMngeni | U2R001 | Upper system; Midmar WTW | 235.4–235.5 Mm³ | Level from **1963-10-29** |
| Albert Falls | uMngeni | U2R003 | Largest Mgeni storage; transfers from Midmar | 285.6–285.7 Mm³ | Level from **1975-06-09** |
| Nagle | uMngeni | U2R002 | Lower uMngeni; Durban Heights / Nagle–Inanda chain | 23.2–23.3 Mm³ | Level from **1980-12-01** (1% missing) |
| Inanda | uMngeni | U2R004 | Lower uMngeni; Wiggins WTW / coastal eThekwini | 237.4–237.5 Mm³ | Level from **1989-04-25** |
| Spring Grove | Mooi | V2R003 | Mooi–Mgeni Transfer Scheme Phase 2 into Midmar | 139.2–139.3 Mm³ | Level from **2014-03-10** |
| Mearns Weir/Dam | Mooi | V2R002 | MMTS-1 transfer into Mgeni; small storage | 5.2 Mm³ | Level from **2002-06-06** |

Coordinates (DWS catalogue, converted from dd:mm:ss where needed):

- Midmar U2R001: 29°29′42″S, 30°12′05″E  
- Nagle U2R002: 29°35′26″S, 30°37′39″E  
- Albert Falls U2R003: 29°25′52″S, 30°25′33″E  
- Inanda U2R004: 29°42′32″S, 30°52′01″E (HyDataSets also lists −29.70890, 30.86706)  
- Spring Grove V2R003: −29.31913, 29.96569  
- Hazelmere U3R001: 29°35′54″S, 31°02′34″E  

**Do not use Mearns as a large storage signal.** It is a transfer weir with ~5 Mm³ capacity.

**Combined Mgeni WSS full-supply capacity** used in the DWS weekly Umgeni system total is about **920.90 Mm³** (Midmar + Nagle + Albert Falls + Inanda + Spring Grove). This is the recommended combined-storage series.

### 1.2 Secondary system: North Coast / Hazelmere (do not mix into Mgeni storage)

Hazelmere Dam (U3R001, Mdloti River) supplies northern eThekwini and parts of iLembe / Siza Water. UUW and DWS treat this as a **separate** water-supply system. During 2015–16 it was under much stricter restrictions than Mgeni (DWS drought briefing: 30–50% domestic on Hazelmere vs 15% domestic on Mgeni).

Hazelmere was **raised** (FSC increased from ~17.7 Mm³ historically to **37.13 Mm³** in the 2017-10-01 basin survey). Percentage-full is not comparable across that change without using volume.

**Recommendation:** keep Hazelmere as an optional secondary model or appendix, not in the Mgeni combined target.

### 1.3 Not in the current bulk-supply model

- **Henley Dam:** small Msunduzi storage; not a Durban bulk source.  
- **South Coast dams** (Umzinto, E.J. Smith, Nungwane, Mhlabatshane): primarily Ugu; eThekwini south is also linked via the South Coast pipeline, but these are not the Durban metro bulk system.  
- **uMkhomazi / Smithfield / Lower uMkhomazi BWSS / Ngwadini:** future or incomplete augmentation. Do not treat as historical supply.  
- **Cape Town / WCWSS dams:** out of scope.

---

## 2. Restriction / low-storage threshold research

No public document found that states a single automatic “crisis” storage percentage for Mgeni (for example “restrict when the system falls below X%”). Restriction decisions are made by DWS / Joint Operating Committees and gazetted. The following **are** documented:

| Date / source | Finding | How it may be used |
| --- | --- | --- |
| July 2015; DWS drought briefing 3 Mar 2016 | Restrictions **gazetted** on Mgeni WSS: **15% domestic, 50% irrigation**. System storage cited as **78% (Jan 2015) → 59% (Jan 2016)**. | Confirms a real restriction episode; does **not** give a storage trigger. |
| Dec 2015 (news citing DWS; UUW statements 2016–17) | 15% restriction on domestic/industrial/commercial users in the greater Umgeni system. | Same episode. |
| UUW, Jul 2017 (Highway Mail / Infrastructure News) | Restrictions to remain until **average dam levels reach 70%**; collective storage then ~60%. Albert Falls was the stressed dam (~33%). | Closest **recovery** figure used in public UUW messaging. Not a gazetted trigger. |
| UUW, Nov 2017 (Highway Mail) | Collective storage 50%; unrestricted supply said to require resources **collectively at least 75%**. | Conflicts with the 70% figure. Must be disclosed. |
| UUW, Jan 2017 | Midmar and Albert Falls would each need to reach **70%** before resources were considered adequate. | Dam-specific recovery language, not a system trigger. |
| eThekwini PWSeT dashboard, May 2026 | “Current restriction level requires an **8% saving in demand**”; system described as over-abstracted. | Demand restriction, **not** a storage threshold. |
| DWS operating measures 2026/27 (news, Aug 2026) | uMngeni started the operating year at **99.5%**; **no storage restrictions** for 2026/27. South Coast has a 10% supply restriction for yield/demand reasons, not because storage was low. | Shows restrictions are not a 1:1 map of dam %. |

**Conclusion:** there is **no official published crisis threshold** of the form “Mgeni < X% = crisis”. There **is** a documented 2015–18 restriction episode, and UUW publicly used **70%** (and once **75%**) as a recovery / adequacy benchmark.

### Proposed academic target (to be labelled as such and made configurable)

- **Primary (proposed):** `future_low_storage = 1` if combined Mgeni WSS storage (volume-weighted % of current FSC for Midmar + Albert Falls + Nagle + Inanda + Spring Grove) is **below 70%** four weeks ahead.  
  - **Label:** academic / operational proxy, derived from UUW 2017 public recovery statements, **not** a gazetted drought trigger.  
  - **Justification:** 70% is the most repeated UUW figure for “adequate to meet full demand / lift restrictions”. It is historically populated (2015–18 drought).  
- **Sensitivity runs (required in later phases):** 60% and 75%; also Albert Falls alone < 40% (the dam that actually approached failure in 2016–17).  
- **Do not** copy Cape Town’s WCWSS restriction stages.

Class balance cannot be known until the series is downloaded. Qualitatively, 2015–2018 is the main positive-class window; 2019–2026 appears mostly high storage. If positives are too few, fall back to **four-week storage-percentage regression** (see risks).

---

## 3. Source table

Access method notes:

- **Official download** = provider exposes a data file, query URL, or API intended for retrieval.  
- **Dashboard export** = interactive UI with CSV/Excel; confirm export after approval.  
- **Do not scrape** where terms forbid scraping or where only a latest snapshot is published.

| Dataset name | Provider | URL | Variables | Date range (as published) | Frequency | Format | Access method | Licence / terms | Intended use | Known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Verified reservoir levels — Midmar U2R001 | DWS Hydrological Services | https://www.dws.gov.za/hydrology/Verified/HyDataSets.aspx?Station=U2R001 and HyData.aspx query | Reservoir water level (m); related spill/flow components | Level: 1963-10-29 to at least 2026-05-11 (catalogue) | Sub-daily Point (often 12-min); daily HyData is spillway flow, not storage | HTML/text time series via official HyData endpoint | Official station download. **Calendar-month Point chunks** because 7 000 primary records truncate a year of 12-min data after ~2 months. Polite rate limits. | DWS copyright retained. Free for **academic, research or personal** use. Must not be sold. Acknowledge DWS. No accuracy warranty. See NIWIS / WSKS copyright notices. | Core storage feature and target construction (convert level → volume/% using FSC tables) | Verified series can lag the weekly bulletin. FSC changed (Midmar raised; 2002 FSC 235.42 Mm³). Missing periods exist on some sensors. Year-long Point downloads from 2026-09-02 were truncated (e.g. Midmar 2015 ended 2015-02-27). |
| Verified reservoir levels — Albert Falls U2R003 | DWS | https://www.dws.gov.za/hydrology/Verified/HyDataSets.aspx?Station=U2R003 | Level (m) | 1975-06-09 to at least 2026-05-11 | Daily | Same | Same | Same | Core storage; historically the stressed dam | Basin surveys changed FSC (218.93 → 285.64 Mm³ net). |
| Verified reservoir levels — Nagle U2R002 | DWS | https://www.dws.gov.za/hydrology/Verified/HyDataSets.aspx?Station=U2R002 | Level (m) | 1980-12-01 to at least 2026-03-29; ~1% missing | Daily | Same | Same | Same | Core storage (small FSC; still in UM total) | Small dam; % can swing quickly. |
| Verified reservoir levels — Inanda U2R004 | DWS | https://www.dws.gov.za/hydrology/Verified/HyDataSets.aspx?Station=U2R004 | Level (m); spill; pipelines | RES 1989-04-25 to 2026-07-06 (station page, accessed 2026-09-02) | Daily | Same | Same | Same | Core lower-uMngeni storage for eThekwini | Starts 1989. Some downstream-level gaps. |
| Verified reservoir levels — Spring Grove V2R003 | DWS | https://www.dws.gov.za/hydrology/Verified/HyDataSets.aspx?Station=V2R003 | Level (m); downstream flow | RES 2014-03-10 to 2026-08-12 (station page) | Daily | Same | Same | Same | MMTS-2 storage in combined Mgeni WSS | **Limits combined 5-dam history to 2014-onward.** |
| Verified reservoir levels — Mearns V2R002 | DWS | Catalogue: https://www.dws.gov.za/Hydrology/Verified/dwafapp2_wma/WMA3_Pongola-Mtamvuna_Reservoir.pdf | Level (m) | 2002-06-06 to 2026-04-06 | Daily | Same | Same | Same | Optional transfer-scheme context only | Tiny FSC (~5 Mm³). Do not weight equally with large dams. |
| Verified reservoir levels — Hazelmere U3R001 | DWS | Catalogue PDF above; HyDataSets?Station=U3R001 | Level (m) | 1975-11-01 to 2026-04-26 | Daily | Same | Same | Same | Optional North Coast secondary target | FSC raised in 2017 (17.68 → 37.13 Mm³). Separate system. |
| Reservoir metadata / FSC tables | DWS | https://www.dws.gov.za/Hydrology/Verified/dwafapp2_wma/WMA3_Pongola-Mtamvuna_Reservoir.pdf | Station IDs, coordinates, FSC history, missing-% flags | Metadata current as of PDF (includes 2026 end dates) | Static catalogue | PDF | Manual download | DWS copyright; academic/research use | Convert levels to volume/%; document FSC changes | PDF parsing needed; FSC is not constant. |
| Weekly State of Dams — KZN table | DWS | https://www.dws.gov.za/Hydrology/Weekly/ProvinceWeek.aspx?region=KN | Dam name, river, FSC, this week %, last week %, last year % | **Latest week only** on the live page (accessed 2026-09-02: week of 2026-08-31) | Weekly | HTML table | Read current bulletin. Historical weeks are not offered as a bulk CSV on this page. | Same DWS terms. Public bulletin. | Near-real-time app overlay; QA against verified daily | Not a historical archive by itself. |
| Weekly State of Dams — national PDF | DWS | https://www.dws.gov.za/hydrology/Weekly/Weekly.pdf | Per-dam FSC, storage, %, last week, last year; **UM Umgeni system total** | Latest bulletin (overwrites) | Weekly | PDF | Official PDF download of current week | Same | System-level % (UM) for target; station codes | Historical PDFs would need an official archive; do not scrape the whole site. Internet Archive copies may exist for research — check robots/terms before bulk collection. |
| Weekly State of Dams — water supply systems | DWS | https://www.dws.gov.za/Hydrology/Weekly/Storage.aspx and WeekSys (UM) | Combined Umgeni system storage | Latest week | Weekly | HTML | Official bulletin | Same | Combined UM % | Live page timed out during this research pass; PDF confirms UM total exists. |
| NIWIS Surface Water Storage | DWS | https://www.dws.gov.za/niwis2/ and Surface Water Reserve dashboard | Dam storage time series (dashboard) | Open Data ZA toolkit: about **5 years** of weekly export | Weekly | CSV / Excel export from dashboard | Manual dashboard export (no documented public API) | DWS copyright; academic/research; not for sale | Backup weekly series if HyData is awkward | Navigation is manual. Not a bulk API. Portal was slow/unreliable during this pass. |
| River flow — Midmar downstream U2H048 | DWS | https://www.dws.gov.za/hydrology/Verified/HyDataSets.aspx?Station=U2H048 | Daily average flow (m³/s) | Long record (station from 1968-03-11); confirm on download | Daily | HyData text | Official download; 20-year chunks | Same | Optional inflow/outflow feature | Operating rules (transfers, pumping) confound rainfall–flow–storage. |
| River flow — Inanda U2H055 / U2H054 | DWS | https://www.dws.gov.za/hydrology/Verified/HyDataSets.aspx?Station=U2H055 | Flow, level | Inanda loc. from 1989 | Daily | HyData | Official download | Same | Optional lower-system flow | Same confounders. |
| UUW current dam & rainfall table | uMngeni-uThukela Water | https://umngeni-uthukela.co.za/rainfall-and-dam-data/ | Dam, date, volume Mm³, % full, outflow, rainfall mm, previous-year %; **Mgeni System** row | **Latest snapshot** on the public page (page also showed an older 2025-04-30 table in markup) | Appears daily/near-daily for latest | HTML | Human-readable current table. **Do not scrape** until UUW terms are confirmed in writing. | No clear open-data licence found on the page. Corporate site. Contact info@umgeniwater.co.za. | Cross-check latest DWS figures; documentation of UUW’s Mgeni System aggregate | Not a historical download. Two tables on the page can disagree in vintage. |
| UUW dam historical dashboard | UUW | http://umgenidata.eastus.cloudapp.azure.com/umgeni/Storage | Dam storage; “Latest” and “Last 5 Years” filters | About **5 years** if export works | Unclear (dashboard) | Unknown (likely interactive BI) | Register / log in. Confirm CSV export after approval. **Do not scrape.** | Login/register present. About page is a placeholder. Terms not clearly published. | Possible 5-year UUW series if they permit export | Azure hostname; availability unknown; 5 years **misses 2015–16 drought** if that is all that exists. Prefer DWS for history. |
| UUW Infrastructure Master Plan Vol. 2 | UUW | https://www.umngeni-uthukela.co.za/wp-content/uploads/2026/07/UUW_IMP_2026_Vol2_FINAL.pdf (also 2023 PDF on umgeni.co.za) | System description, operating rules, yields, WTW demands | Planning document, not a time series | n/a | PDF | Manual | UUW publication; cite the document | Domain documentation: which dams serve whom; pumping rules | Not observational data. |
| DWS KZN drought briefing | DWS | https://www.dws.gov.za/iwrp/KZN%20Recon/documents/SSC%209/7.1%20Angela%20Masefield.pdf | Monthly % for Mgeni dams Feb 2015–Feb 2016; restriction table | Feb 2015–Feb 2016 snapshots | Monthly (in slides) | PDF | Manual | DWS; academic citation | Sparse labels for 2015–16 drought; threshold research | Not a full series. |
| NASA POWER Daily (point) | NASA Langley POWER | https://power.larc.nasa.gov/api/temporal/daily/point and docs https://power.larc.nasa.gov/docs/services/api/temporal/daily/ | PRECTOTCORR (mm/day), T2M, T2M_MAX, T2M_MIN, RH2M; EVPTRNS / ET0 if offered for the AG community | Meteorology **1981-01-01 to near real time** (2–7 day lag) | Daily | JSON, CSV, ASCII, NetCDF | Public REST API; no auth. Max 20 parameters/point. | **CC BY 4.0**. Cite POWER project, product version, and date accessed. https://power.larc.nasa.gov/docs/referencing/ | Catchment weather: rainfall, temperature, humidity, evapotranspiration | **Grid (~0.5°), not a rain gauge.** Durban CBD ≠ Midmar catchment. Use inland catchment points, not only −29.86, 31.02. |
| CHIRPS rainfall (v3 preferred; v2 still online) | UCSB Climate Hazards Center / USGS | https://www.chc.ucsb.edu/data/chirps3 ; data https://data.chc.ucsb.edu/products/CHIRPS/v3.0/ ; v2 https://data.chc.ucsb.edu/products/CHIRPS-2.0/ | Precipitation (mm) | 1981 to near present | Pentad (native); daily derived; monthly | GeoTIFF, NetCDF, BIL, COG | Official FTP/HTTP/rsync. Prefer **Africa pentad or monthly**, not global daily. | CHIRPS: public domain / CC0-style waiver; CHIRPS3 also CC BY 4.0 language on product page. Cite CHC. | Catchment rainfall independent of NASA POWER; anomaly vs climatology | Large files if daily global is pulled. Preliminary vs final lag (final ~ third week of following month). Satellite–gauge blend, not a Durban gauge. |
| eThekwini Data Feeds (FEWS telemetry) | eThekwini Municipality | https://data.ethekwinifews.durban/ | Urban rainfall (5-min/hourly/daily), river level, weather stations, tides, waves | Near-real-time; historical depth **not verified** without API registration | Sub-daily to daily | Portal + API (registered users) | **Registered API only.** Terms **prohibit scraping** and overloading the API. | Research/education/non-commercial allowed with attribution: “Source: eThekwini Municipality Data Feeds Portal”. No commercial resale without permission. | Optional urban rainfall / river levels; **not** dam storage | Coastal/urban network, not Mgeni catchment dams. API keys, rate limits. Not an emergency-warning system (their own disclaimer). |
| EDGE open data — Water and Sanitation | eThekwini | https://edge.durban/dataset/ethekwini-water-and-sanitation | 2019/20 ward infrastructure counts, issues log, tanks | 2019/20 snapshot | One-off | XLS | Download | Creative Commons Attribution (portal) | Context only | **No time series of dam levels or restrictions.** Stale. |
| PWSeT / eThekwini Water Security dashboard | DWS / eThekwini | https://www.dws.gov.za/documents/2026-05%20PWSeT%20Dashboard.pdf and municipality copies | Narrative on 5 dams, 98% purchase from UUW, demand vs licence, 8% saving | Latest monthly PDF | Monthly PDF | PDF | Manual | Government publication | Problem framing; demand vs resource distinction | Not a modelling table. Interruptions are often **infrastructure**, not dam crisis. |
| SAWS station rainfall | South African Weather Service | https://www.weathersa.co.za/ | Gauge rainfall | Long, if purchased/approved | Daily | Proprietary | **Request** (e.g. info4@weathersa.co.za). Not open. Pilot/commercial APIs exist. | Not open access. Do not scrape. | Gold-standard gauges **if** a research licence is granted | Out of default scope until a licence is obtained. |

---

## 4. Overlap assessment (before download)

| Series | Overlap with others | Long enough for ≥5 years weekly? |
| --- | --- | --- |
| 5-dam Mgeni WSS volume | Limited by Spring Grove (2014) | **Yes, ~12 years (2014–2026)** if HyData downloads succeed — includes 2015–18 drought |
| 4-dam uMngeni river only | Limited by Inanda (1989) | Yes, ~37 years; incomplete system (no Spring Grove) |
| NASA POWER | 1981–present at catchment points | Yes |
| CHIRPS | 1981–present | Yes |
| UUW dashboard | ~5 years claimed | Yes for length, **no** for the drought if it starts ~2021 |
| eThekwini FEWS | Unknown | Unknown; optional |
| SAWS | Unknown without request | Do not depend on it |

**Preferred modelling window:** weekly, **2014-03-10 to latest verified DWS week**, so all five Mgeni WSS dams exist.  
**Sensitivity window:** 1989–present for the four uMngeni River dams.

NASA POWER and CHIRPS fully cover both windows.

---

## 5. Proposed joining strategy (for later phases; not implemented)

1. Download DWS daily reservoir **level** for U2R001, U2R003, U2R002, U2R004, V2R003.  
2. Convert level to volume using DWS FSC / capacity tables; compute **% of current FSC** and also keep volume (Mm³). Document FSC change dates.  
3. Aggregate to a **Monday-ending ISO week** (or DWS bulletin weekday — to be aligned after inspecting weekly PDF dates).  
4. Combined storage % = sum(volume) / sum(current FSC) × 100 for the five WSS dams.  
5. NASA POWER: daily point requests for at least three catchment locations (Midmar, Albert Falls, Inanda), **not** Durban CBD alone; sum precipitation to the same week; mean temperature.  
6. CHIRPS: extract pentad/monthly values for the same catchment bounding box; resample to weeks. Use as rainfall QA vs POWER.  
7. Features at week *t* use only data known at *t* (lags, cumulative rain, month, season).  
8. Target: `future_low_storage(t) = 1{ combined_%(t+4) < threshold }` with threshold default 70, configurable.  
9. Publication delay: verified HyData may end weeks/months before “today”. For the Streamlit demo, optionally append the latest DWS weekly bulletin as “unverified latest week”, flagged. Never use future rain.  
10. Chronological split only.

---

## 6. Access restrictions and quality problems (research pass)

- DWS HyData pages **timed out** intermittently on 2026-09-02. Scripts will need retries and timeouts.  
- DWS query limits: **7 000 primary records or 1 year**; **20 years of daily** per request. Midmar/Albert Falls/Spring Grove Point listings are 12-minute: a calendar-year request stops around day 58. Downloads therefore use monthly windows (and split the remainder if a month is still truncated). Sparse daily/weekly stations (Nagle, recent Inanda) can still use a longer window without hitting the cap.  
- No DWS public REST API for dam %; HyData is the official machine interface.  
- UUW public page is a **latest table**, not an archive. Dashboard may require registration; 5-year window likely misses the drought.  
- eThekwini FEWS **forbids scraping**. API is for registered users.  
- SAWS is **not open**.  
- NIWIS export is manual and about five years.  
- Storage % is not the same as “Durban has water”: eThekwini interruptions are often pipe bursts, non-revenue water, and over-abstraction, not empty dams (PWSeT dashboard).  
- Combined storage **hides** Albert Falls stress (2016–17: Inanda stayed high while Albert Falls fell below 40%).

---

## 7. Sources cited in this research (accessed 2 September 2026)

- DWS KZN weekly dams: https://www.dws.gov.za/Hydrology/Weekly/ProvinceWeek.aspx?region=KN  
- DWS weekly PDF: https://www.dws.gov.za/hydrology/Weekly/Weekly.pdf  
- DWS verified hydrology: https://www.dws.gov.za/hydrology/Verified/hymain.aspx  
- DWS WMA3 reservoir catalogue: https://www.dws.gov.za/Hydrology/Verified/dwafapp2_wma/WMA3_Pongola-Mtamvuna_Reservoir.pdf  
- DWS drought briefing: https://www.dws.gov.za/iwrp/KZN%20Recon/documents/SSC%209/7.1%20Angela%20Masefield.pdf  
- DWS NIWIS copyright note: https://www.dws.gov.za/niwis2/  
- WSKS copyright: https://ws.dws.gov.za/wsks/copyright.aspx  
- UUW rainfall and dam data: https://umngeni-uthukela.co.za/rainfall-and-dam-data/  
- UUW IMP 2026 Vol. 2: https://www.umngeni-uthukela.co.za/wp-content/uploads/2026/07/UUW_IMP_2026_Vol2_FINAL.pdf  
- DWS uMkhomazi summary: https://www.dws.gov.za/iwrp/uMkhomazi/Documents/Module%201/2/uMWP_Summary%20Report_Final.pdf  
- NASA POWER daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/  
- NASA POWER licence: CC BY 4.0; https://power.larc.nasa.gov/docs/referencing/  
- CHIRPS: https://www.chc.ucsb.edu/data/chirps3  
- eThekwini FEWS terms: https://data.ethekwinifews.durban/  
- EDGE water datasets: https://edge.durban/dataset/ethekwini-water-and-sanitation  
- PWSeT dashboard PDF: https://www.dws.gov.za/documents/2026-05%20PWSeT%20Dashboard.pdf  

---

## 8. Approval gate

**Do not download large files or write acquisition/training code until the proposed sources, target, and 70% academic threshold are approved.**
