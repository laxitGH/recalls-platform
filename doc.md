# Curium SWE assignment  
## OpenFDA Drug Recall Assistant using OpenAI Function Calling

This assignment asks you to build a small assistant that answers questions about FDA drug recalls using:

1. Live data from the OpenFDA Drug Enforcement (Recalls) API  
2. OpenAI function calling (tools)  
3. A simple UI interface (required)

Estimated time: 1–2 hours.

---

## Dataset: OpenFDA Drug Enforcement (Recalls)

Your assistant must fetch real recall data from:

https://api.fda.gov/drug/enforcement.json

Fields include:

- recall_number  
- classification  
- reason_for_recall  
- status  
- product_description  
- recall_initiation_date  
- firm_name  
- city, state  

Documentation: https://open.fda.gov/apis/drug/enforcement/

Required OpenFDA parameters:

- search=  
- limit=  
- skip=  
- count=

You do not need the full dataset; fetching a limited subset is fine.

---

## Requirements Overview

You must implement:

1. Two OpenAI function-calling tools  
2. OpenFDA integration for all tools

---

## Required Tools (Functions)

### 1. search_recalls

Inputs:
- query (optional string)  
- classification (optional string: "Class I", "Class II", "Class III")  
- limit (optional integer, default 10, max 50)

Output:
A list of normalized recall objects with fields such as:
- id (recall_number)  
- classification  
- productName  
- firmName  
- status  
- recallInitiationDate  
- state  


### 2. get_recall_stats

Output:
A summary statistics object. Suggested metrics:
- Total recall count  
- Recalls by classification  
- Top firms  
- Recalls by year  

---


## Small Web UI

 build a minimal webpage that:
- Accepts a question  
- Shows the final assistant answer
- (Optional) automatically generates a visualization for certain queries.  

Example questions:
- "What are recent reasons for Class II ibuprofen recalls?"  
- "Which firms have the most drug recalls?"  
- "How many Class I recalls occurred in 2020?"

---

## Suggested Project Structure

```
.
├── openfda/
│   ├── client.(ts|py)
│   └── transforms.(ts|py)
├── tools.(ts|py)
├── function_schemas.(ts|py)
├── main.(ts|py)
```

---

## Submission

Submission link:  https://forms.gle/usF3MNhdy2rKY96q9

Submit a GitHub repository and a quick 20-30 second demo video.

Feel free to use any AI tools you please (Cursor, Copilot ...)

## Final Notes

The goal is a small, focused implementation demonstrating:
- Function calling  
- External API integration  
- Clean code organization  

