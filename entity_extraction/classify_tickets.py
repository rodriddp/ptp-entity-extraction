import sys
from pathlib import Path
# Set sys.path to include the project root
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.snowAPI import get_tickets,filter_tickets,Region
from utils.openAI_cost import calculate_openai_cost
from utils.processing import post_process_extracted_text
from utils.load_env_vars import load_env_vars
from core import SnowTicket, SubcategoryClassifier
import json
import numpy as np
import pandas as pd
import os
import json
import time
import argparse
from datetime import datetime


def classify_tickets_by_subcategory(start_date, end_date,selected_regions,path_to_env_var, path_to_system_prompt):
    current_dir = os.getcwd()
    # Get api keys and other secrets
    load_env_vars(path_to_env_var)
    with open(path_to_system_prompt, "r", encoding="utf-8") as file:
        system_prompt = file.read()
    # create folder with results
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_folder_name = timestamp_str + "_run"
    results_path = os.path.join(current_dir,"data","outputs","ticket_classification",results_folder_name)
    os.makedirs(results_path, exist_ok=True)
    # TODO: for the implementation maybe need to add time-stamp when extracting from SNOW API or filter tickets with filter_tickets(tickets, field_key, field_value)
    tickets = get_tickets(start_date=start_date, end_date=end_date)
    print(f"\nCollected a total of {len(tickets)} Snow tickets across all markets between {start_date} and {end_date}\n")
    if selected_regions is not None:
        mapped_regions = [Region[r].value for r in selected_regions]
        tickets = filter_tickets(tickets, "u_region", mapped_regions)
        print(f"Filtered to a total of {len(tickets)} Snow tickets from the following markets: {selected_regions}\n")
    print(f"Start to classify {len(tickets)} Snow tickets:\n\n")
    # tickets = tickets[:10]
    subcategory_classifier = SubcategoryClassifier(system_prompt)
    metrics = {"ticket":[],"input_tokens":[], "output_tokens":[], "costs_gpt4o":[], "time_to_get_subcategory":[], "description":[], "assigned_subcategory":[],"selected_subcategory":[]}
    for i,ticket in enumerate(tickets):
        # create SnowTicket from ticket
        snow_ticket = SnowTicket(ticket,results_path)
        selected_subcategory = snow_ticket.ticket["u_subcategory"]
        print(f"Processing ticket number:{snow_ticket.ticket['number']}. Selected subcategory: {selected_subcategory}")
        start_time = time.time()
        # Download attachments, process attachments, convert attachments to text and combine with ticket description and title. (preprocess ticket)
        desc = snow_ticket.description
        assigned_subcategory, input_tokens, output_tokens = subcategory_classifier.get_subcategory(desc,few_shot=True)
        print(f"Predicted subcategory:{assigned_subcategory}")
        selected_subcategory = snow_ticket.ticket["u_subcategory"]
        time_to_get_subcategory = time.time() - start_time

        log = f"SYSTEM PROMPT: {system_prompt} \n DESCRIPTION: {desc} \n\n"
        log += f"ASSIGNED SUBCATEGORY: {assigned_subcategory}\nSELECTED SUBCATEGORY:{selected_subcategory}\n\n + INPUT TOKENS: {input_tokens}\n + OUTPUT TOKENS: {output_tokens}\n + TIME: {time_to_get_subcategory:.2f} seconds\n"
        
        cost_gpt4o = calculate_openai_cost(input_tokens, output_tokens, model="gpt-4o")

        # add metrics to dictionary
        metrics["ticket"].append(snow_ticket.ticket['number'])
        metrics["time_to_get_subcategory"].append(float(np.round(time_to_get_subcategory,2)))
        metrics["input_tokens"].append(input_tokens)
        metrics["output_tokens"].append(output_tokens)
        metrics["costs_gpt4o"].append(cost_gpt4o)
        metrics["description"].append(desc)
        metrics["assigned_subcategory"].append(assigned_subcategory)
        metrics["selected_subcategory"].append(selected_subcategory)

        # create directory for the ticket if it does not exist
        os.makedirs(snow_ticket.dir_att_path, exist_ok=True)
        # save the log file
        with open(snow_ticket.dir_att_path + "/" + "log.txt", "w", encoding="utf-8") as file:
            file.write(log)
        if i%5 == 0:
            print(f"\n{i+1} Tickets processed\n\n")
    # save metrics in excel
    metrics_df = pd.DataFrame(metrics)
    metrics_df_path = os.path.join(results_path,"metrics_" + timestamp_str + ".xlsx")
    metrics_df.to_excel(metrics_df_path,index = False)
    # save as well the parameters of the run as a json
    params = {
    "regions": selected_regions,
    "start_date": start_date,
    "end_date": end_date
    }
    params_path = os.path.join(results_path, f"parameters_{timestamp_str}.json")
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2, ensure_ascii=False)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a ServiceNow ticket.")

    # Required positional arguments
    parser.add_argument("start_date", help="time range start date for reading tickets")
    parser.add_argument("end_date", help="time range end date for reading tickets")

    parser.add_argument("--regions", nargs='+', default=None, help="Space separated regions. Pick between APAC, EMEA and AMERICAS. Example: --regions APAC EMEA")
    parser.add_argument("--path_to_env_var", default="data/inputs/secrets/secrets.txt", help="path to file with env variables for Azure Open AI")
    parser.add_argument("--path_to_system_prompt", default="data/inputs/system_prompts/subcategory_classifier_v2.txt", help="path to file for the system prompt of the entity extractor")


    args = parser.parse_args()
    classify_tickets_by_subcategory(start_date = args.start_date, end_date = args.end_date,selected_regions=args.regions, path_to_env_var = args.path_to_env_var, path_to_system_prompt = args.path_to_system_prompt)

# example how to run: ./.chatbot_env/Scripts/python.exe entity_extraction/classify_tickets.py "2025-05-01" "2025-06-01"
# example how to run if env activated: python entity_extraction/classify_tickets.py "2025-05-01" "2025-06-01"
                        # with region: python entity_extraction/classify_tickets.py "2025-05-01" "2025-06-01" --regions EMEA AMERICAS