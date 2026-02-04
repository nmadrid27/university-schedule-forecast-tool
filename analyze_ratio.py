import pandas as pd

# Load data
df = pd.read_csv('Data/FOUN_Historical.csv')

# Combine SUBJ and CRS NUMBER
df['course_code'] = df['SUBJ'] + " " + df['CRS NUMBER'].astype(str)

# Group by Course and Term
course_term = df.groupby(['course_code', 'TERM'])['ACT ENR'].sum().reset_index()

# Find years
years = df['TERM'].astype(str).str[:4].unique()

ratios = []

for course in course_term['course_code'].unique():
    ct = course_term[course_term['course_code'] == course].set_index('TERM')['ACT ENR']
    
    course_ratios = []
    for year in years:
        spring_term = int(f"{year}30")
        summer_term = int(f"{year}40")
        
        if spring_term in ct.index and summer_term in ct.index:
            spring_enr = ct[spring_term]
            summer_enr = ct[summer_term]
            if spring_enr > 0:
                ratio = summer_enr / spring_enr
                course_ratios.append(ratio)
    
    if course_ratios:
        avg_ratio = sum(course_ratios) / len(course_ratios)
        ratios.append({'course': course, 'avg_ratio': avg_ratio, 'count': len(course_ratios)})

df_ratios = pd.DataFrame(ratios).sort_values('avg_ratio', ascending=False)
print(df_ratios)
