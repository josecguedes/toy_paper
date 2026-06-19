"""
Research question: Among professional developers, is reported AI-tool adoption
associated with reported job satisfaction, controlling for years of professional
experience and primary developer role?

Outputs:
  paper/figures/fig1_satisfaction_by_ai_use.pdf
  paper/figures/fig2_years_experience.pdf
  results_table.csv
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT     = Path(__file__).resolve().parent.parent
DATA     = ROOT / "data" / "results.csv"
FIG_DIR  = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Load and filter
# ---------------------------------------------------------------------------
df = pd.read_csv(DATA, low_memory=False)
print(f"Raw data: {df.shape[0]:,} rows × {df.shape[1]} columns")

# Keep professional developers only
df = df[df["MainBranch"] == "I am a developer by profession"].copy()
print(f"Professional developers: {len(df):,}")

# ---------------------------------------------------------------------------
# Variable construction
# ---------------------------------------------------------------------------

# AI use — ordered categories
AI_ORDER = [
    "No, and I don't plan to",
    "No, but I plan to soon",
    "Yes, I use AI tools monthly or infrequently",
    "Yes, I use AI tools weekly",
    "Yes, I use AI tools daily",
]
AI_SHORT = {
    "No, and I don't plan to":                    "No\n(won't)",
    "No, but I plan to soon":                     "No\n(soon)",
    "Yes, I use AI tools monthly or infrequently":"Monthly/\ninfreq.",
    "Yes, I use AI tools weekly":                 "Weekly",
    "Yes, I use AI tools daily":                  "Daily",
}
AI_ORDINAL = {v: i for i, v in enumerate(AI_ORDER)}

df["ai_label"]   = df["AISelect"].map(AI_SHORT)
df["ai_ordinal"] = df["AISelect"].map(AI_ORDINAL)
df["uses_ai"]    = df["ai_ordinal"].apply(lambda x: 1 if x >= 2 else 0 if pd.notna(x) else np.nan)

# Job satisfaction (1–10)
df["job_sat"] = pd.to_numeric(df["JobSat"], errors="coerce")

# Professional work experience (years)
df["work_exp"] = pd.to_numeric(df["WorkExp"], errors="coerce")

# Primary developer role: take first listed value
df["dev_role"] = df["DevType"].str.split(";").str[0].str.strip()

# ---------------------------------------------------------------------------
# Analysis sample
# ---------------------------------------------------------------------------
KEEP = ["job_sat", "ai_ordinal", "uses_ai", "ai_label", "work_exp", "dev_role"]
df_a = df[KEEP].dropna(subset=["job_sat", "ai_ordinal", "work_exp", "dev_role"]).copy()
print(f"Analysis sample (complete cases): {len(df_a):,}")

# Keep only roles with ≥50 respondents (needed for stable FE estimation)
role_counts = df_a["dev_role"].value_counts()
keep_roles  = role_counts[role_counts >= 50].index
df_a = df_a[df_a["dev_role"].isin(keep_roles)].copy()
print(f"After role-frequency filter (>=50 per role): {len(df_a):,}")

# ---------------------------------------------------------------------------
# Descriptive stats: satisfaction by AI use
# ---------------------------------------------------------------------------
sat_by_ai = (
    df_a.groupby("ai_label")["job_sat"]
    .agg(n="count", mean="mean", median="median", std="std")
    .reset_index()
)
# Sort by ordinal
label_to_ord = {AI_SHORT[k]: v for k, v in AI_ORDINAL.items()}
sat_by_ai["_ord"] = sat_by_ai["ai_label"].map(label_to_ord)
sat_by_ai = sat_by_ai.sort_values("_ord").drop(columns="_ord")
sat_by_ai["se"] = sat_by_ai["std"] / np.sqrt(sat_by_ai["n"])

print("\nSatisfaction by AI use:")
print(sat_by_ai.to_string(index=False))

# ---------------------------------------------------------------------------
# Regressions
# ---------------------------------------------------------------------------

# Model 1: bivariate
m1 = smf.ols("job_sat ~ uses_ai", data=df_a).fit()

# Model 2: add work experience (linear + quadratic)
m2 = smf.ols("job_sat ~ uses_ai + work_exp + I(work_exp**2)", data=df_a).fit()

# Model 3: add role fixed effects
m3 = smf.ols("job_sat ~ uses_ai + work_exp + I(work_exp**2) + C(dev_role)",
              data=df_a).fit()

# Model 4: ordinal AI use (robustness)
m4 = smf.ols("job_sat ~ ai_ordinal + work_exp + I(work_exp**2) + C(dev_role)",
              data=df_a).fit()

def extract(model, var):
    coef = model.params[var]
    se   = model.bse[var]
    pval = model.pvalues[var]
    ci_lo, ci_hi = model.conf_int().loc[var]
    return coef, se, pval, ci_lo, ci_hi

rows = []
for label, model, var in [
    ("M1: bivariate",           m1, "uses_ai"),
    ("M2: + experience",        m2, "uses_ai"),
    ("M3: + role FE (binary)",  m3, "uses_ai"),
    ("M4: + role FE (ordinal)", m4, "ai_ordinal"),
]:
    coef, se, pval, ci_lo, ci_hi = extract(model, var)
    rows.append({
        "model":    label,
        "variable": var,
        "coef":     round(coef,  4),
        "se":       round(se,    4),
        "pval":     round(pval,  4),
        "ci_lo":    round(ci_lo, 4),
        "ci_hi":    round(ci_hi, 4),
        "n":        int(model.nobs),
        "r2":       round(model.rsquared, 4),
    })

results = pd.DataFrame(rows)
results.to_csv(ROOT / "results_table.csv", index=False)
print("\nRegression results:")
print(results.to_string(index=False))

# Convenience extracts for LaTeX
m3_coef  = results.loc[results.model.str.startswith("M3"), "coef"].values[0]
m3_se    = results.loc[results.model.str.startswith("M3"), "se"].values[0]
m3_pval  = results.loc[results.model.str.startswith("M3"), "pval"].values[0]
m3_n     = results.loc[results.model.str.startswith("M3"), "n"].values[0]
m3_r2    = results.loc[results.model.str.startswith("M3"), "r2"].values[0]
m4_coef  = results.loc[results.model.str.startswith("M4"), "coef"].values[0]
m4_se    = results.loc[results.model.str.startswith("M4"), "se"].values[0]
m4_pval  = results.loc[results.model.str.startswith("M4"), "pval"].values[0]

pval_str = lambda p: f"{p:.3f}" if p >= 0.001 else "<0.001"

print(f"\nKey numbers for LaTeX:")
print(f"  Analysis sample n = {len(df_a):,}")
print(f"  M3 uses_ai coef = {m3_coef:+.3f}  SE={m3_se:.3f}  p={pval_str(m3_pval)}")
print(f"  M4 ai_ordinal coef = {m4_coef:+.3f}  SE={m4_se:.3f}  p={pval_str(m4_pval)}")

# Satisfaction means for No vs Daily
sat_no    = sat_by_ai.loc[sat_by_ai["ai_label"] == "No\n(won't)", "mean"].values
sat_daily = sat_by_ai.loc[sat_by_ai["ai_label"] == "Daily",       "mean"].values
if len(sat_no) and len(sat_daily):
    print(f"  Mean sat (no AI):    {sat_no[0]:.2f}")
    print(f"  Mean sat (daily AI): {sat_daily[0]:.2f}")

# Work experience descriptives
print(f"  Median work exp: {df_a['work_exp'].median():.0f} yrs")
print(f"  Mean work exp:   {df_a['work_exp'].mean():.1f} yrs")

# ---------------------------------------------------------------------------
# Figure 1 — satisfaction by AI use (bar + error bars)
# ---------------------------------------------------------------------------
PALETTE = ["#C0392B", "#E67E22", "#F1C40F", "#27AE60", "#1A5276"]

fig, ax = plt.subplots(figsize=(7, 4.2))
x     = np.arange(len(sat_by_ai))
bars  = ax.bar(x, sat_by_ai["mean"], color=PALETTE, width=0.55,
               edgecolor="white", linewidth=0.8)
ax.errorbar(x, sat_by_ai["mean"], yerr=1.96 * sat_by_ai["se"],
            fmt="none", color="#2C3E50", capsize=4, linewidth=1.2)

ax.set_xticks(x)
ax.set_xticklabels(sat_by_ai["ai_label"], fontsize=9)
ax.set_ylabel("Mean job satisfaction (1–10)", fontsize=10)
ax.set_title("Self-reported job satisfaction by AI-tool use frequency\n"
             "(professional developers, SO Survey 2025)",
             fontsize=10, pad=8)
ax.set_ylim(0, 10)
ax.yaxis.grid(True, linestyle="--", alpha=0.5)
ax.set_axisbelow(True)

for bar, row in zip(bars, sat_by_ai.itertuples()):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
            f"{row.mean:.2f}\n(n={row.n:,})", ha="center", va="bottom",
            fontsize=7.5, color="#2C3E50")

ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig1_satisfaction_by_ai_use.pdf", bbox_inches="tight")
fig.savefig(FIG_DIR / "fig1_satisfaction_by_ai_use.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("\nSaved fig1")

# ---------------------------------------------------------------------------
# Figure 2 — distribution of years of professional experience
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.5, 4))
exp_cap = df_a["work_exp"].clip(upper=40)
ax.hist(exp_cap, bins=30, color="#2E75B6", edgecolor="white",
        linewidth=0.6, alpha=0.85)
ax.axvline(df_a["work_exp"].median(), color="#C0392B", linewidth=1.8,
           linestyle="--", label=f"Median = {df_a['work_exp'].median():.0f} yrs")
ax.set_xlabel("Years of professional work experience (capped at 40)", fontsize=10)
ax.set_ylabel("Number of respondents", fontsize=10)
ax.set_title("Distribution of professional work experience\n"
             "(analysis sample, SO Survey 2025)",
             fontsize=10, pad=8)
ax.legend(fontsize=9)
ax.yaxis.grid(True, linestyle="--", alpha=0.5)
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig2_years_experience.pdf", bbox_inches="tight")
fig.savefig(FIG_DIR / "fig2_years_experience.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved fig2")

print("\nDone. All outputs written.")
