import sys
from pathlib import Path
# Set sys.path to include the project root
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.snowAPI import get_tickets,filter_tickets, Region
from utils.openAI_cost import calculate_openai_cost
from utils.processing import post_process_extracted_text
from utils.load_env_vars import load_env_vars
from entity_extraction.core import SnowTicket, EntityExtractor
import json
import numpy as np
import pandas as pd
import os
import json
import time
import argparse
from datetime import datetime


def extract_entities(start_date, end_date, selected_regions, path_to_env_var, path_to_system_prompt):
    current_dir = os.getcwd()
    # Get api keys and other secrets
    load_env_vars(path_to_env_var)
    with open(path_to_system_prompt, "r", encoding="utf-8") as file:
        system_prompt = file.read()
    # create folder with results
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_folder_name = timestamp_str + "_run"
    results_path = os.path.join(current_dir,"data","outputs","entity_extraction",results_folder_name)
    os.makedirs(results_path, exist_ok=True)
    # TODO: for the implementation maybe need to add time-stamp when extracting from SNOW API or filter tickets with filter_tickets(tickets, field_key, field_value)
    tickets = get_tickets(start_date=start_date, end_date=end_date)
    print(f"\nCollected a total of {len(tickets)} Snow tickets across all markets between {start_date} and {end_date}\n")
    if selected_regions is not None:
        mapped_regions = [Region[r].value for r in selected_regions]
        tickets = filter_tickets(tickets, "u_region", mapped_regions)
        print(f"Filtered to a total of {len(tickets)} Snow tickets from the following markets: {selected_regions}\n")
    print(f"Start to extract entities from {len(tickets)} Snow tickets:\n\n")
    # tickets = tickets[:10]
    entity_extractor = EntityExtractor(system_prompt)
    metrics = {"ticket":[],"input_tokens":[], "output_tokens":[], "time_to_ticket_to_text":[], "time_to_extract_entities":[], "costs_gpt4o":[], "error":[]}
    for i,ticket in enumerate(tickets):
        # create SnowTicket from ticket
        snow_ticket = SnowTicket(ticket,results_path)
        error = False
        print(f"Processing ticket number:{snow_ticket.ticket['number']}, from selected entity: {snow_ticket.vcc_entity}")
        start_time = time.time()
        # Download attachments, process attachments, convert attachments to text and combine with ticket description and title. (preprocess ticket)
        snow_ticket.to_llm_input()
        # Calculate time to preprocess ticket
        time_to_llm_input = time.time() - start_time
        time_to_process_attachments_str = str(time_to_llm_input//60) + " minutes " + str(time_to_llm_input%60) + " seconds"
        print(f"Attachments processed in: {time_to_process_attachments_str}")
        # Initialize log
        log = ""
        # extract entities from processed tickets. If input is larger than max_content, it might exceed token rate limit
        try:  
            extracted_text, input_tokens, output_tokens = entity_extractor.extract_entities(snow_ticket.processed_ticket)
        except Exception as e:
            extracted_text,input_tokens, output_tokens = "", 0 , 0
            log+="**ERROR: Token rate limit exceded**\n\n"
            print(f"ERROR extracting entities: {e}")
            error = True
        # calculate time spent in extracting entities
        time_to_extract_entities = time.time() - start_time - time_to_llm_input
        # post process extacted text:
        try:    
            extracted_text_post_processed = post_process_extracted_text(extracted_text, snow_ticket.vcc_entity)
        except Exception as e:
            extracted_text_post_processed = "**ERROR IN LLM OUTPUT FORMAT**\n"
            error = True
            # this error usually is because output is longer than max_output_tokens in EntityExtractor.extract_entities, so the output is truncated and the dictionary is never closed with }
        time_to_extract_entities_str = str(time_to_extract_entities//60) + " minutes " + str(time_to_extract_entities%60) + " seconds"
        print(f"Entities extracted in: {time_to_extract_entities_str}")
        # calculate cost
        cost_gpt4o = calculate_openai_cost(input_tokens, output_tokens, model="gpt-4o")
        # add metrics to dictionary
        metrics["ticket"].append(snow_ticket.ticket['number'])
        metrics["input_tokens"].append(input_tokens)
        metrics["output_tokens"].append(output_tokens)
        metrics["costs_gpt4o"].append(cost_gpt4o)
        metrics["time_to_ticket_to_text"].append(time_to_llm_input)
        metrics["time_to_extract_entities"].append(time_to_extract_entities)
        metrics["error"].append(error)

        # combine processed ticket + output
        log += "LLM_INPUT:\n" + snow_ticket.processed_ticket + "TICKET ENTITY:\n" + snow_ticket.vcc_entity + "\n\nLLM_OUTPUT\n" + extracted_text + "\n\nLLM_OUTPUT + ENTITY\n" + extracted_text_post_processed
        log += "\n\nINPUT_TOKENS:" + str(metrics["input_tokens"][i]) + "\nOUTPUT_TOKENS:" + str(metrics["output_tokens"][i])
        log += "\n\nTIME TO PROCESS TICKET: " + str(metrics["time_to_ticket_to_text"][i]) + "\nTIME TO EXTRACT ENTITIES: " + str(metrics["time_to_extract_entities"][i]) + "\n"
        log += "\n\n COSTS: " + "[" + str(metrics["costs_gpt4o"][i]) +"]"
        # create directory for the ticket if it does not exist
        os.makedirs(snow_ticket.dir_att_path, exist_ok=True)
        # save the log file
        with open(snow_ticket.dir_att_path + "/" + "log.txt", "w", encoding="utf-8") as file:
            file.write(log)
        # save the results
        with open(snow_ticket.dir_att_path + "/" + "extracted_entities.txt", "w", encoding="utf-8") as file:
            file.write(extracted_text_post_processed)
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
    parser.add_argument("--path_to_system_prompt", default="data/inputs/system_prompts/default_system_prompt_v6.txt", help="path to file for the system prompt of the entity extractor")


    args = parser.parse_args()
    extract_entities(start_date = args.start_date, end_date = args.end_date, selected_regions = args.regions, path_to_env_var = args.path_to_env_var, path_to_system_prompt = args.path_to_system_prompt)

# example how to run: ./.chatbot_env/Scripts/python.exe entity_extraction/extract_entities.py "2025-05-01" "2025-06-01"
# example how to run if env activated: python entity_extraction/extract_entities.py "2025-05-30" "2025-06-01" --regions AMERICAS EMEA