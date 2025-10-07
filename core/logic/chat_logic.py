import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter , CharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
# from src.models.model import embed_model
import fitz  # PyMuPDF
from langchain_community.document_loaders import TextLoader
from langchain.docstore.document import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
import requests
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings  
from langchain.prompts import PromptTemplate
from langchain.chains.retrieval_qa.base import RetrievalQA

from core.logic.send_email import *
from core.models.model import *
from core.logic.deserializer import dataclass_to_dict, ParamHandler
from fastapi.responses import JSONResponse
import json
import requests
import logging
from typing import Dict, Any
from fastapi import HTTPException
import os
from cryptography.fernet import Fernet
# from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings  
from core.logic.token_handler import *
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from dotenv import load_dotenv


from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

CONNECTION_STRING=os.getenv("MySQLConnectionString", "")

# def ingest_file(file_url: str, client_name: str, client_id: str, file_id: str, chroma_path: str = "./chroma_langchain_db"):
#     """
#     Download a file from URL, split into chunks, attach metadata, and add to Chroma DB.
#     """
#     print(f"📥 Ingesting file for client={client_id}, file={file_id}")
    
#     # --- Step 1: download file ---
#     local_filename = "temp_ingest.txt"
#     resp = requests.get(file_url)
#     resp.raise_for_status()
#     with open(local_filename, "wb") as f:
#         f.write(resp.content)
#     print(f"✅ File downloaded: {local_filename}")

#     # --- Step 2: load & split ---
#     loader = TextLoader(local_filename, encoding="utf-8")
#     documents = loader.load()
#     text_splitter = CharacterTextSplitter(chunk_size=65535, chunk_overlap=0)
#     texts = text_splitter.split_documents(documents)

#     # --- Step 3: attach metadata ---
#     for i, doc in enumerate(texts):
#         doc.metadata.update({
#             "file_id": file_id,
#             "client_id": client_id,
#             "chunk_no": i + 1,
#         })

#     print(f"📑 Prepared {len(texts)} chunks with metadata")

#     # --- Step 4: connect to Chroma ---
#     embed_model = HuggingFaceEmbeddings()
#     vectorstore = Chroma(
#         persist_directory=chroma_path,
#         embedding_function=embed_model,
#         collection_name=client_name,
#     )

#     # --- Step 5: add + persist ---
#     vectorstore.add_documents(texts)
    
#     # vectorstore.persist()
#     print(f"✅ Stored {len(texts)} chunks in Chroma (collection={client_name})")

#     try:
#         baseurl=os.getenv("BaseApiUrl", "")
#         url2 = baseurl+'/api/DataOperation/Writedata'
#         param_handler = ParamHandler()  

#         param_handler.add_param("p_knowledge_id", file_id)
#         # param_handler.add_param("p_user_id", data.user_id)   
#         dbrequest = dbserviceRequest(
#             procedureName="usp_Updatembeddings",  # Assuming you have a stored procedure for saving journeys
#             keyValuePairs=param_handler.get_params(),
#             outputParam="string",
#             connectionString=CONNECTION_STRING,
#             dbtype="mysql"
#         ) 

#         headers = {'Content-Type': 'application/json'}
#         payload = {
#             "procedureName": dbrequest.procedureName,
#             "keyValuePairs": [
#                 {
#                     "key": kvp.key,
#                     "dbType": kvp.dbType,
#                     "value": kvp.value,
#                     "isInParameter": kvp.isInParameter
#                 } for kvp in dbrequest.keyValuePairs
#             ],
#             "outkeyValuePairs": {},
#             "outputParam": dbrequest.outputParam,
#             "connectionString": dbrequest.connectionString,
#             "dbtype": dbrequest.dbtype
#         }

#         print(dbrequest.keyValuePairs)
#         print("before sp paramsssssss")
#         response = requests.post(url2, headers=headers, data=json.dumps(payload))
#         print(response.json())
#         response_data = response.json()
#         if not response_data.get("isSucceeded", False):
#                 return {
#                     "status": "error",
#                     "message": response_data.get("result", {}).get("message", "Unknown error"),
#                     "data": []
#                 }
#     except requests.RequestException as e:
#             # logger.error(f"DB service call failed for message {message.id}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"DB service error: {str(e)}")
#     except Exception as e:
#             # logger.error(f"Processing failed for message {message.id}: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
#     finally:
#         print("Client active list process completed.") 


