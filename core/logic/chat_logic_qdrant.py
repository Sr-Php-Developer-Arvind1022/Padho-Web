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
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings  
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
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.http.exceptions import UnexpectedResponse

from dotenv import load_dotenv
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

VectorURL=os.getenv("VectorURL", "http://localhost:6333")
def getVectorStoreAsRetriver(response_data):
        chroma_path = "./chroma_langchain_db"

        collection_name = response_data["result"][0]["ClientName"]
        embed_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

        client = QdrantClient(VectorURL)
#         vectorstore = Chroma(
#     persist_directory=chroma_path,
#     collection_name=collection_name,
#     embedding_function=embed_model,
# )
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embed_model,
        )
        return vectorstore.as_retriever()
        
        


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

        
        retriever = getVectorStoreAsRetriver(response_data)

        llm_model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",                     
        temperature=0,                                
        )

        qa = RetrievalQA.from_chain_type(llm=llm_model,chain_type="stuff", retriever=retriever,return_source_documents=False)

        # question = "What is e-TDS returns?"
        documents = qa.invoke(question)
        # print(documents.keys())
        # print(len(documents))
        
    
        result = documents
        print(type(result))
        print(result.keys())
        print(len(result))
        print('result:', result['result'])
        # print('source_documents:', result['source_documents'])
        print('Question:', result['query'])

    
           


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
        
        return {
                "status": "success",
                "message": "Vectore store created successfully",
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

