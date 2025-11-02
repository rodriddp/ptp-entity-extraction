def calculate_openai_cost(input_tokens: int, output_tokens: int, model: str="gpt-4-turbo") -> float:
    """
    Calculate the cost of querying OpenAI's GPT-4 API based on the number of input and output tokens.

    :param input_tokens: Number of input tokens used in the request.
    :param output_tokens: Number of output tokens generated in the response.
    :param model: The specific GPT-4 model used ('gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini').
    :return: Total cost in USD.
    """
    pricing = {
        'gpt-4': {'input_per_1m': 30, 'input_per_1m': 60},
        'gpt-4-turbo': {'input_per_1m': 10, 'input_per_1m': 30},
        'gpt-4o': {'input_per_1m': 5, 'input_per_1m': 15},
        'gpt-4o-mini': {'input_per_1m': 0.15, 'input_per_1m': 0.6},
    }

    if model not in pricing:
        raise ValueError(f"Model '{model}' not recognized. Available models: {', '.join(pricing.keys())}")

    input_cost = (input_tokens / 10e6) * pricing[model]['input_per_1m']
    output_cost = (output_tokens / 10e6) * pricing[model]['input_per_1m']
    total_cost = input_cost + output_cost

    return round(total_cost, 6)  # Round to 6 decimal places for precision