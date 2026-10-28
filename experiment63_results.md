# Experiment #63 — how good are professional forecasters? (2026-10-28 06:47 UTC)

## A Did the professionals see recessions coming? (SPF anxious index)
| recession starts | P(decline next quarter) said the quarter before | P(decline in 4 quarters) said a year before |
|---|--:|--:|
| 1970Q1 | 44 % | — |
| 1974Q1 | 47 % | 16 % |
| 1980Q2 | 51 % | 27 % |
| 1981Q4 | 35 % | 14 % |
| 1990Q4 | 42 % | 17 % |
| 2001Q2 | 32 % | 18 % |
| 2008Q1 | 23 % | 15 % |
| 2020Q1 | 18 % | 22 % |

Surveys 1968Q4–2026Q3: average P(decline next quarter) before a recession quarter 42 % vs other quarters 16 % (AUC 0.91; 0.5 = no skill, 1 = perfect). Recession STARTS flagged with ≥ 50 % the quarter before: **1 of 8**; false alarms (≥ 50 %, no recession next quarter): 5.

## B Unemployment 4 quarters ahead: professionals vs 'no change'
222 forecasts 1968Q4–2025Q2: error (RMSE) SPF 1.18 pt vs naive 'no change' 1.57 pt. Big rises (≥ 1 pt within ~5 quarters): 43; of those the professionals forecast a rise of ≥ 0.5 pt: **23**.

## C Stocks
### Professionals' 10-year stock return expectations (SPF STOCK10) vs reality
| survey | expected p.a. (next 10 y) | actual p.a. | error |
|---|--:|--:|--:|
| 1992Q1 | 10.0 % | +12.5 % | +2.5 pt |
| 1993Q1 | 9.0 % | +8.6 % | -0.4 pt |
| 1994Q1 | 10.0 % | +11.3 % | +1.3 pt |
| 1995Q1 | 8.2 % | +11.2 % | +3.0 pt |
| 1996Q1 | 9.0 % | +8.8 % | -0.2 pt |
| 1997Q1 | 9.0 % | +7.5 % | -1.5 pt |
| 1998Q1 | 9.0 % | +4.0 % | -5.0 pt |
| 1999Q1 | 8.0 % | -3.5 % | -11.5 pt |
| 2000Q1 | 8.0 % | -0.4 % | -8.4 pt |
| 2001Q1 | 7.5 % | +2.5 % | -5.0 pt |
| 2002Q1 | 7.0 % | +4.1 % | -2.9 pt |
| 2003Q1 | 8.0 % | +8.1 % | +0.1 pt |
| 2004Q1 | 7.8 % | +7.0 % | -0.7 pt |
| 2005Q1 | 7.0 % | +7.9 % | +0.9 pt |
| 2006Q1 | 7.0 % | +6.3 % | -0.7 pt |
| 2007Q1 | 7.5 % | +7.5 % | -0.0 pt |
| 2008Q1 | 6.5 % | +9.6 % | +3.1 pt |
| 2009Q1 | 6.5 % | +16.5 % | +10.0 pt |
| 2010Q1 | 7.0 % | +12.5 % | +5.5 pt |
| 2011Q1 | 7.2 % | +13.3 % | +6.0 pt |
| 2012Q1 | 6.8 % | +14.4 % | +7.6 pt |
| 2013Q1 | 6.1 % | +12.1 % | +6.0 pt |
| 2014Q1 | 6.0 % | +12.5 % | +6.5 pt |
| 2015Q1 | 5.5 % | +12.8 % | +7.4 pt |
| 2016Q1 | 5.4 % | +15.3 % | +10.0 pt |

25 surveys: expected avg 7.6 %/yr, actual avg 8.9 %/yr; average miss 4.2 pt/yr (a constant guess would miss 4.0 pt); correlation expected → actual **-0.32** (overlapping windows, few independent decades).

### Livingston Survey S&P forecasts (1952–1990)
Found in `medians.xlsx` sheet `SPIF`: columns SPIF_BP, SPIF_ZM, SPIF_6M, SPIF_12M, SPIF_BY, SPIF_ZY, SPIF_1Y, SPIF_2Y.
(Livingston asked for the S&P Industrials; the outcome uses the S&P 500 price index as a close proxy.)
67 half-yearly surveys 1992-06–2025-06: forecast 12-month change avg +5.8 %, actual avg +10.1 %; direction right **73 %** (always guessing 'up' would have been right 76 %); correlation forecast → actual -0.11.

