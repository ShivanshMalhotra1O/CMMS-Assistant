from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.models.schemas import TaskCommand
from app.policy.roles import Action


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
            ('system',
                "You are a CMMS task interpreter. "
                "Extract a structured task command from the user request.\n"
                "{format_instructions}"
            ),
            ('human',f"{input}")
        ])

    def run(self, user_input:str) -> TaskCommand:

        chain = self.prompt | self.llm | self.parser  # It is a modern langchain way to define the process of how things will flow, first we will get the prompt then it will be given to the llm and the output will be passed on to the parser that will structure it into a structured format.

        return chain.invoke({
            "input": user_input,
            "format_instructions": self.parser.get_format_instructions(),
        })