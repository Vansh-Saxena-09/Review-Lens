# Review Lens – Fake Review Detection

Review Lens is a website that checks reviews and predicts whether they are Computer-Generated (CG) or Original (OR).

**Note:** It only checks writing patterns. It cannot prove whether a review or product is fake or real.

## Project Status

The old website, model, and dataset were missing. A new model and Amazon product link checker have been added.

The model achieved **94.71% accuracy** on the test dataset.

This score is only for review the checking, not product checking.

## Setup

**Step 1: Install Python**

Install Python 3.11 or 3.12.

**Step 2: Install Libraries**

```bash
python -m pip install -r backend/requirements.txt
```

**Step 3: Add Dataset**

Use a CSV file with two columns:
- `text_` or `text` – Review text.
- `label` – CG or OR.

**Step 4: Train the Model**

```bash
python backend/train.py backend/data/reviews.csv
```

The model will be saved in `backend/models/`.

**Step 5: Start the Website**

```bash
python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open: https://review-lens-udz4.onrender.com

**Step 6: Test the Backend**

```bash
python -m unittest discover -s backend/tests -v
```

All 13 backend tests passed. Some website features still need testing.

## Amazon Product Check

Users can paste a direct Amazon product link.

The website tries to get product details and reviews.

- Only direct Amazon HTTPS links are supported.
- Only Amazon India pages are checked.
- Amazon may block access or hide reviews.
- Product details entered by users are not verified.
- The website cannot confirm if a product is real or fake.

## Dataset Details

The dataset was downloaded from:

[Fake Reviews Detection – GitHub](https://github.com/SayamAlt/Fake-Reviews-Detection)

Its usage rights should be checked before sharing or reusing it.

## Limitations

- Similar reviews may appear in training and testing data.
- Results may differ on other datasets.
- Different languages may affect accuracy.
- AI-generated reviews may be harder to detect.
- No trained BiLSTM model is included.

## Data Storage

Review history is saved locally in:

`backend/history.sqlite3`

The website has no login system. Extra security is needed before public use.

## Conclusion

Review Lens uses machine learning to check whether reviews look computer-generated or original. It also checks Amazon product links.

It helps users understand review patterns, but its results are only predictions, not proof.
