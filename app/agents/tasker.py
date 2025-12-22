from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.models.schemas import TaskCommand
from app.policy.roles import Action
from app.orchestration.router import Intent
from app.policy.engine import resolve_action
import re


class TaskerAgent:
    def __init__(self):
        
        # ChatOpenAI Model
        self.llm = ChatOpenAI(
            model = "gpt-4o-mini",
            temperature = 0
        )

        # LocalHost Model
        # self.llm = ChatOllama(
        #     model="llama3", 
        #     temperature=0
        # )

        # Output Parser - Forces LLM to give output in desired format only 
        self.parser = PydanticOutputParser(pydantic_object=TaskCommand)

        # Prompt Template
        self.prompt = ChatPromptTemplate.from_messages([
            (
                 "system",
                    """You are a CMMS task interpreter.

                        Extract a structured JSON command from the user request.

                        Rules:
                        - If the user mentions a work order like "WO-1", extract it as work_order_id.
                        - Work order IDs always start with "WO-".
                        - Do NOT invent IDs.
                        - If no ID is present, return null.

                        Return ONLY valid JSON matching this schema:
                        {format_instructions}
                    """
            ),
            ('human',f"{input}")
        ])

    
    def run(self, action: Action, resource: str, user_input: str) -> dict:
        chain = self.prompt | self.llm | self.parser # It is a modern langchain way to define the process of how things will flow, first we will get the prompt then it will be given to the llm and the output will be passed on to the parser that will structure it into a structured format

        command = chain.invoke({
            "input": user_input,
            "format_instructions": self.parser.get_format_instructions()
        })

        #   Regex
        if action == Action.VIEW and not command.work_order_id:
            match = re.search(r"\b(WO-\d+)\b", user_input, re.IGNORECASE)
            if match:
                command.work_order_id = match.group(1)

        # Debug once (remove later)
        print("DEBUG → action:", action)
        print("DEBUG → command:", command)


        # Always return a plain dict
        return command.model_dump()