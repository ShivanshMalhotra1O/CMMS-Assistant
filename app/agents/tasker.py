from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.models.schemas import TaskCommand
import re
import os
from dotenv import load_dotenv

load_dotenv()


class TaskerAgent:
    def __init__(self):

        self.llm = ChatOpenAI(
            model="gpt-oss:latest",
            base_url=os.getenv("LLM_BASE_URL"),
            api_key=os.getenv("LLM_API_KEY", "dummy"),
            temperature=0
        )

        self.parser = PydanticOutputParser(
            pydantic_object=TaskCommand
        )

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """
                You are a CMMS Task Interpreter.

                Your job is to convert a user's natural language request into a structured JSON
                command that the CMMS system can execute safely.

                Resource: {resource}

                ------------------------------------
                SUPPORTED RESOURCES
                ------------------------------------
                - work_order
                - asset
                - pm   (preventive maintenance)

                ------------------------------------
                SUPPORTED ACTIONS
                ------------------------------------
                - view    → view records (single or many)
                - create  → create a new record
                - update  → update an existing record

                ------------------------------------
                IMPORTANT RULES
                ------------------------------------
                1. DO NOT invent IDs.
                2. IDs may appear in many formats.
                3. Convert spoken numbers to numeric form if obvious.
                4. If a filter is mentioned → include it.
                5. If nothing is mentioned → return empty filters.
                6. ALWAYS use action = "view" for read requests.
                7. Never explain. Always return a best guess.

                ------------------------------------
                STATUS NORMALIZATION (WORK ORDERS)
                ------------------------------------
                - open, pending         → status = "Open"
                - closed, completed    → status = "Closed"
                - in progress, running → status = "In Progress"

                ------------------------------------
                ASSET STATUS NORMALIZATION
                ------------------------------------
                - running, active, operational → status = "Running"
                - stopped, inactive            → status = "Stopped"
                - maintenance, under repair    → status = "Maintenance"

                ------------------------------------
                OUTPUT FORMAT
                ------------------------------------
                Return ONLY valid JSON matching this schema:

                {format_instructions}

                ------------------------------------
                EXAMPLES
                ------------------------------------
                User: "list open work orders"
                Output:
                {{
                "resource": "work_order",
                "action": "view",
                "filters": {{
                    "status": "Open"
                }},
                "confidence": "high"
                }}

                User: "show work order 42"
                Output:
                {{
                "resource": "work_order",
                "action": "view",
                "filters": {{
                    "id": "WO-42"
                }},
                "confidence": "high"
                }}

                User: "show all assets"
                Output:
                {{
                "resource": "asset",
                "action": "view",
                "filters": {{}},
                "confidence": "high"
                }}

                User: "give me list of running assets"
                Output:
                {{
                "resource": "asset",
                "action": "view",
                "filters": {{
                    "status": "Running"
                }},
                "confidence": "high"
                }}

                ------------------------------------
                Now process the user request.
                """
            ),
            ("human", "{input}")
        ])

    def run(self, user_input: str, resource: str) -> TaskCommand:
        chain = self.prompt | self.llm | self.parser

        command: TaskCommand = chain.invoke({
            "input": user_input,
            "resource": resource,
            "format_instructions": self.parser.get_format_instructions()
        })

        # -----------------------------
        # Regex fallback (SAFE)
        # -----------------------------
        if (
            command.resource == "work_order"
            and command.action == "view"
            and not command.filters.id
        ):
            match = re.search(r"\bWO[-\s]?(\d+)\b", user_input, re.IGNORECASE)
            if match:
                command.filters.id = f"WO-{match.group(1)}"

        if (
            command.resource == "asset"
            and command.action == "view"
            and not command.filters.id
        ):
            match = re.search(r"\basset\s+([\w\- ]+)\b", user_input, re.IGNORECASE)
            if match:
                command.filters.id = match.group(1).strip()

        if (
            command.resource == "pm"
            and command.action == "view"
            and not command.filters.id
        ):
            match = re.search(r"\bPM[-\s]?(\d+)\b", user_input, re.IGNORECASE)
            if match:
                command.filters.id = f"PM-{match.group(1)}"

        # if (command.action == "list"):
        #     command.action = "view"

        print("DEBUG → TaskCommand:", command.model_dump())
        return command
