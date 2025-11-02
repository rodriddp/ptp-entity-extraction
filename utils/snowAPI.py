import http.client
import json
import os
import re
import unicodedata
from enum import Enum

def sanitize_filename(filename, replacement="_"):
    """
    Removes invalid characters from a filename and replaces non-ASCII characters.
    """
    # Normalise Unicode characters to convert letters with accents to their base form
    # e.g. "á" -> "a", "ñ" -> "n"
    filename = unicodedata.normalize("NFKD", filename)

    # Replaces invalid characters for Windows (\/:*?"<>|) and non-alphanumeric characters except "_", "-" and "."
    filename = re.sub(r'[\/:*?"<>|]', replacement, filename)
    filename = re.sub(r"[^a-zA-Z0-9_.-]", replacement, filename)

    # Avoides that the filename ends with a space or dot
    filename = filename.rstrip(" .")

    return filename

def get_tickets(start_date, end_date):

    """Get tickets from Accounts Payable (AP) category and Invoice Payment Status subcategory created after between start_date (YYYY-MM-DD) and end_date (YYYY-MM-DD)"""
    # Get user_key for API
    USER_KEY =  os.environ["SNOW_API_KEY"]
    conn = http.client.HTTPSConnection("<vcc-api>")
    payload = ''
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Cookie': '<vcc-api-cookie>'
    }
    conn.request("GET", f"<vcc-endpoint-with{USER_KEY}+{start_date}+{end_date}>", payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    json_data = json.loads(data)["result"]
    return json_data

def get_attachments_from_ticket(ticket_sys_id:str):
    # Get user_key for API
    USER_KEY =  os.environ["SNOW_API_KEY"]
    conn = http.client.HTTPSConnection("<vcc-api>")
    payload = ''
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Cookie': '<vcc-api-cookie>'
    }
    conn.request("GET", f"<vcc-endpoint-with{USER_KEY}+{ticket_sys_id}>", payload, headers)
    res = conn.getresponse()
    data = res.read()
    data = json.loads(data.decode("utf-8"))["result"]
    system_ids_atts = [d["sys_id"] for d in data]
    file_names_atts = [d["file_name"] for d in data]
    return system_ids_atts, file_names_atts

def download_attachment_from_id(attachment_id:str, attachment_name:str, dir):

    # Get user_key for API
    USER_KEY =  os.environ["SNOW_API_KEY"]
    conn = http.client.HTTPSConnection("gw1.api.volvocars.biz")
    payload = ''
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Cookie': '<vcc-api-cookie>'
    }
    conn.request("GET", f"<vcc-endpoint-with{USER_KEY}+{attachment_id}>", payload, headers)
    res = conn.getresponse()
    data = res.read()
    sanitized_att_name = sanitize_filename(attachment_name)
    filename = dir + f"/{sanitized_att_name}"
    with open(filename, "wb") as file:
        file.write(data)
    return sanitized_att_name

def filter_tickets(tickets:list, filter_key:str, filter_values:list):
    filtered_tickets = [item for item in tickets if item[filter_key] in filter_values]
    return filtered_tickets

def return_ticket_refs(tickets:list):
    ticket_refs = [item["number"] for item in tickets]
    return ticket_refs

class Region(Enum):
    APAC = "APAC (Asia Pacific And China)"
    EMEA = "EMEA (Europe Middle East and Africa)"
    AMERICAS = "Americas (North and South America)"


