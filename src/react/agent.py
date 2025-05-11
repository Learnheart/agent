from typing import Dict, List
from enum import Enum, auto
from typing import Union, Callable
from pydantic import BaseModel, Field
from hr_agent.src.config.log import logger
from hr_agent.src.config.data_config import data_config
from openai import OpenAI
from hr_agent.src.utils.common import read_file, write_to_file
import json
from hr_agent.src.tool.calculation import calculation
from hr_agent.src.tool.knowledge import context
from hr_agent.src.utils.llm import answer

output_path = "../data/output/trace.txt"
Observation = Union[str, Exception]

class Name(Enum):
    """Enumeration for tool names available to the agent."""
    CALCULATION = auto()
    KNOWLEDGE = auto()
    NONE = auto()

    def __str__(self) -> str:
        return self.name.lower() # return a string or exception => use for return answer

class Message(BaseModel):
    role: str = Field(..., description="role of message sender")
    content: str = Field(..., description="the content of message")

class Choice(BaseModel):
    name: Name = Field(..., description="name of chosen tool")
    reason: str = Field(..., description="reason to choose that tool")

class Tool:
    def __init__(self, name:Name, function:Callable[[str], str]):
        self.name = name
        self.function = function

    def use(self, query:str) -> Observation:
        """
        :param query: input query for the tool generate by llm
        :return: decision of chosen tool
        """
        try:
            return self.function(query)
        except Exception as e:
            logger.error(f"Error executing tool {self.name}: {e}")
            return str(e)

class Agent:
    def __init__(self) -> None:
        self.tools: Dict[Name, Tool] = {}
        self.messages: List[Message] = []
        self.query = ""
        self.max_iteration = 5
        self.current_iteration = 0
        self.template = self.load_template()
        self.client = OpenAI(
            base_url=data_config["base_url"],
            api_key=data_config["api_key"]
        )

    def load_template(self) -> str:
        file = "../data/input/react_prompt.txt"
        return read_file(file)

    def register(self, name:Name, function: Callable[[str], str]):
        self.tools[name] = Tool(name, function)

    def call_llm(self, message_input, client, data_config, temperature=0.4, top_p=0.9):
        try:
            response = client.chat.completions.create(
                model=data_config["model_name"],
                messages=message_input,
                temperature=temperature,
                top_p=top_p
            )
            return response.choices[0].message.content
        except Exception as e:
            print(e)
            print("No response from agent")

    # Logs the message with the specified role and content and writes to file.
    def trace(self, role:str, content: str) -> None:
        if role != "system":
            self.messages.append(Message(role=role, content=content))
            write_to_file(path=output_path, content=f"{role}: {content} \n")

    def get_history(self) -> str:
        """
        Retrieves the conversation history.

        Returns:
            str: Formatted history of messages.
        """
        return "\n".join([f"{message.role}: {message.content}" for message in self.messages])

    def think(self) -> None:
        """
        process current query, decision actions
        Returns: thinking solution
        """
        self.current_iteration += 1
        logger.info(f"Starting at {self.current_iteration} iteration")
        write_to_file(path=output_path, content=f"\n{'='*50}\nIteration {self.current_iteration}\n{'='*50}\n")

        if self.current_iteration > self.max_iteration:
            logger.warning("Get maximum iterations, stopping")
            self.trace("assistant", "I'm sorry, but I couldn't find a satisfactory answer within the allowed number of iterations. Here's what I know so far: " + self.get_history())
            return

        prompt = self.template.format(
            query = self.query,
            history = self.get_history(),
            tools = ", ".join([str(tool.name) for tool in self.tools.values()])
        )

        message = [{"role": "user", "content": prompt}]

        response = self.call_llm(
            message_input=message,
            data_config=data_config,
            client=self.client
        )
        logger.info(f"Thinking => {response}")
        self.trace("assistant", f"thought: {response}")
        self.decide(response)

    def decide(self, response: str):
        """
        Returns: decide whether return final answer or take action
        """
        try:
            parsed_response = json.loads(response)
            if "action" in parsed_response:
                action = parsed_response["action"]
                tool_name = Name[action["name"].upper()]
                if tool_name == Name.NONE:
                    logger.info("No tool suitable. Proceeding answer")
                    self.think()
                else:
                    self.trace("assistant", f"Action: Using tool {tool_name}")
                    self.act(tool_name, action.get("input", self.query))
            elif "answer" in parsed_response:
                self.trace("assistant", f"Final answer: {parsed_response['answer']}")

            else:
                raise ValueError("Invalid response format")

        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            self.trace("assistant", "I encountered an unexpected error. Let me try a different approach.")
            self.think()


    def act(self, tool_name:Name, query:str):
        """
        Executes the specified tool's function on the query and logs the result.

        Args:
            tool_name (Name): The tool to be used.
            query (str): The query for the tool.
        """
        tool = self.tools.get(tool_name)
        if tool:
            result = tool.use(query)
            observation = f"Observation from {tool_name}: {result}"
            self.trace("system", observation)
            self.messages.append(Message(role="system", content=observation))  # Add observation to message history
            self.think()
        else:
            logger.error(f"No tool registered for choice: {tool_name}")
            self.trace("system", f"Error: Tool {tool_name} not found")
            self.think()

    def execute(self, query:str):
        """
        Executes the agent's query-processing workflow.

        Args:
            query (str): The query to be processed.

        Returns:
            str: The final answer or last recorded message content.
        """
        self.query = query
        self.trace(role="user", content=query)
        self.think()
        return self.messages[-1].content


def run(query:str) -> str:
    hr_agent = Agent()
    hr_agent.register(Name.KNOWLEDGE, context)
    hr_agent.register(Name.CALCULATION, calculation)

    answer = hr_agent.execute(query)
    return answer


if __name__ == '__main__':
    query = "msb có bao nhiêu ca làm việc?"
    final_answer = run(query)
    logger.info(final_answer)



