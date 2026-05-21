"""
Train the error-classification model used by the dashboard's
/api/classify_error endpoint.

Usage:
    python python_server/train_model.py

Reads:  python_server/dataset.csv
Writes: python_server/final_model.pkl
"""
import re

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


def preprocess_error_message(text: str) -> str:
    """Strip stack traces, file paths, line numbers; normalize whitespace."""
    text = text.split('\n')[0]
    text = re.sub(r' at line \d+', '', text)
    text = re.sub(r'[\w/]+\.java:\d+', '', text)
    text = text.lower().strip()
    return text


# Load dataset
df = pd.read_csv('dataset.csv', encoding='utf-8')

# Pre-process error messages
df['error_message'] = df['error_message'].apply(preprocess_error_message)

# Features + labels
X = df['error_message']
y = df['label']

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Pipeline
model = Pipeline([
    ('tfidf', TfidfVectorizer(lowercase=True, max_features=5000)),
    ('clf', LogisticRegression(max_iter=1000)),
])

# Train
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print("Model performance:")
print(classification_report(y_test, y_pred))

# Persist
joblib.dump(model, 'final_model.pkl')
print("Training complete. Model saved as final_model.pkl")
