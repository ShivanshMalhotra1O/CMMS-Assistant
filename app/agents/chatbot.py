# This is the chatbot agent that will be used to answer questions and provide guidance. It won't execute actions or modify data.


class ChatbotAgent:

    def __init__(self, model):
        self.model = model

    def run(self, user_input: str) -> str:
        messages=[
                {"role": "system", "content":(""" You are a CMMS AI assistant.
                Rules:
                - Do NOT assume access to live CMMS data.
                - Do NOT invent asset statuses or records.
                - Keep responses concise and operational.
                - If a request sounds like a system query (status, list, search), explain what would be checked, not how to troubleshoot.
                - Do NOT provide generic troubleshooting unless explicitly asked.
                - Avoid long explanations unless the user asks "how" or "why".
                """)},
                        
                {"role": "user", "content": user_input}
            ]
        return self.model.chat(messages)