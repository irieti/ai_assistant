import os
from typing import Optional
from functools import lru_cache
from core_functions import KnowledgeManager
from openai import OpenAI
import logging
from .views import get_chat_mapping, update_chat_mapping

client = OpenAI()

# Set up logging
logger = logging.getLogger(__name__)


class AIAssistant:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        # Set the OpenAI API key and initialize assistant with model
        client.api_key = api_key
        self.model = model
        self.knowledge_manager = KnowledgeManager()  # Manage knowledge base
        self._assistant_id: Optional[str] = None  # Cache assistant ID

    @lru_cache(maxsize=1)
    def get_assistant_id(self) -> str:
        """Cache and retrieve assistant ID."""
        if self._assistant_id:
            assistant_id = self._assistant_id

            new_instructions = self.knowledge_manager.load_instructions()

            try:
                # Update assistant instructions
                assistant = client.beta.assistants.update(
                    assistant_id=assistant_id, instructions=new_instructions
                )
                self._assistant_id = (
                    None  # Invalidate cached assistant ID to force re-fetch
                )
                logger.info(f"Instructions updated for assistant: {assistant_id}")
                print(f"Instructions updated for assistant: {assistant_id}")
                return assistant_id
            except Exception as e:
                logger.error(f"Error updating assistant instructions: {e}")
                raise

        # Retrieve the list of assistants from the beta API
        try:
            assistants = client.beta.assistants.list()
            logger.debug(f"Assistants list retrieved: {assistants}")
        except Exception as e:
            logger.error(f"Error retrieving assistants: {e}")
            raise

        # Access the assistants' list from the returned object
        for assistant in assistants.data:
            if assistant.name == os.getenv("ASSISTANT_NAME"):
                self._assistant_id = assistant.id
                new_instructions = self.knowledge_manager.load_instructions()
                assistant = client.beta.assistants.update(
                    assistant_id=self._assistant_id, instructions=new_instructions
                )
                logger.info(f"Assistant found: {self._assistant_id}")
                return self._assistant_id

        # If assistant doesn't exist, create a new one using the beta API
        try:
            assistant = client.beta.assistants.create(
                name=os.getenv("ASSISTANT_NAME"),
                instructions=self.knowledge_manager.load_instructions(),
                model="gpt-4o",
                tools=[{"type": "file_search"}],  # Define tools like file search
            )
            self._assistant_id = assistant.id
            logger.info(f"New assistant created: {self._assistant_id}")
            print("instructions was loaded successfully")
            return self._assistant_id
        except Exception as e:
            logger.error(f"Error creating assistant: {e}")
            raise

    def get_response(self, integration, chat_id, prompt: str) -> str:
        """Get AI response to the given prompt."""
        assistant_id = self.get_assistant_id()  # Retrieve the assistant ID

        # Check and update knowledge base if necessary
        if self.knowledge_manager.check_and_update_knowledge():
            logger.info("Knowledge base update detected, updating knowledge.")
            print("Updating knowledge in vector store")

            try:
                vector_stores = client.beta.vector_stores.list()
                existing_store = None

                for store in vector_stores.data:
                    if store.name == "Online School Statements":
                        existing_store = store
                        break

                if existing_store:
                    vector_store_id = existing_store.id
                else:
                    vector_store = client.beta.vector_stores.create(
                        name="Online School Statements"
                    )
                    vector_store_id = vector_store.id

                existing_files = client.beta.vector_stores.files.list(
                    vector_store_id=vector_store_id
                )

                for file in existing_files.data:
                    client.beta.vector_stores.files.delete(
                        vector_store_id=vector_store_id, file_id=file.id
                    )

                file_paths = ["ai_assistant/knowledge_base.txt"]
                file_streams = [open(path, "rb") for path in file_paths]

                file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vector_store_id, files=file_streams
                )

                assistant = client.beta.assistants.update(
                    assistant_id=assistant_id,
                    tool_resources={
                        "file_search": {"vector_store_ids": [vector_store_id]}
                    },
                )

            except Exception as e:
                logger.error(f"Error managing vector store: {e}")
                raise
        assistant = client.beta.assistants.retrieve(assistant_id=assistant_id)

        # Create a new thread for interaction with the assistant
        chat_mapping = get_chat_mapping(
            integration=integration, chat_id=chat_id, assistant_id=assistant.id
        )
        if not chat_mapping:
            # Create a thread and attach the file to the message
            thread = client.beta.threads.create()

            update_chat_mapping(
                integration=integration,
                chat_id=chat_id,
                assistant_id=assistant.id,
                thread_id=thread.id,
            )
            thread_id = thread.id
            print("chat_mappings updated")
        else:
            thread_id = chat_mapping.thread_id
            print("chat_mapping exists")

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content="Remember to ONLY use information from the knowledge_base to answer my questions. If the information is not in the knowledge base, tell me you don't have that information. My question is: "
            + prompt
            + "do NOT add the link or mention the knowledge_base.txt file in the answer",
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id, assistant_id=assistant.id
        )

        messages = list(
            client.beta.threads.messages.list(thread_id=thread_id, run_id=run.id)
        )
        messages_content = messages[0].content[0].text
        return messages_content
