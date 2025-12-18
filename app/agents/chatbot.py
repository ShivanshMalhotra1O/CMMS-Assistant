# This is the chatbot agent that will be used to answer questions and provide guidance. It won't execute actions or modify data.


class ChatbotAgent:

    def __init__(self, model):
        self.model = model

    def run(self, user_input: str) -> str:
        messages=[
                {"role": "system", "content":("You are a helpful CMMS assistant. "
                        "You provide explanations, guidance, and answers. "
                        "You do NOT execute actions or modify data.")},
                        
                {"role": "user", "content": user_input}
            ]
        return self.model.chat(messages)