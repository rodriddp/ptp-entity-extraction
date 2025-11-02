from utils.snowAPI import get_attachments_from_ticket, download_attachment_from_id
from utils.processing import pdf2text, image2text, word_to_text, tabular_to_text
import os
import json
from openai import AzureOpenAI

class SubcategoryClassifier:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.chat_history = [{"role": "system", "content": self.system_prompt}]
        self.model = os.environ["AZURE_OPENAI_DEPLOYMENT"] 
        self.api_version = os.environ["AZURE_OPENAI_API_VERSION"]
        self.api_key = os.environ["AZURE_OPENAI_API_KEY"]
        self.endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.initialize_client()

    def initialize_client(self):
        self.client = AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
        )

    def get_subcategory(self, desc: str, few_shot = False, max_output_tokens: int = 256, add_to_history: bool = False, max_input_tokens:int = 65536 ) -> tuple[str, int, int]:

        if few_shot:
            input_data = [
             {"role": "system", "content": self.system_prompt},
             {"role": "user", "content": f"Ticket description: {desc}\nYour response:" }
            ]
        
        else:
            input_data = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": desc}
                ]
        
        response = self.client.chat.completions.create(
            messages=input_data,
            max_tokens=max_output_tokens,
            temperature=1.0,
            top_p=0.9,
            model=self.model
        )
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        assigned_subcategory = response.choices[0].message.content.strip()
        if add_to_history:
            self.chat_history.append({"role": "user", "content": desc})
            self.chat_history.append({"role": "assistant", "content": assigned_subcategory})

        return assigned_subcategory, input_tokens, output_tokens
    
class EntityExtractor:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.chat_history = [{"role": "system", "content": self.system_prompt}]
        self.model = os.environ["AZURE_OPENAI_DEPLOYMENT"] 
        self.api_version = os.environ["AZURE_OPENAI_API_VERSION"]
        self.api_key = os.environ["AZURE_OPENAI_API_KEY"]
        self.endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.initialize_client()

    def initialize_client(self):
        self.client = AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
        )
        
    def extract_entities(self, processed_ticket: str, max_output_tokens: int = 2048, add_to_history: bool = False,  max_input_tokens:int = 65536) -> tuple[str, int, int]:
        # TODO: Truncate input to max_input tokens --> need to use tiktoken tokenizer
        # TODO: Maybe change the temperature to 1 to make it deterministic "less creative", every time select most probable token

        # Format and build input from system prompt + formatted ticket
        input_data = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": processed_ticket}
        ]

        # generate text by providing the input and the deployed model we want to use
        response = self.client.chat.completions.create(
            messages=input_data,
            max_tokens=max_output_tokens,
            temperature=1.0,
            top_p=0.9,
            model=self.model
        )
        # count number of input and output tokens
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        # extract entities from the output
        extracted_entities = response.choices[0].message.content.strip()

        # by default we don't want to add to history, not relevant information of previous ticket to the next ticket
        if add_to_history:
            self.chat_history.append({"role": "user", "content": processed_ticket})
            self.chat_history.append({"role": "assistant", "content": extracted_entities})

        return extracted_entities, input_tokens, output_tokens
    
    def print_current_history(self):
        print(json.dumps(self.chat_history, indent=2))
    def clean_current_history(self):
        self.chat_history = [{"role": "system","content": self.system_prompt}]

class SnowTicket:

    def __init__(self, input_ticket:dict, dir_to_att:str="data/outputs/entity_extaction"):
        self.ticket = input_ticket
        self.dir_att_path = dir_to_att + "/" + self.ticket['number']
        self.description = self.ticket['short_description'] + "\n" + self.ticket['description'] + "\n\n"
        self.vendor_code = self.ticket['u_vendor_id']
        self.vcc_entity = self.ticket["u_type_of_entity"] + " " + self.ticket['u_entity']  + " " + self.ticket['u_subentity']
        self.attachment_ids = []
        self.attachment_names = []
        self.sanitized_att_names = []
        self.str_attachments = ""
        self.processed_ticket = ""

    def __str__(self):
        "Representation when printing"
        return f"{self.ticket}"
    def __repr__(self):
        "Representation in lists or debugging"
        return f"SnowTicket({self.ticket['number']})"   

    def get_attachment_ids(self):
        # returns attachment ids + attachment names
        attachment_ids, attachment_names = get_attachments_from_ticket(self.ticket['sys_id'])
        return attachment_ids, attachment_names
    
    def download_attachments(self):
        # Create folder with ticket name if it does not exist
        if not os.path.exists(self.dir_att_path):
            os.makedirs(self.dir_att_path)
        self.sanitized_att_names = []
        # download attachments
        for attachment_id, attachment_name in zip(self.attachment_ids, self.attachment_names):
            self.sanitized_att_names += [download_attachment_from_id(attachment_id, attachment_name, dir=self.dir_att_path)]

    def process_attachments(self):
        str_attachments = ""
        i = 1
        # convert attachments to text: depending on the file extension we need to use different functions to convert to text
        for attachment_name in self.sanitized_att_names:
            extension = (attachment_name.split(".")[-1]).lower()
            if extension == "pdf":
                str_att = f"FILE {i} - {attachment_name}:\n\n" + pdf2text(self.dir_att_path + "/" + attachment_name) + "\n\n"
            elif extension in ["jpg", "jpeg", "png"]:
                str_att = f"FILE {i} - {attachment_name}:\n\n" + image2text(self.dir_att_path + "/" + attachment_name) + "\n\n"
            elif extension in ["txt"]:
                with open(self.dir_att_path + "/" + attachment_name, "r") as file:
                    str_att = f"FILE {i} - {attachment_name}:\n\n" + file.read() + "\n\n"
            elif extension in ["docx"]:
                str_att = f"FILE {i} - {attachment_name}:\n\n" + word_to_text(self.dir_att_path + "/" + attachment_name) + "\n\n"
            elif extension in ["csv", "xls", "xlsx","xlsb"]:
                str_att = f"FILE {i} - {attachment_name}:\n\n" + tabular_to_text(self.dir_att_path + "/" + attachment_name) + "\n\n"
            else:
                # TODO: verify cases when this happens and maybe set exception and don't include it in the str_attachments
                # TODO: Print/log warning when this happens
                str_att = f"FILE {i} - {attachment_name}:\n\n" + f"File {attachment_name} type not supported" + "\n\n"
            i += 1
            str_attachments += str_att
        return str_attachments

    
    def process_ticket(self):
        # returns ticket structured to be input to LLM
        processed_ticket = f"TICKET DESCRIPTION: {self.description}\n\n"
        processed_ticket += f"TICKET VENDOR CODE: {self.vendor_code}\n\n"
        processed_ticket += f"{self.str_attachments}"

        return processed_ticket
    
    def to_llm_input(self):

        self.attachment_ids, self.attachment_names = self.get_attachment_ids()
        if self.attachment_ids != []:
            self.download_attachments()
            self.str_attachments = self.process_attachments()
        self.processed_ticket = self.process_ticket()
        return self.processed_ticket
        