def getVectorStoreAsRetriver(response_data):
        chroma_path = "./chroma_langchain_db"
        collection_name = response_data["result"][0]["ClientName"]
        # embed_model = HuggingFaceEmbeddings()
        APIKey = str(response_data["result"][0]["APIKey"])
        embed_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004" ,google_api_key=str(APIKey))


        vectorstore = Chroma(
    persist_directory=chroma_path,
    collection_name=collection_name,
    embedding_function=embed_model,
)
        inspect_vectorstore(vectorstore)
        
        retriever = vectorstore.as_retriever(
    search_type="mmr",         # "similarity" or "mmr"
    search_kwargs={
        "k": 2,                # fetch more docs
        "fetch_k": 10,         # pool to diversify
        "lambda_mult": 0.7     # balance relevance/diversity
    }
)       
        # test_query = "What are e-TDS returns"   # replace with your real query when debugging
        # docs = retriever.get_relevant_documents(test_query)
        # print("\n--- Retriever Returned ---")
        # for i, d in enumerate(docs, 1):
        #     print(f"\nDoc {i}:")
        #     print("Source:", d.metadata.get("source") or d.metadata.get("url"))
        #     print("Content Preview:", d.page_content[:300], "...")
        #     print("Metadata:", d.metadata)

        return retriever
                
# Global storage for chat histories (per session)
_chat_histories = {}


def run_qa_with_extras(question: str, response_data: dict, session_id: str):
    print("🚀 Starting QA with history-aware retrieval")
    
    retriever = getVectorStoreAsRetriver(response_data)
    
    APIKey = str(response_data["result"][0]["APIKey"])
    model_name = str(response_data["result"][0]["llm_model"])
    print("🔑 APIKey:", APIKey[:10] + "...")
    print("📌 Model:", model_name)

    # Initialize or retrieve chat history for this session
    if session_id not in _chat_histories:
        _chat_histories[session_id] = []
    
    chat_history = _chat_histories[session_id]

    # Initialize LLM
    llm_model = ChatGoogleGenerativeAI(
        google_api_key=APIKey,
        model=model_name,
        temperature=0,
    )

    # ============================================
    # STEP 1: History-Aware Retriever
    # ============================================
    # This reformulates the question based on chat history BEFORE retrieval
    contextualize_q_system_prompt = """
Given a chat history and the latest user question which might reference context in the chat history, 
formulate a standalone question which can be understood without the chat history. 
Do NOT answer the question, just reformulate it if needed and otherwise return it as is.
"""

    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    history_aware_retriever = create_history_aware_retriever(
        llm_model, retriever, contextualize_q_prompt
    )

    # ============================================
    # STEP 2: Question-Answer Chain
    # ============================================
    qa_system_prompt = """
You are a helpful assistant. Use ONLY the following context to answer the question.

If the answer is not in the context, reply with: "I don't know based on the provided documents."

Context:
{context}
"""

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm_model, qa_prompt)

    # ============================================
    # STEP 3: Combine into RAG Chain
    # ============================================
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    # ============================================
    # STEP 4: Invoke with Chat History
    # ============================================
    result = rag_chain.invoke({
        "input": question,
        "chat_history": chat_history
    })

    answer = result["answer"]
    source_docs = result.get("context", [])
    
    print("\n✅ Answer:", answer)
    print("\n📂 Retrieved Documents:")
    for i, doc in enumerate(source_docs, start=1):
        print(f"--- Doc {i} ---")
        print("Metadata:", doc.metadata)
        snippet = doc.page_content[:300].replace("\n", " ")
        print("Snippet:", snippet, "...\n")

    # ============================================
    # STEP 5: Update Chat History
    # ============================================
    chat_history.extend([
        HumanMessage(content=question),
        AIMessage(content=answer)
    ])
    
    # Keep only last 10 messages (5 exchanges) to prevent context overflow
    if len(chat_history) > 10:
        chat_history = chat_history[-10:]
    
    _chat_histories[session_id] = chat_history

    # ============================================
    # Token Counting & Metadata Enrichment
    # ============================================
    input_text = "".join([doc.page_content for doc in source_docs]) + question
    input_tokens = len(input_text.split())
    output_tokens = len(answer.split())

    print("🔢 Input tokens (approx):", input_tokens)
    print("🔢 Output tokens (approx):", output_tokens)

    # Enrich response with metadata
    enrich_prompt = f"""
You are a helpful assistant analyzing a Q&A interaction.

User asked: "{question}"
Answer generated: "{answer}"

Return ONLY a valid JSON object with these keys:
- "page_numbers": Extract page numbers from metadata if available, otherwise empty string ""
- "next_suggestion": Suggest ONE relevant follow-up question
- "better_prompt": If answer seems incomplete, suggest how to rephrase the question, otherwise empty string ""

Output only the JSON, no extra text.
"""

    try:
        enriched = llm_model.invoke(enrich_prompt).content
    except Exception as e:
        print(f"⚠️ Enrichment failed: {e}")
        enriched = '{"page_numbers": "", "next_suggestion": "", "better_prompt": ""}'

    # ============================================
    # Final Response
    # ============================================
    custom_response = {
        "query": question,
        "result": answer,
        "metadata": [doc.metadata for doc in source_docs],
        "chat_history_length": len(chat_history),
        "extras": enriched
    }

    return custom_response


