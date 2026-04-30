import random
import pandas as pd

rows = []
for i in range(600):
    age = random.randint(18, 80)
    income = random.randint(20000, 180000)
    schemes_taken = random.randint(0, 12)
    fraud = 1 if (income < 40000 and schemes_taken > 5) or random.random() < 0.18 else 0
    rows.append({
        'age': age,
        'income': income,
        'schemes_taken': schemes_taken,
        'fraud_predicted': fraud,
    })

pd.DataFrame(rows).to_csv('fraud_output.csv', index=False)
print('Generated fraud_output.csv with', len(rows), 'rows')
