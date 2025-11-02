# 🧾 PTP Ticket Entity Extraction

This repository enables automated **entity extraction from ServiceNow (SNOW) tickets** using **LLMs (Azure OpenAI)**, specifically designed to extract invoice-related fields such as vendor code, invoice numbers, PO numbers, etc.

---

## 🧠 What It Does

Given a date range (and optional region filters), this tool:

1. **Retrieves all SNOW tickets** between `start_date` and `end_date`.
2. Optionally filters them by region: `APAC`, `EMEA`, or `AMERICAS`.
3. **Processes each ticket** sequentially:
   - Downloads and converts attachments to text.
   - Combines that with the ticket description and subject.
4. Feeds the content into a custom **LLM agent (`EntityExtractor`)** with a configurable system prompt.
5. Returns extracted entities in a structured JSON format.
6. Applies post-processing logic.
7. Saves results to a timestamped run folder with full logs, metrics, and parameters used.

---

### 🧾 Example Output (per ticket)

```json
{
  "vendor_code": "XXXXXX",
  "vendor_name": "XXXXXXX",
  "invoices": [
    ["XXXXXXX", "2025", "Volvo Cars Sweden Sales Company"]
  ],
  "po_numbers": ["XXXXXXX"],
  "delivery_notes": []
}
```

---

## 📁 Output Folder Structure

Each run creates a folder like `2025-07-06_143022_run` with the following layout:

```
2025-07-06_143022_run/
│
├── ticket_1/
│   ├── attachment_1.pdf
│   ├── attachment_2.png
│   ├── log.txt
│   └── extracted_entities.txt
│
├── ticket_2/
│   └── ...
│
├── parameters_2025-07-06_143022.json     ← stores run configuration (dates, regions, prompt)
├── metrics.xlsx                          ← execution cost, time, token usage, etc.
```

---

## 🏷️ Optional: Subcategory Classification

The `SubcategoryClassifier` can be used to classify tickets into categories (e.g., `Invoice Payment Status`) based on the supplier's description. This is useful to pre-filter relevant tickets before extraction.

---

## ⚙️ Setup Instructions

### 1. Clone & Setup Environment

> You need **Python 3.12+**

```bash
# From root of ptp-entity-extraction
sh utils/env_setup/environment.sh
```

📌 _Note: Setup may take ~10 min. Consider removing unused heavy packages (e.g., transformers, tiktoken) from `requirements.txt`._

### 2. Add API Keys

Go to `data/inputs/secrets/secrets.txt` and fill in:

```
SNOW_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_MODEL=gpt-4o
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

---

## 🚀 How to Run

### 1. Activate the environment

```bash
source .ptp-entity-extraction/Scripts/activate  # Windows (Git Bash)
# OR
source .ptp-entity-extraction/bin/activate      # macOS/Linux
```

---

### 2. Run Entity Extraction

#### a) For all tickets between two dates:

```bash
python entity_extraction/extract_entities.py "2025-05-29" "2025-06-01"
```

#### b) For specific regions (EMEA and APAC):

```bash
python entity_extraction/extract_entities.py "2025-05-29" "2025-06-01" --regions EMEA APAC
```

---

### 3. Run Subcategory Classification

#### a) For all tickets:

```bash
python entity_extraction/classify_tickets.py "2025-05-29" "2025-06-01"
```

#### b) For EMEA and APAC:

```bash
python entity_extraction/classify_tickets.py "2025-05-29" "2025-06-01" --regions EMEA APAC
```

---

## 🛠️ Modify System Prompts

You can customize the behavior of the LLM by modifying system prompts. These are stored in `data/inputs/system_prompts`.

#### Example: change prompt used

```bash
python entity_extraction/extract_entities.py "2025-05-29" "2025-06-01" \
  --regions EMEA APAC \
  --path_to_system_prompt data/inputs/system_prompts/new_system_prompt.txt
```

This allows you to change:
- Output format
- Entities to extract (e.g., add “ship to” field)
- Prompt wording or style

## 📎 Relevant Links and resources

- 🔐 [AI Committee Case Submission](placeholder) 

- 📊 [Steering Committee Checkpoint Presentation](placeholder)  

- 📖 [Guideline for create Azure Open AI services](placeholder)

- 🤖 [Azure Open AI Service](placeholder)