from langchain.schema import Document

def inspect_vectorstore(vectorstore, n=5):
    docs = vectorstore.get(limit=n)  # fetch few raw docs
    print(f"📦 Vectorstore contains {len(vectorstore.get()['ids'])} chunks")

    for i, doc in enumerate(docs["documents"]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Length: {len(doc)} characters")
        print(f"Preview: {doc[:300]!r}")
        print(f"Metadata: {docs['metadatas'][i]}")

def clear_session_history(session_id: str):
    """Clear chat history for a specific session"""
    if session_id in _chat_histories:
        del _chat_histories[session_id]
        print(f"🗑️ Cleared history for session: {session_id}")


def start_chat(user_id,question):
    """Create or load vector store for document retrieval."""

    # First call the stored procedure to get all the documents with embedding 0


    try:
       
        baseurl=os.getenv("BaseApiUrl", "")
        url = baseurl+'/api/DataOperation/Getdata'
        param_handler = ParamHandler()  

        param_handler.add_param("p_userId",user_id)
        param_handler.add_param("flag","getclient")

        
        dbrequest = dbserviceRequest(
            procedureName="usp_GetClient",  # Assuming you have a stored procedure for saving journeys
            keyValuePairs=param_handler.get_params(),
            outputParam="string",
            connectionString=CONNECTION_STRING,
            dbtype="mysql"
        ) 

        headers = {'Content-Type': 'application/json'}
        payload = {
            "procedureName": dbrequest.procedureName,
            "keyValuePairs": [
                {
                    "key": kvp.key,
                    "dbType": kvp.dbType,
                    "value": kvp.value,
                    "isInParameter": kvp.isInParameter
                } for kvp in dbrequest.keyValuePairs
            ],
            "outkeyValuePairs": {},
            "outputParam": dbrequest.outputParam,
            "connectionString": dbrequest.connectionString,
            "dbtype": dbrequest.dbtype
        }

        print(dbrequest.keyValuePairs)
        print("before sp paramsssssss")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(response.json())
        response.raise_for_status()
        print(response.raise_for_status())
        response_data = response.json()
        print(response_data["result"][0]["ClientName"])

        
        result = run_qa_with_extras(question,response_data,user_id)
        # retriever = getVectorStoreAsRetriver(response_data)

        # llm_model = ChatGoogleGenerativeAI(
        # model="gemini-2.0-flash-lite",                     
        # temperature=0,                                
        # )

        # qa = RetrievalQA.from_chain_type(llm=llm_model,chain_type="stuff", retriever=retriever,return_source_documents=True)

        # # question = "What is e-TDS returns?"
        # documents = qa.invoke(question)
        # # print(documents.keys())
        # # print(len(documents))
        
    
        # result = documents
        # answer = result["result"]
        # source_docs = result["source_documents"]
        # print("\n🔹 Answer:", answer)
        # print("\n🔹 Sources:")
        # for i, doc in enumerate(source_docs, 1):
        #     print(f"Doc {i} metadata:", doc.metadata)
        #     print(f"Doc {i} snippet:", doc.page_content[:200], "...\n")


        # print(type(result))
        # print(result.keys())
        # print(len(result))
        # print('result:', result['result'])
        # print('source_documents:', result['source_documents'])
        # print('Question:', result['query'])

    
           


        # for record in response_data["result"]:
        #     if record["types"] == "file":
        #         ingest_file(
        #             file_url=record["url"],
        #             client_name=record["ClientName"],
        #             client_id=record["clientId"],
        #             file_id=record["knowledge_id"],
        #             chroma_path="./chroma_langchain_db"
        #         )
    

        # print("Vector store created!")
        
        if not response_data.get("isSucceeded", False):
                return {
                    "status": "error",
                    "message": response_data.get("result", {}).get("message", "Unknown error"),
                    "data": []
                }
        
        return {
                "status": "success",
                "message": "Chat response recieved",
                "data": result
            }
    except requests.RequestException as e:
            # logger.error(f"DB service call failed for message {message.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"DB service error: {str(e)}")
    except Exception as e:
            # logger.error(f"Processing failed for message {message.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        print("Client active list process completed.") 


def check_knowledge_exist(user_id):
    """Create or load vector store for document retrieval."""

    # First call the stored procedure to get all the documents with embedding 0


    try:
       
        baseurl=os.getenv("BaseApiUrl", "")
        url = baseurl+'/api/DataOperation/Getdata'
        param_handler = ParamHandler()  

        param_handler.add_param("p_userId",user_id)
        param_handler.add_param("flag","check")
        
        dbrequest = dbserviceRequest(
            procedureName="usp_GetClient",  # Assuming you have a stored procedure for saving journeys
            keyValuePairs=param_handler.get_params(),
            outputParam="string",
            connectionString=CONNECTION_STRING,
            dbtype="mysql"
        ) 

        headers = {'Content-Type': 'application/json'}
        payload = {
            "procedureName": dbrequest.procedureName,
            "keyValuePairs": [
                {
                    "key": kvp.key,
                    "dbType": kvp.dbType,
                    "value": kvp.value,
                    "isInParameter": kvp.isInParameter
                } for kvp in dbrequest.keyValuePairs
            ],
            "outkeyValuePairs": {},
            "outputParam": dbrequest.outputParam,
            "connectionString": dbrequest.connectionString,
            "dbtype": dbrequest.dbtype
        }

        print(dbrequest.keyValuePairs)
        print("before sp paramsssssss")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(response.json())
        response.raise_for_status()
        print(response.raise_for_status())
        response_data = response.json()
        print(response_data["result"][0]["COUNT"])


    
           


        # for record in response_data["result"]:
        #     if record["types"] == "file":
        #         ingest_file(
        #             file_url=record["url"],
        #             client_name=record["ClientName"],
        #             client_id=record["clientId"],
        #             file_id=record["knowledge_id"],
        #             chroma_path="./chroma_langchain_db"
        #         )
    

        print("Vector store created!")
        
        if not response_data.get("isSucceeded", False):
                return {
                    "status": "error",
                    "message": response_data.get("result", {}).get("message", "Unknown error"),
                    "data": []
                }
        
        return response_data["result"][0]["COUNT"]
    except requests.RequestException as e:
            # logger.error(f"DB service call failed for message {message.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"DB service error: {str(e)}")
    except Exception as e:
            # logger.error(f"Processing failed for message {message.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        print("Client active list process completed.") 











    


# def inspect_vectorstore():
#     """Inspect the text content in the Chroma vector store."""
#     chroma_path = "./chroma_langchain_db"
#     collection_name = "client1"

#     if not os.path.exists(chroma_path):
#         print("No vector store found at the specified path.")
#         return

#     print("Loading vector store...")
#     vectorstore = Chroma(
#         persist_directory=chroma_path,
#         embedding_function=embed_model,
#         collection_name=collection_name,
#     )

#     # Get all documents from the collection
#     print("Retrieving documents...")
#     collection = vectorstore._client.get_collection(collection_name)
#     documents = collection.get(include=["documents"])

#     # Print the text content of each document
#     if documents["documents"]:
#         print(f"Found {len(documents['documents'])} document(s) in the vector store.")
#         for i, doc in enumerate(documents["documents"], 1):
#             print(f"\nDocument {i}:")
#             print(doc)
#             print("-" * 50)
#     else:
#         print("No documents found in the vector store.")

