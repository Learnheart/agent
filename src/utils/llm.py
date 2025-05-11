# from hr_agent.src.config.data_config import data_config
# from openai import OpenAI
#
# client = OpenAI(
#     base_url=data_config["base_url"],
#     api_key=data_config["api_key"]
# )
#
# def call_llm(message_input, client, data_config, temperature=0.4, top_p=0.9):
#     response = client.chat.completions.create(
#         model=data_config["model_name"],
#         messages=message_input,
#         temperature=temperature,
#         top_p=top_p
#     )
#     return response.choices[0].message.content
#
# message_input = [
#     {"role": "user", "content": "suggest a sad song for me"}
# ]
#
# answer = call_llm(message_input, client, data_config)
# print(answer)