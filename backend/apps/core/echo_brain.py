import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables import Runnable
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv

load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "false"
class EchoBrain:
    def __init__(self):
        self.openai_key=os.getenv("OPENAI_API_KEY")
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY is not set in this environment")
        
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="gpt-4",
            openai_api_key=self.openai_key
        )

        self.memory=ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        self.embeddings=OpenAIEmbeddings(openai_api_key=self.openai_key)
        self.db = Chroma(
            collection_name="echo_brain",
            embedding_function=self.embeddings,
            persist_directory="chroma_store"
        )
        self.db = Chroma(
            persist_directory="vectorstore",
            embedding_function=self.embeddings
        )
        retriever=self.db.as_retriever()

        retriever_prompt=ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("placeholder", "{chat_history}"),
            ("human", "{input}")
        ])

        combine_prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(
            "Use the following context to answer the user's question:\n\n{context}\n\nQuestion: {input}"
            )
        ])

        retrieval_chain=create_history_aware_retriever(
            retriever=retriever,
            llm=self.llm,
            prompt=retriever_prompt
        )

        combine_docs_chain = create_stuff_documents_chain(
            llm=self.llm,
            prompt=combine_prompt,
        )

        self.chain = create_retrieval_chain(
            retrieval_chain,
            combine_docs_chain
       )


    def ask(self, question: str) -> str:
        response=self.chain.invoke({
            "input": question,
            "chat_history": self.memory.load_memory_variables({})["chat_history"]
        })
        return response
