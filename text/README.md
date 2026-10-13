# Part 5 — Text Analyst

## Overview

This folder contains the implementation for **Part 5 — Text Analyst** in the Multimodal Crime / Incident Report Analyzer project.

The goal of this component is to process unstructured text data from social media and news-style crime reports, apply Natural Language Processing (NLP) methods, and convert the raw text into structured incident information that can be used by the final integration and dashboard component.

## Dataset

The dataset used for this part is the Kaggle **CrimeReport** dataset:

* Dataset name: CrimeReport
* Kaggle dataset ID: `cameliasiadat/crimereport`
* Download method: Kaggle API
* Local input file: `text/data/CrimeReport (1).txt`

Although the assignment description refers to a CSV file, the actual downloaded Kaggle file is a JSON Lines `.txt` file. Each line is one JSON record containing a social/news post, including fields such as:

* `text`
* `created_at`
* `source`
* `place`
* `user`
* `id`

The raw dataset file is stored locally in `text/data/`, but this folder is ignored by Git because raw downloaded datasets should not be pushed to GitHub.

## Tools and Models Used

This component uses the following tools:

* `pandas` for loading JSON Lines data and generating CSV outputs
* `spaCy` for Named Entity Recognition (NER)
* `en_core_web_sm` as the spaCy English language model
* `transformers` from HuggingFace for NLP model pipelines
* `torch` as the backend for transformer models
* `NLTK` for supporting text preprocessing resources
* `scikit-learn` as a supporting machine learning package

The main AI/NLP methods used are:

1. **Text cleaning and preprocessing**

   * Removes URLs
   * Removes user mentions
   * Removes hashtag symbols
   * Normalizes whitespace
   * Tokenizes cleaned text with NLTK
   * Removes common English stopwords during tokenization
   * Preserves the original raw text for final reporting


2. **Named Entity Recognition**

   * Extracts people, locations, organizations, facilities, and dates
   * Entity labels include `PERSON`, `GPE`, `LOC`, `FAC`, `ORG`, and `DATE`

3. **Sentiment Analysis**

   * Uses a HuggingFace sentiment-analysis pipeline
   * Produces sentiment labels such as `Negative`, `Positive`, or `Neutral`

4. **Topic Classification**

   * Uses a HuggingFace zero-shot classification pipeline
   * Classifies each text record into incident-related topics such as:

     * Shooting
     * Theft / Robbery
     * Assault
     * Fire
     * Accident
     * Drug Crime
     * Public Disturbance
     * Police Activity
     * Legal / Court
     * Other

## Folder Structure

```text
text/
├── README.md
├── data/
│   └── CrimeReport (1).txt
├── notebooks/
├── outputs/
│   ├── .gitkeep
│   ├── part5_text_analysis_output.csv
│   └── part5_text_integration_output.csv
└── src/
    └── text_analyzer.py
```

## How to Run

From the project root directory, activate the virtual environment first:

Install the required Python packages for this component:

```bash
python -m pip install -r text\requirements.txt
python -m spacy download en_core_web_sm

```bash
.venv\Scripts\activate
```

Then run the Part 5 text analysis script:

```bash
python text\src\text_analyzer.py
```

For a quick test with only five records, run:

```bash
python text\src\text_analyzer.py --limit 5
```

To view the command-line options:

```bash
python text\src\text_analyzer.py --help
```

## Outputs

This component generates two CSV files.

### 1. Part 5 Text Analysis Output

File:

```text
text/outputs/part5_text_analysis_output.csv
```

Columns:

```text
Text_ID, Source, Raw_Text, Sentiment, Entities, Topic
```

This output directly satisfies the Part 5 Text Analyst requirement. It shows the cleaned NLP results for each text record.

### 2. Team Integration Output

File:

```text
text/outputs/part5_text_integration_output.csv
```

Columns:

```text
Incident_ID, Event_Type, Source_Type, Date_Time, Location, Confidence_Score, Summary
```

This output follows the shared team integration format.

The `Incident_ID` uses the common team format:

```text
INC-2026-004000
INC-2026-004001
INC-2026-004002
```

The `Source_Type` field is always set to:

```text
Text
```

This allows the integration lead to merge this output with the audio, document, image, and video outputs using a consistent schema.

## Local Test Results

The full dataset was processed successfully.

Final output validation results:

```text
Text analysis shape: (115, 6)
Integration shape: (115, 7)
Full Part 5 output checks passed.
```

Topic classification summary:

```text
Police Activity       97
Legal / Court          6
Other                  5
Public Disturbance     3
Shooting               2
Theft / Robbery        2
```

Sentiment analysis summary:

```text
Negative    101
Positive     14
```

## Challenges and Solutions

### Challenge 1: Dataset format mismatch

The assignment instructions describe the dataset as a CSV file, but the actual downloaded file from Kaggle is a JSON Lines `.txt` file.

Solution:

The script uses:

```python
pd.read_json(input_path, lines=True)
```

instead of `pd.read_csv()`.

### Challenge 2: Raw social media text is noisy

The text contains URLs, hashtags, user mentions, and HTML-style source fields.

Solution:

The script cleans the text by removing URLs, mentions, extra hashtag symbols, and extra whitespace. It also converts HTML-style source fields into readable source names.

### Challenge 3: Missing entities

Some text records do not contain clear named entities.

Solution:

If no entity is detected, the output uses:

```text
No entities found
```

instead of leaving the field blank. This avoids missing values during integration.

### Challenge 4: Shared integration format

The individual Part 5 output format is different from the final team integration format.

Solution:

The script generates two outputs:

* one CSV for Part 5 text analysis
* one CSV using the team’s shared integration schema

This makes the component useful both as an individual NLP analysis module and as a clean input for the final dashboard or query system.

## Summary

The Part 5 Text Analyst component successfully converts unstructured crime-related social/news text into structured incident information. It applies text preprocessing, Named Entity Recognition, sentiment analysis, and topic classification, then exports results in both the required Part 5 format and the shared team integration format.
