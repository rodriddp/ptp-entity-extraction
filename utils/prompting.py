def get_system_prompt(path: str) -> str:
    with open(path, "r") as file:
        return file.read()
    
def save_system_prompt(prompt: str, path: str):
    with open(path, "w") as file:
        file.write(prompt)