### Professionals' recession worry as a stock signal
| professionals' recession worry (quintile) | S&P next 12 months | n |
|---|--:|--:|
| 1 (calmest) | +1.9 % | 46 |
| 2 | +11.9 % | 46 |
| 3 | +11.6 % | 45 |
| 4 | +7.0 % | 46 |
| 5 (most worried) | +13.7 % | 46 |
Correlation worry → next-12-month return: +0.16 (price only).

## D Private investors' mood (AAII)
AAII data not reachable (full history now members-only).

## Data discovery (what was found)
- https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/median-forecasts → 2 workbook links
- https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/mean-forecasts → 2 workbook links
- https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/anxious-index → 1 workbook links
- https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/probability-variables → 1 workbook links
- https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters → 2 workbook links
- https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/livingston-historical-data → 12 workbook links
- https://www.richmondfed.org/research/national_economy/cfo_survey/data_and_results → 2 workbook links
- https://www.aaii.com/files/surveys/sentiment.xls → ERROR <HTTPError 403: 'Forbidden'>
- `medianLevel.xlsx`: NGDP [YEAR, QUARTER, NGDP1, NGDP2, NGDP3, NGDP4, NGDP5, NGDP6, NGDPA, NGDPB] (232 rows); PGDP [YEAR, QUARTER, PGDP1, PGDP2, PGDP3, PGDP4, PGDP5, PGDP6, PGDPA, PGDPB] (232 rows); CPROF [YEAR, QUARTER, CPROF1, CPROF2, CPROF3, CPROF4, CPROF5, CPROF6, CPROFA, CPROFB] (232 rows); UNEMP [YEAR, QUARTER, UNEMP1, UNEMP2, UNEMP3, UNEMP4, UNEMP5, UNEMP6, UNEMPA, UNEMPB …] (232 rows); EMP [YEAR, QUARTER, EMP1, EMP2, EMP3, EMP4, EMP5, EMP6, EMPA, EMPB] (232 rows); INDPROD [YEAR, QUARTER, INDPROD1, INDPROD2, INDPROD3, INDPROD4, INDPROD5, INDPROD6, INDPRODA, INDPRODB] (232 rows); … 58 sheets
- `medianGrowth.xlsx`: NGDP [YEAR, QUARTER, dngdp2, dngdp3, dngdp4, dngdp5, dngdp6] (232 rows); PGDP [YEAR, QUARTER, dpgdp2, dpgdp3, dpgdp4, dpgdp5, dpgdp6] (232 rows); CPROF [YEAR, QUARTER, dcprof2, dcprof3, dcprof4, dcprof5, dcprof6] (232 rows); EMP_AVG [YEAR, QUARTER, dempa2, dempa3, dempa4, dempa5, dempa6] (232 rows); EMP_PCG [YEAR, QUARTER, dempb2, dempb3, dempb4, dempb5, dempb6] (232 rows); INDPROD [YEAR, QUARTER, dindprod2, dindprod3, dindprod4, dindprod5, dindprod6] (232 rows); … 13 sheets
- `meanLevel.xlsx`: NGDP [YEAR, QUARTER, NGDP1, NGDP2, NGDP3, NGDP4, NGDP5, NGDP6, NGDPA, NGDPB] (232 rows); PGDP [YEAR, QUARTER, PGDP1, PGDP2, PGDP3, PGDP4, PGDP5, PGDP6, PGDPA, PGDPB] (232 rows); CPROF [YEAR, QUARTER, CPROF1, CPROF2, CPROF3, CPROF4, CPROF5, CPROF6, CPROFA, CPROFB] (232 rows); UNEMP [YEAR, QUARTER, UNEMP1, UNEMP2, UNEMP3, UNEMP4, UNEMP5, UNEMP6, UNEMPA, UNEMPB …] (232 rows); EMP [YEAR, QUARTER, EMP1, EMP2, EMP3, EMP4, EMP5, EMP6, EMPA, EMPB] (232 rows); INDPROD [YEAR, QUARTER, INDPROD1, INDPROD2, INDPROD3, INDPROD4, INDPROD5, INDPROD6, INDPRODA, INDPRODB] (232 rows); … 58 sheets
- `meanGrowth.xlsx`: NGDP [YEAR, QUARTER, dngdp2, dngdp3, dngdp4, dngdp5, dngdp6] (232 rows); PGDP [YEAR, QUARTER, dpgdp2, dpgdp3, dpgdp4, dpgdp5, dpgdp6] (232 rows); CPROF [YEAR, QUARTER, dcprof2, dcprof3, dcprof4, dcprof5, dcprof6] (232 rows); EMP_AVG [YEAR, QUARTER, dempa2, dempa3, dempa4, dempa5, dempa6] (232 rows); EMP_PCG [YEAR, QUARTER, dempb2, dempb3, dempb4, dempb5, dempb6] (232 rows); INDPROD [YEAR, QUARTER, dindprod2, dindprod3, dindprod4, dindprod5, dindprod6] (232 rows); … 13 sheets
- `anxious_index_chart.xlsx`: Data [Obs Year, Obs Quarter, Anxious Index, RECESS, col4] (240 rows); Documentation [Anxious Index] (10 rows)
- `prob.xlsx`: PRGDP [YEAR, QUARTER, PRGDP1, PRGDP2, PRGDP3, PRGDP4, PRGDP5, PRGDP6, PRGDP7, PRGDP8 …] (232 rows); PRPGDP [YEAR, QUARTER, PRPGDP1, PRPGDP2, PRPGDP3, PRPGDP4, PRPGDP5, PRPGDP6, PRPGDP7, PRPGDP8 …] (232 rows); PRUNEMP [YEAR, QUARTER, PRUNEMP1, PRUNEMP2, PRUNEMP3, PRUNEMP4, PRUNEMP5, PRUNEMP6, PRUNEMP7, PRUNEMP8 …] (232 rows); PRCCPI [YEAR, QUARTER, PRCCPI1, PRCCPI2, PRCCPI3, PRCCPI4, PRCCPI5, PRCCPI6, PRCCPI7, PRCCPI8 …] (232 rows); PRCPCE [YEAR, QUARTER, PRCPCE1, PRCPCE2, PRCPCE3, PRCPCE4, PRCPCE5, PRCPCE6, PRCPCE7, PRCPCE8 …] (232 rows); RECESS [YEAR, QUARTER, RECESS1, RECESS2, RECESS3, RECESS4, RECESS5] (232 rows)
- `annual-historical-values-by-survey-date-selected-variables.xlsx`: Data [Annual Averages for the Year Before the Survey Year, col1, col2, col3] (141 rows)
- `survq212_special-questions.xls`: 
- `medians.xlsx`: RGDPX [Date, RGDPX_BP, RGDPX_ZM, RGDPX_6M, RGDPX_12M, RGDPX_BY, RGDPX_ZY, RGDPX_1Y, RGDPX_2Y, RGDPX_10Y] (161 rows); GDPX [Date, GDPX_BP, GDPX_ZM, GDPX_6M, GDPX_12M, GDPX_BY, GDPX_ZY, GDPX_1Y, GDPX_2Y] (161 rows); BFIX [Date, BFIX_BP, BFIX_ZM, BFIX_6M, BFIX_12M, BFIX_BY, BFIX_ZY, BFIX_1Y, BFIX_2Y] (161 rows); CPAT [Date, CPAT_BP, CPAT_ZM, CPAT_6M, CPAT_12M, CPAT_BY, CPAT_ZY, CPAT_1Y, CPAT_2Y] (161 rows); IP [Date, IP_BP, IP_ZM, IP_6M, IP_12M, IP_BY, IP_ZY, IP_1Y, IP_2Y] (161 rows); TPHS [Date, TPHS_BP, TPHS_ZM, TPHS_6M, TPHS_12M, TPHS_BY, TPHS_ZY, TPHS_1Y, TPHS_2Y] (161 rows); … 16 sheets
- `means.xlsx`: RGDPX [Date, RGDPX_BP, RGDPX_ZM, RGDPX_6M, RGDPX_12M, RGDPX_BY, RGDPX_ZY, RGDPX_1Y, RGDPX_2Y, RGDPX_10Y] (161 rows); GDPX [Date, GDPX_BP, GDPX_ZM, GDPX_6M, GDPX_12M, GDPX_BY, GDPX_ZY, GDPX_1Y, GDPX_2Y] (161 rows); BFIX [Date, BFIX_BP, BFIX_ZM, BFIX_6M, BFIX_12M, BFIX_BY, BFIX_ZY, BFIX_1Y, BFIX_2Y] (161 rows); CPAT [Date, CPAT_BP, CPAT_ZM, CPAT_6M, CPAT_12M, CPAT_BY, CPAT_ZY, CPAT_1Y, CPAT_2Y] (161 rows); IP [Date, IP_BP, IP_ZM, IP_6M, IP_12M, IP_BY, IP_ZY, IP_1Y, IP_2Y] (161 rows); TPHS [Date, TPHS_BP, TPHS_ZM, TPHS_6M, TPHS_12M, TPHS_BY, TPHS_ZY, TPHS_1Y, TPHS_2Y] (161 rows); … 16 sheets
- `individualdata.xlsx`: RGDPX [Date, ID, Category, RGDPX_BP, RGDPX_ZM, RGDPX_6M, RGDPX_12M, RGDPX_BY, RGDPX_ZY, RGDPX_1Y …] (7241 rows); GDPX [Date, ID, Category, GDPX_BP, GDPX_ZM, GDPX_6M, GDPX_12M, GDPX_BY, GDPX_ZY, GDPX_1Y …] (7241 rows); BFIX [Date, ID, Category, BFIX_BP, BFIX_ZM, BFIX_6M, BFIX_12M, BFIX_BY, BFIX_ZY, BFIX_1Y …] (7241 rows); CPAT [Date, ID, Category, CPAT_BP, CPAT_ZM, CPAT_6M, CPAT_12M, CPAT_BY, CPAT_ZY, CPAT_1Y …] (7241 rows); IP [Date, ID, Category, IP_BP, IP_ZM, IP_6M, IP_12M, IP_BY, IP_ZY, IP_1Y …] (7241 rows); TPHS [Date, ID, Category, TPHS_BP, TPHS_ZM, TPHS_6M, TPHS_12M, TPHS_BY, TPHS_ZY, TPHS_1Y …] (7241 rows); … 16 sheets
- `MedianGrowthRate.xlsx`: RGDPX [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); GDPX [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); BFIX [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); IP [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); PPI [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); CPI [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); … 7 sheets
- `MeanGrowthRate.xlsx`: RGDPX [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); GDPX [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); BFIX [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); IP [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); PPI [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); CPI [Date, G_BP_To_ZM, G_BP_To_6M, G_BP_To_12M, G_ZM_To_6M, G_ZM_To_12M, G_6M_To_12M, G_BY_To_ZY, G_BY_To_1Y, G_BY_To_2Y …] (161 rows); … 7 sheets
- `Dispersion1.xlsx`: GDPX [Measures of Cross-Sectional Dispersion for NOMINAL GROSS DOMESTIC PRODUCT (GDPX), col1, col2, col3, col4, col5, col6] (165 rows); CPAT [Measures of Cross-Sectional Dispersion for NOMINAL CORPORATE PROFITS AFTER TAXES (CPAT), col1, col2, col3, col4, col5, col6] (165 rows); TPHS [Measures of Cross-Sectional Dispersion for NEW PRIVATE HOUSING STARTS (TPHS), col1, col2, col3, col4, col5, col6] (165 rows); UNPR [Measures of Cross-Sectional Dispersion for CIVILIAN UNEMPLOYMENT RATE (UNPR), col1, col2, col3, col4, col5, col6] (165 rows); WMFG [Measures of Cross-Sectional Dispersion for AVERAGE WEEKLY EARNINGS (WMFG), col1, col2, col3, col4, col5, col6] (165 rows); RTTR [Measures of Cross-Sectional Dispersion for NOMINAL RETAIL SALES & FOOD SERVICES (RTTR), col1, col2, col3, col4, col5, col6] (165 rows); … 12 sheets
- `Dispersion2.xlsx`: RGDPX [Measures of Cross-Sectional Dispersion for REAL GROSS DOMESTIC PRODUCT (RGDPX), col1, col2, col3, col4, col5, col6, col7, col8, col9 …] (165 rows); GDPX [Measures of Cross-Sectional Dispersion for NOMINAL GROSS DOMESTIC PRODUCT (GDPX), col1, col2, col3, col4, col5, col6, col7, col8, col9 …] (165 rows); BFIX [Measures of Cross-Sectional Dispersion for REAL PRIVATE NON-RESIDENTIAL FIXED INVESTMENT (BFIX), col1, col2, col3, col4, col5, col6, col7, col8, col9 …] (165 rows); CPAT [Measures of Cross-Sectional Dispersion for NOMINAL CORPORATE PROFITS AFTER TAXES (CPAT), col1, col2, col3, col4, col5, col6, col7, col8, col9 …] (165 rows); IP [Measures of Cross-Sectional Dispersion for INDUSTRIAL PRODUCTION (IP), col1, col2, col3, col4, col5, col6, col7, col8, col9 …] (165 rows); TPHS [Measures of Cross-Sectional Dispersion for NEW PRIVATE HOUSING STARTS (TPHS), col1, col2, col3, col4, col5, col6, col7, col8, col9 …] (165 rows); … 12 sheets
- `Dispersion3.xlsx`: RGDPX [Measures of Cross-Sectional Dispersion for REAL GROSS DOMESTIC PRODUCT (RGDPX), col1, col2, col3, col4, col5, col6] (164 rows); GDPX [Measures of Cross-Sectional Dispersion for NOMINAL GROSS DOMESTIC PRODUCT (GDPX), col1, col2, col3, col4, col5, col6] (164 rows); BFIX [Measures of Cross-Sectional Dispersion for REAL PRIVATE NON-RESIDENTIAL FIXED INVESTMENT (BFIX), col1, col2, col3, col4, col5, col6] (164 rows); CPAT [Measures of Cross-Sectional Dispersion for NOMINAL CORPORATE PROFITS AFTER TAXES (CPAT), col1, col2, col3, col4, col5, col6] (164 rows); IP [Measures of Cross-Sectional Dispersion for INDUSTRIAL PRODUCTION (IP), col1, col2, col3, col4, col5, col6] (164 rows); TPHS [Measures of Cross-Sectional Dispersion for NEW PRIVATE HOUSING STARTS (TPHS), col1, col2, col3, col4, col5, col6] (164 rows); … 13 sheets
- `Alternative_Base_Values.xlsx`: Sheet1 [col0, BasePeriodAlt, col2] (112 rows)
- `SPI_Medians.xls`: 
- `SPI_Means.xls`: 
- `SPI_Raw.xls`: 
- `current_historical_cfo_data.xlsx`: CFO_optimism_all [year, quarter, economy_N, economy_mean, economy_median, ownfirm_N, ownfirm_mean, ownfirm_median] (26 rows); CFO_optimism_bysize [year, quarter, big, economy_N, economy_mean, economy_median, ownfirm_N, ownfirm_mean, ownfirm_median] (52 rows); CFO_optimism_byempcat [year, quarter, emp_cat, economy_N, economy_mean, economy_median, ownfirm_N, ownfirm_mean, ownfirm_median] (100 rows); CFO_optimism_bysector [year, quarter, naics1, economy_N, economy_mean, economy_median, ownfirm_N, ownfirm_mean, ownfirm_median] (125 rows); CFO_expectations [year, quarter, icat, exp1_N, exp1, exp1_med, exp2_N, exp2, exp2_med] (136 rows); CFO_expectations_byempcat [year, quarter, icat, emp_cat, exp1_N, exp1, exp1_med, exp2_N, exp2, exp2_med] (544 rows); … 23 sheets
- `special_questions.xlsx`: Special Questions Index [Topics ↓ | Dates →, TOTAL, Q2 2020, Q3 2020, Q4 2020, Q1 2021, Q2 2021, Q3 2021, Q4 2021, Q1 2022 …] (32 rows); Q3 2026 [Q3 2026 Special Questions, col1, col2, col3, col4, col5, col6, col7, Back to Index, col9 …] (60 rows); Q2 2026 [Q2 2026 Special Questions, col1, col2, col3, col4, col5, col6, col7, Back to Index, col9 …] (69 rows); Q1 2026 [Q1 2026 Special Questions, col1, col2, col3, col4, col5, col6, col7, Back to Index, col9 …] (54 rows); Q4 2025 [Q4 2025 Special Questions, col1, col2, col3, col4, col5, col6, col7, Back to Index, col9 …] (155 rows); Q3 2025 [Q3 2025 Special Questions, col1, col2, col3, col4, col5, col6, col7, Back to Index, col9 …] (48 rows); … 27 sheets