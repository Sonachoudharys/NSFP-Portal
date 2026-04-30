import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
import joblib
from PIL import Image, ImageDraw, ImageFont

# Train on generated dataset
print('Loading dataset...')
df = pd.read_csv('fraud_output.csv')
X = df[['age', 'income', 'schemes_taken']]

print('Training IsolationForest...')
model = IsolationForest(n_estimators=200, contamination=0.2, max_samples='auto', random_state=42, n_jobs=-1)
model.fit(X)
joblib.dump(model, 'fraud_model.pkl')
print('Saved fraud_model.pkl')

# Create placeholder charts if matplotlib is unavailable
for name in ['confusion_matrix.png', 'accuracy_chart.png']:
    path = f'static/{name}'
    img = Image.new('RGB', (900, 540), color=(18, 29, 51))
    draw = ImageDraw.Draw(img)
    text = name.replace('_', ' ').replace('.png', '').title()
    try:
        font = ImageFont.truetype('arial.ttf', 36)
    except IOError:
        font = ImageFont.load_default()
    try:
        w, h = draw.textsize(text, font=font)
    except AttributeError:
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((900-w)/2, (540-h)/2), text, fill=(255, 255, 255), font=font)
    img.save(path)
    print(f'Created placeholder {path}')
