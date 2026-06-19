import pandas as pd, warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('data/results.csv', low_memory=False)
n_rows, n_cols = df.shape

NUM = {
    'WorkExp':             'Work experience (yrs)',
    'YearsCode':           'Years coding',
    'ConvertedCompYearly': 'Annual comp (USD)',
    'JobSat':              'Job satisfaction (1-10)',
    'ToolCountWork':       'Tools at work',
    'ToolCountPersonal':   'Tools (personal)',
}
CAT = {
    'MainBranch':    'Main professional branch',
    'Age':           'Age group',
    'EdLevel':       'Education level',
    'Employment':    'Employment status',
    'RemoteWork':    'Remote-work arrangement',
    'ICorPM':        'IC vs. People Manager',
    'DevType':       'Developer type',
    'OrgSize':       'Organisation size',
    'Industry':      'Industry',
    'Country':       'Country',
    'AISelect':      'AI tool usage frequency',
    'AISent':        'Sentiment toward AI',
    'AIAcc':         'AI trust / accuracy',
    'AIComplex':     'AI on complex tasks',
    'AIAgents':      'AI agents usage',
    'AIAgentChange': 'AI agents impact on work',
    'AIThreat':      'Perceived AI job threat',
}

num_rows_a, num_rows_b = [], []
for col, lbl in NUM.items():
    if col not in df.columns:
        continue
    s = pd.to_numeric(df[col], errors='coerce').dropna()
    miss = n_rows - len(s)
    num_rows_a.append((lbl, f'{len(s):,}', f'{miss:,}', f'{miss/n_rows*100:.1f}%'))
    num_rows_b.append((lbl, f'{s.mean():,.1f}', f'{s.median():,.1f}', f'{s.std():,.1f}',
                       f'{s.min():,.1f}', f'{s.quantile(.25):,.1f}',
                       f'{s.quantile(.75):,.1f}', f'{s.max():,.1f}'))

cat_data = {}
for col, lbl in CAT.items():
    if col not in df.columns:
        continue
    s  = df[col].dropna()
    vc = s.value_counts()
    miss = n_rows - len(s)
    top_n = 15 if col == 'Country' else 10
    rows  = [(val, f'{cnt:,}', f'{cnt/n_rows*100:.1f}%') for val, cnt in vc.head(top_n).items()]
    extra = max(0, len(vc) - top_n)
    cat_data[lbl] = {'n': len(s), 'miss': miss, 'rows': rows, 'extra': extra}

lines = []
lines.append('# Descriptive Statistics Report')
lines.append('**Stack Overflow Annual Developer Survey 2025**  ')
lines.append(f'Total responses: {n_rows:,} | Total variables: {n_cols} | Source: survey.stackoverflow.co')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## 1. Continuous Variables')
lines.append('')
lines.append('### 1a. Sample Size and Missing Data')
lines.append('')
lines.append('| Variable | N (valid) | Missing | Missing % |')
lines.append('|---|---:|---:|---:|')
for r in num_rows_a:
    lines.append(f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} |')
lines.append('')
lines.append('### 1b. Distributional Statistics')
lines.append('')
lines.append('| Variable | Mean | Median | Std Dev | Min | Q1 | Q3 | Max |')
lines.append('|---|---:|---:|---:|---:|---:|---:|---:|')
for r in num_rows_b:
    lines.append(f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |')
lines.append('')
lines.append('> **Note:** Compensation missing rate is high (51%) because only employed respondents answered.')
lines.append('> Tool counts and compensation have extreme outliers — medians are more informative than means.')
lines.append('')
lines.append('---')
lines.append('')
lines.append('## 2. Categorical Variables')
lines.append('')

for lbl, info in cat_data.items():
    miss_pct = f"{info['miss'] / n_rows * 100:.1f}%"
    n_valid  = f"{info['n']:,}"
    n_miss   = f"{info['miss']:,}"
    lines.append(f'### {lbl}')
    lines.append(f'*n = {n_valid} | missing = {n_miss} ({miss_pct})*')
    lines.append('')
    lines.append('| Category | Count | % |')
    lines.append('|---|---:|---:|')
    for row in info['rows']:
        lines.append(f'| {row[0]} | {row[1]} | {row[2]} |')
    if info['extra'] > 0:
        lines.append(f'| *+ {info["extra"]} more categories* | — | — |')
    lines.append('')
    lines.append('---')
    lines.append('')

out_path = r'C:\Users\User\Desktop\ai-for-research\descriptive_statistics.md'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'Saved -> {out_path}')
