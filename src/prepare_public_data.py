import hashlib
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/public_emails.csv"
OUTPUT = ROOT / "data/processed/public_v1"
OUTPUT.mkdir(parents=True, exist_ok=True)

MAX_CHARACTERS = 50_000
SEED = 42

df = pd.read_csv(SOURCE)
original_rows = len(df)

# Preserve original source row numbers for traceability.
df["source_row"] = df.index

df = df.rename(columns={
    "Email Text": "text",
    "Email Type": "source_label",
})

label_map = {
    "Safe Email": "legitimate",
    "Phishing Email": "phishing",
}

if not df["source_label"].isin(label_map).all():
    raise ValueError("Missing or unexpected source labels found.")

df["label"] = df["source_label"].map(label_map)

# Normalise whitespace. Retain case in the saved text.
df["text"] = (
    df["text"].fillna("").astype(str)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

empty = df["text"].eq("")
removed_empty = int(empty.sum())
df = df.loc[~empty].copy()

# Identify duplicates without treating case differences as unique.
df["text_id"] = df["text"].str.lower().map(
    lambda text: hashlib.sha256(text.encode("utf-8")).hexdigest()
)

# Remove every copy of any text with conflicting source labels.
label_counts = df.groupby("text_id")["label"].nunique()
conflicting_ids = label_counts[label_counts > 1].index
conflicting = df["text_id"].isin(conflicting_ids)
removed_conflicting = int(conflicting.sum())
df = df.loc[~conflicting].copy()

# Exclude oversized records rather than silently truncating them.
too_long = df["text"].str.len() > MAX_CHARACTERS
removed_long = int(too_long.sum())
df = df.loc[~too_long].copy()

before_deduplication = len(df)
df = df.drop_duplicates("text_id").copy()
removed_duplicates = before_deduplication - len(df)

columns = ["text_id", "source_row", "text", "source_label", "label"]
df = df[columns]

train, remaining = train_test_split(
    df,
    test_size=0.30,
    stratify=df["label"],
    random_state=SEED,
)

validation, test = train_test_split(
    remaining,
    test_size=0.50,
    stratify=remaining["label"],
    random_state=SEED,
)

splits = {
    "train": train,
    "validation": validation,
    "test": test,
}

# Check that normalised identical texts cannot cross splits.
assert set(train["text_id"]).isdisjoint(validation["text_id"])
assert set(train["text_id"]).isdisjoint(test["text_id"])
assert set(validation["text_id"]).isdisjoint(test["text_id"])

summary = {
    "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "original_rows": original_rows,
    "removed_empty": removed_empty,
    "removed_conflicting_rows": removed_conflicting,
    "removed_oversized_rows": removed_long,
    "removed_duplicate_rows": removed_duplicates,
    "retained_rows": len(df),
    "max_characters": MAX_CHARACTERS,
    "random_seed": SEED,
    "limitation": (
        "Source labels retained without independent verification. "
        "Normalised exact duplicates removed; near-duplicates and "
        "related email threads may remain."
    ),
    "splits": {},
}

for name, split in splits.items():
    split.to_csv(OUTPUT / f"{name}.csv", index=False)
    summary["splits"][name] = {
        "rows": len(split),
        "labels": {
            label: int(count)
            for label, count in split["label"].value_counts().items()
        },
    }

with open(OUTPUT / "preparation_summary.json", "w") as file:
    json.dump(summary, file, indent=2)

print(json.dumps(summary, indent=2))
print("\nSaved prepared data to:", OUTPUT)
print("Passed: no normalised exact-text overlap between splits.")
