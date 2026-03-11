# train_model_class_weights.py
"""
TRAIN ML MODEL - USING CLASS WEIGHTS ONLY (No memory issues)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.utils.class_weight import compute_class_weight
import joblib
import os
import glob
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("TRAINING ML MODEL - USING CLASS WEIGHTS")
print("=" * 70)

# ============================================
# 1. LOAD YOUR DATABASE FILES
# ============================================

data_path = "data/raw/"
csv_files = glob.glob(os.path.join(data_path, "*.csv"))
print(f"\nFound {len(csv_files)} CSV files")

if len(csv_files) == 0:
    print("❌ No CSV files found!")
    exit(1)

df_list = []
for file in csv_files:
    print(f"Loading: {os.path.basename(file)}")
    df = pd.read_csv(file)
    df_list.append(df)

df = pd.concat(df_list, ignore_index=True)
print(f"\n✅ Total records: {len(df)}")

# ============================================
# 2. FIND LABEL COLUMN
# ============================================

print("\n" + "=" * 70)
print("FINDING LABEL COLUMN")
print("=" * 70)

all_columns = df.columns.tolist()
print(f"First 10 columns: {all_columns[:10]}")

# Try to find label column
label_column = None
for col in all_columns:
    col_lower = col.lower().strip()
    if 'label' in col_lower or 'class' in col_lower or 'attack' in col_lower:
        label_column = col
        break

if label_column is None:
    print("\nCould not find label column automatically.")
    print("Enter the exact column name (e.g., ' Label' with space):")
    label_column = input("Label column: ").strip()

print(f"\n✅ Using label column: '{label_column}'")

# ============================================
# 3. CHECK CLASS DISTRIBUTION
# ============================================

print("\n" + "=" * 70)
print("CLASS DISTRIBUTION")
print("=" * 70)

y = df[label_column]
class_counts = y.value_counts()
print(class_counts)

print(f"\nTotal classes: {len(class_counts)}")
print(f"Majority class: '{class_counts.index[0]}' with {class_counts.iloc[0]} samples")
print(f"Minority class: '{class_counts.index[-1]}' with {class_counts.iloc[-1]} samples")
print(f"Imbalance ratio: {class_counts.iloc[0] / class_counts.iloc[-1]:.1f}:1")

# ============================================
# 4. PREPARE FEATURES
# ============================================

print("\n" + "=" * 70)
print("PREPARING FEATURES")
print("=" * 70)

# Separate features and labels
X = df.drop([label_column], axis=1)
y_raw = df[label_column]

# Clean column names (remove extra spaces)
X.columns = X.columns.str.strip()
print(f"Original features shape: {X.shape}")

# Handle infinite values
X = X.replace([np.inf, -np.inf], np.nan)

# Convert to numeric (coerce errors to NaN)
for col in X.columns:
    if X[col].dtype == 'object':
        X[col] = pd.to_numeric(X[col], errors='coerce')

# Fill NaN with median (more robust than mean)
X = X.fillna(X.median())

# Drop columns that are all NaN or constant
X = X.dropna(axis=1, how='all')
X = X.loc[:, X.std() > 0]  # Drop constant columns

print(f"Final features shape: {X.shape}")
print(f"Number of features: {X.shape[1]}")

# ============================================
# 5. ENCODE LABELS
# ============================================

print("\n" + "=" * 70)
print("ENCODING LABELS")
print("=" * 70)

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y_raw)

print(f"Encoded {len(label_encoder.classes_)} classes:")
for i, class_name in enumerate(label_encoder.classes_):
    count = sum(y_encoded == i)
    percentage = count / len(y_encoded) * 100
    print(f"  {i:2d}: '{class_name[:30]}' - {count:6d} samples ({percentage:5.1f}%)")

# ============================================
# 6. TRAIN/TEST SPLIT
# ============================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

print(f"\nTraining set: {X_train.shape[0]:,} samples")
print(f"Test set: {X_test.shape[0]:,} samples")

# ============================================
# 7. SCALE FEATURES
# ============================================

print("\n" + "=" * 70)
print("SCALING FEATURES")
print("=" * 70)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("✅ Features scaled (mean=0, std=1)")

# ============================================
# 8. COMPUTE CLASS WEIGHTS (KEY FIX!)
# ============================================

print("\n" + "=" * 70)
print("COMPUTING CLASS WEIGHTS")
print("=" * 70)

# Get unique classes
classes = np.unique(y_train)

# Compute balanced class weights
class_weights = compute_class_weight(
    class_weight='balanced',
    classes=classes,
    y=y_train
)

# Convert to dictionary format RandomForest expects
class_weight_dict = {cls: weight for cls, weight in zip(classes, class_weights)}

print("Class weights (higher weight = more important):")
for cls, weight in zip(classes, class_weights):
    class_name = label_encoder.inverse_transform([cls])[0]
    count = np.sum(y_train == cls)
    print(f"  {class_name[:30]:30} | Count: {count:6d} | Weight: {weight:8.3f}")

# ============================================
# 9. TRAIN RANDOM FOREST WITH CLASS WEIGHTS
# ============================================

print("\n" + "=" * 70)
print("TRAINING RANDOM FOREST WITH CLASS WEIGHTS")
print("=" * 70)

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=20,
    min_samples_split=5,
    min_samples_leaf=2,
    class_weight=class_weight_dict,  # Use computed weights
    random_state=42,
    n_jobs=-1,
    verbose=0
)

print("Training model (this may take a few minutes)...")
model.fit(X_train_scaled, y_train)

# ============================================
# 10. EVALUATE ON TEST SET
# ============================================

print("\n" + "=" * 70)
print("EVALUATING MODEL")
print("=" * 70)

y_pred = model.predict(X_test_scaled)
y_proba = model.predict_proba(X_test_scaled)

# Classification report
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

# Check if model predicts multiple classes
unique_preds = np.unique(y_pred)
print(f"\n✅ Model predicts {len(unique_preds)} different classes")
print(f"   Predicted classes: {[label_encoder.inverse_transform([p])[0][:20] for p in unique_preds]}")

# Confidence analysis
confidences = np.max(y_proba, axis=1)
print(f"\nConfidence statistics:")
print(f"  Mean confidence: {confidences.mean():.3f}")
print(f"  Std confidence:  {confidences.std():.3f}")
print(f"  Min confidence:  {confidences.min():.3f}")
print(f"  Max confidence:  {confidences.max():.3f}")

# ============================================
# 11. TEST ON RANDOM SAMPLES
# ============================================

print("\n" + "=" * 70)
print("TESTING ON RANDOM SAMPLES")
print("=" * 70)

# Test on 10 random samples
indices = np.random.choice(len(X_test), min(10, len(X_test)), replace=False)

for i, idx in enumerate(indices):
    sample = X_test_scaled[idx].reshape(1, -1)
    true_label = label_encoder.inverse_transform([y_test[idx]])[0]
    
    pred = model.predict(sample)[0]
    proba = model.predict_proba(sample)[0]
    confidence = np.max(proba)
    pred_label = label_encoder.inverse_transform([pred])[0]
    
    print(f"\nSample {i+1}:")
    print(f"  True: {true_label[:30]}")
    print(f"  Pred: {pred_label[:30]} (confidence: {confidence:.1%})")
    
    # Show top 3 predictions
    top_3_idx = np.argsort(proba)[-3:][::-1]
    print("  Top 3 predictions:")
    for tidx in top_3_idx:
        tlabel = label_encoder.inverse_transform([tidx])[0]
        print(f"    → {tlabel[:30]}: {proba[tidx]:.1%}")

# ============================================
# 12. SAVE MODEL AND PREPROCESSORS
# ============================================

print("\n" + "=" * 70)
print("SAVING MODEL")
print("=" * 70)

os.makedirs("models", exist_ok=True)

# Save model
model_path = "models/ids_model_class_weights.pkl"
joblib.dump(model, model_path)
print(f"✅ Model saved to: {model_path}")

# Save label encoder
encoder_path = "models/label_encoder_class_weights.pkl"
joblib.dump(label_encoder, encoder_path)
print(f"✅ Label encoder saved to: {encoder_path}")

# Save feature names
feature_names_path = "models/feature_names_class_weights.pkl"
joblib.dump(X.columns.tolist(), feature_names_path)
print(f"✅ Feature names saved to: {feature_names_path}")

# Save scaler
scaler_path = "models/scaler_class_weights.pkl"
joblib.dump(scaler, scaler_path)
print(f"✅ Scaler saved to: {scaler_path}")

# Save class weights info
weights_info = {
    'classes': label_encoder.classes_.tolist(),
    'weights': class_weights.tolist()
}
joblib.dump(weights_info, "models/class_weights_info.pkl")

print("\n" + "=" * 70)
print("✅ TRAINING COMPLETE!")
print("=" * 70)
print(f"\nModel saved with {X.shape[1]} features")
print(f"Can detect {len(label_encoder.classes_)} attack types")
print(f"Class weights applied - minority classes now have higher importance")
print("\nNext step: Run live_detector_class_weights.py")