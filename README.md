# FAKE DECT

A local review-text analysis website under reconstruction. The intended model estimates whether text resembles the computer-generated (CG) or original (OR) reviews in its training dataset. **It does not establish fraud or authenticity.**

## Current status

The original website, model, dataset and evaluation files were missing from this folder. The replacement includes a newly trained review-text model and an Amazon-link evidence checklist. Its held-out review-level accuracy is 94.71% on the included dataset; this is not an accuracy measurement for product authenticity. See [PROJECT_STATUS.md](PROJECT_STATUS.md) for verification and limitations.

## Setup

Install Python 3.11 or 3.12, then from the project directory install the backend dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

Provide a legally obtained CSV containing a `text_` (or `text`) column and a `label` column containing `CG` and `OR`. Train the model:

```bash
python backend/train.py backend/data/reviews.csv
```

Training writes a model and measured evaluation metadata to `backend/models/`. The script refuses to replace existing artifacts unless `--overwrite` is supplied. Back up existing artifacts before retraining. Only load joblib artifacts from sources you trust; deserializing a malicious artifact can execute code.

Start the server:

```bash
python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. Restart the server after training so it loads the new model. Until then, prediction requests return an error rather than a simulated result. The static frontend does not require Node.

Run the backend tests:

```bash
python -m unittest discover -s backend/tests -v
```

Thirteen backend tests passed, including mocked retrieval and model-routing cases. A live Amazon India request retrieved the title for one listing but exposed no review text. Review prediction, CSV export, and mobile layout have not been fully verified end to end.

## Amazon listing check

Paste a direct supported Amazon `/dp/<ASIN>` or `/gp/product/<ASIN>` HTTPS link. Shortened links are not supported. You can optionally enter listing details and your own seller-authorization check. The app attempts to retrieve a bounded public Amazon India listing; other marketplaces are not automatically fetched. It analyzes review text only if present in the returned page. Amazon may block access or omit reviews. User-supplied information is not verified, and the app cannot issue a counterfeit verdict. An optional review-text prediction is a separate writing-pattern estimate, not evidence that the product is genuine or fake. Listing checks are not saved in history; separate review analyses are saved locally.

## Dataset and limitations

The included CSV was downloaded from the [Fake-Reviews-Detection repository](https://github.com/SayamAlt/Fake-Reviews-Detection). Its SHA-256 is `ea03422988824bc917b5f7217e3867e27b597c647d5261adfae73cd7a85e1e1a`. The repository states CC BY 4.0 generally but does not establish the dataset's provenance; verify rights independently before reuse or redistribution. The model's training split is a random stratified review-level split; related or duplicated reviews can cross partitions. Performance on other products, languages and modern generators is unknown. The link checker extracts an ASIN and attempts to retrieve Amazon India product pages without bypassing access restrictions. No trained BiLSTM is included.

Submitted review text is stored locally in `backend/history.sqlite3`. The website has no authentication and is not suitable for public deployment without security and privacy controls.

Contributors:
Vatsal Agarwal
Vansh Saxena
