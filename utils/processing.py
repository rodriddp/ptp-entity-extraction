import pytesseract
import re
import json
import pandas as pd	
from pdf2image import convert_from_path
from docx import Document
from langdetect import detect
from PIL import Image

# TODO: When using pyteseract OCR, can include part of code to detect angle of the image, sometimes horizontal picture, so need to rotate 90º or 270º. Can be easily implemented with python
def detect_image_script(image) -> tuple:
    """Detects the script used in the image via Tesseract's OSD."""
    try:
        osd = pytesseract.image_to_osd(image)
        script = re.search("Script: ([a-zA-Z]+)\n", osd).group(1)
        conf = float(re.search("Script confidence: (\d+\.?(\d+)?)", osd).group(1))
        return script, conf
    except Exception:
        return None, 0.0

def detect_top_scripts(image, top_n=2):
    """Detects the top scripts in the image using Tesseract OSD."""
    try:
        osd = pytesseract.image_to_osd(image)
        
        # Extract script(s) and confidence(s)
        script_matches = re.findall(r"Script: ([a-zA-Z]+)\nScript confidence: (\d+\.?\d*)", osd)
        
        # Convert to (script, confidence) tuples
        scripts_conf = [(script, float(conf)) for script, conf in script_matches]
        
        # Sort scripts by confidence in descending order and return the top N
        top_scripts = sorted(scripts_conf, key=lambda x: x[1], reverse=True)[:top_n]

        return top_scripts, osd
    except Exception:
        return [], None

def detect_text_language(text) -> str:
    """Detects the language of the extracted text using langdetect."""
    try:
        return detect(text)  # Returns language code (e.g., 'en', 'fr', 'ru', etc.)
    except:
        return "unknown"

# TODO: Detect multiple languages and return list of languages

def image2text(image: Image) -> str:
    """Extracts text from an image using Tesseract OCR."""
    # Step 1: Detect script
    script, conf = detect_image_script(image)
        
    # Step 2: Map script to OCR language
    script_to_lang = {
        "Latin": "eng", "Cyrillic": "rus", "Arabic": "ara", "Devanagari": "hin",
        "Greek": "ell", "Hebrew": "heb", "Hangul": "kor", "Han": "chi_sim",
        "Katakana": "jpn", "Tamil": "tam", "Bengali": "ben", "Thai": "tha"
    }
    ocr_lang = script_to_lang.get(script, "eng")  # Default to English if script unknown
    if ocr_lang == "eng":
        ocr_lang += "+chi_sim"
    if ocr_lang != "eng":
        ocr_lang += "+eng"

    # Step 3: Perform OCR with detected script's language
    extracted_text = pytesseract.image_to_string(image, lang=ocr_lang)
    
    # Step 4: Detect final language of text
    detected_lang = detect_text_language(extracted_text)
    if detected_lang == "eng":
        detected_lang += "+chi_sim"
    if detected_lang != "eng":
        detected_lang += "+eng"
    # Step 5: Perform OCR with final detected language
    final_extracted_text = pytesseract.image_to_string(image, lang=detected_lang)
    # print(f"Script: {script} (Confidence: {conf}) -> OCR Lang: {ocr_lang} -> Detected Lang: {detected_lang}")
    return final_extracted_text


def pdf2text(file_path: str) -> str:
    """Extracts text from a PDF with automated script & language detection."""
    text = ""
    images = convert_from_path(file_path)

    for img in images:
        text += image2text(img) + "\n"

    return text

def word_to_text(file_path: str) -> str:
    """Extracts text from a Word document."""
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def detect_table(df):
    """
    Detects the table header dynamically and removes summary rows.
    Returns the cleaned DataFrame.
    """
    # Step 1: Detect header row (first row with at least 50% non-empty values)
    for i, row in df.iterrows():
        non_null_count = row.count()  # Count non-null values
        total_count = len(row)
        if non_null_count / total_count > 0.5:  # At least 50% non-empty
            header_row = i
            break

    # Step 2: Extract table from header onward
    detected_table = df.iloc[header_row:].reset_index(drop=True)

    # Step 3: Set first row as header
    detected_table.columns = detected_table.iloc[0]
    detected_table = detected_table[1:].reset_index(drop=True)

    # Step 4: Remove summary rows (rows with >50% NaN values)
    detected_table = detected_table.dropna(thresh=len(detected_table.columns) * 0.5)

    return detected_table

def tabular_to_text(file_path) -> str:
    """
    Reads an Excel or CSV file, detects the table, removes summary rows, 
    and converts it into a JSON string.
    """
    # Read CSV or Excel file
    if file_path.lower().endswith(".csv"):
        df = pd.read_csv(file_path, header=None)
    else:
        df = pd.read_excel(file_path, engine="pyxlsb" if file_path.endswith(".xlsb") else None,header=None)

    # Detect and clean the table
    df = detect_table(df)

    # Convert DataFrame to dictionary
    data_dict = df.to_dict(orient="records")  # List of dictionaries (row-wise)

    # Convert dictionary to JSON string --> can fail for instance if date in header TODO: fix
    json_str = json.dumps(data_dict, indent=4, ensure_ascii=False, default=str)
    return json_str

def post_process_extracted_text(text, vcc_entity):
    # Convert JSON-like string to a Python dictionary
    text = json.loads(text.replace("(", "[").replace(")", "]"))

    # Use a set to track unique rows
    unique_invoices = set()

    # Process invoices
    cleaned_invoices = []
    for invoice in text['invoices']:
        invoice = list(invoice)  # Convert tuple to list for modification

        # Remove row if invoice[0] is NaN
        if invoice[0] == 'NaN':
            continue

        # Replace invoice[2] with vcc_entity if it's NaN
        if invoice[2] == 'NaN':
            invoice[2] = vcc_entity

        # Add the original invoice if it's unique
        invoice_tuple = tuple(invoice)
        if invoice_tuple not in unique_invoices:
            unique_invoices.add(invoice_tuple)
            cleaned_invoices.append(invoice_tuple)

        # If invoice[2] is not vcc_entity, add a new modified row
        # this way we ensure to have invoices with the entity provided by supplier and with the entity detected in attachments
        if invoice[2] != vcc_entity:
            modified_invoice = (invoice[0], invoice[1], vcc_entity)
            if modified_invoice not in unique_invoices:
                unique_invoices.add(modified_invoice)
                cleaned_invoices.append(modified_invoice)

    # Update the dictionary with cleaned invoices
    text['invoices'] = cleaned_invoices
    #return str(text)
    return json.dumps(text, indent=4, ensure_ascii=False)

