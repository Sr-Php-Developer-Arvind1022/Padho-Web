import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter , CharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
# from src.models.model import embed_model
import fitz  # PyMuPDF
from langchain.docstore.document import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
import requests
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings  
from core.logic.send_email import *
from core.models.model import *
from core.logic.deserializer import dataclass_to_dict, ParamHandler
import json
import requests
import logging
from typing import Dict, Any
from fastapi import HTTPException
import os
from cryptography.fernet import Fernet

from core.logic.token_handler import *

from dotenv import load_dotenv
load_dotenv()

CONNECTION_STRING=os.getenv("MySQLConnectionString", "")

import os
import requests
from langchain_community.document_loaders import (
    TextLoader,
    PyMuPDFLoader,
    WebBaseLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredImageLoader,
)
from langchain.text_splitter import CharacterTextSplitter

import os
import base64
import requests
from langchain_community.document_loaders import (
    TextLoader,
    PyMuPDFLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredImageLoader,
)
from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter


def load_file_from_url(file_url: str, ocr_api_url: str = None):
    # --- Step 1: download ---
    ext = os.path.splitext(file_url)[-1].lower()
    local_filename = "temp_ingest" + ext
    resp = requests.get(file_url)
    resp.raise_for_status()
    with open(local_filename, "wb") as f:
        f.write(resp.content)
    print(f"✅ File downloaded: {local_filename}")

    # --- Step 2: choose loader ---
    if ext == ".pdf":
        loader = PyMuPDFLoader(local_filename)
    elif ext == ".txt":
        loader = TextLoader(local_filename, encoding="utf-8")
    elif ext == ".csv":
        loader = CSVLoader(local_filename, encoding="utf-8")
    elif ext == ".docx":
        loader = Docx2txtLoader(local_filename)
    elif ext in [".png", ".jpg", ".jpeg"]:
        loader = UnstructuredImageLoader(local_filename)
    else:
        raise ValueError(f"❌ Unsupported file type: {ext}")

    # --- Step 3: load documents ---
    documents = loader.load()

    # --- Step 4: PDF OCR fallback ---
    if ext == ".pdf" and ocr_api_url:
        needs_ocr = False
        if not documents or all(len(doc.page_content.strip()) < 100 for doc in documents):
            needs_ocr = True

        if needs_ocr:
            print("⚠️ PDF content too short. Falling back to OCR API...")

            with open(local_filename, "rb") as pdf_file:
                encoded_bytes = base64.b64encode(pdf_file.read()).decode("utf-8")

            payload = {
                "fileName": os.path.basename(local_filename),
                "fileContent": encoded_bytes,
                "documentType": "pdf",
            }

            headers = {"Content-Type": "application/json"}
            r = requests.post(ocr_api_url, headers=headers, json=payload)
            r.raise_for_status()
            ocr_response = r.json()

            if ocr_response.get("status") == "success":
                ocr_text = ocr_response.get("OCRText", "")
                documents = [Document(page_content=ocr_text, metadata={"source": file_url, "ocr": True})]
                print("✅ OCR text extracted via API")
            else:
                raise RuntimeError(f"OCR API failed: {ocr_response}")

    # --- Step 5: split documents ---
    text_splitter = CharacterTextSplitter(chunk_size=65535, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    print(f"✅ Loaded {len(texts)} chunks from {local_filename}")
    return texts







def ingest_file(flag:str,file_url: str, client_name: str, client_id: str, file_id: str,APIKey:str , chroma_path: str = "./chroma_langchain_db"):
    """
    Download a file from URL, split into chunks, attach metadata, and add to Chroma DB.
    """
    print(f"📥 Ingesting file for client={client_id}, file={file_id}")
    
    
    # Decide with the help from flag


    if flag == "URL":
            # url = "https://sansad.in/rs"  # Replace with your URL
        print("INTO URL",file_url)    
        loader = WebBaseLoader(file_url)
        documents = loader.load()

        print(documents)

        # Split the documents
        text_splitter = CharacterTextSplitter(chunk_size=65535, chunk_overlap=0)
        texts = text_splitter.split_documents(documents)
        print(texts[:1000])
        print(len(texts))  # Number of chunks
        
        # texts = load_file_from_url(file_url)

    elif flag == "FILE":
            ocr_api = "https://slapps.southindia.cloudapp.azure.com/botaiservicepapi/api/OCRIntegration/extractText"
            texts = load_file_from_url(file_url,ocr_api)
    

    # --- Step 3: attach metadata ---
    for i, doc in enumerate(texts):
        doc.metadata.update({
            
            "file_id": file_id,
            "client_id": client_id,
            "chunk_no": i + 1,
            "url":file_url
        })

    print(f"📑 Prepared {len(texts)} chunks with metadata")

    # --- Step 4: connect to Chroma ---
    # embed_model = HuggingFaceEmbeddings()
    ### embedding model
    # print("APIKey raw value:", APIKey, type(APIKey))
    # print("APIKey repr:", repr(APIKey)) 
    embed_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004" ,google_api_key=str(APIKey))
    vectorstore = Chroma(
        persist_directory=chroma_path,
        embedding_function=embed_model,
        collection_name=client_name,
    )

    # --- Step 5: add + persist ---
    vectorstore.add_documents(texts)
    
    # vectorstore.persist()
    print(f"✅ Stored {len(texts)} chunks in Chroma (collection={client_name})")

    try:
        baseurl=os.getenv("BaseApiUrl", "")
        url2 = baseurl+'/api/DataOperation/Writedata'
        param_handler = ParamHandler()  

        param_handler.add_param("p_knowledge_id", file_id)
        # param_handler.add_param("p_user_id", data.user_id)   
        dbrequest = dbserviceRequest(
            procedureName="usp_Updatembeddings",  # Assuming you have a stored procedure for saving journeys
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
        response = requests.post(url2, headers=headers, data=json.dumps(payload))
        print(response.json())
        response_data = response.json()
        if not response_data.get("isSucceeded", False):
                return {
                    "status": "error",
                    "message": response_data.get("result", {}).get("message", "Unknown error"),
                    "data": []
                }
    except requests.RequestException as e:
            # logger.error(f"DB service call failed for message {message.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"DB service error: {str(e)}")
    except Exception as e:
            # logger.error(f"Processing failed for message {message.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        print("Client active list process completed.") 


def create_vectorstore():
    """Create or load vector store for document retrieval."""

    # First call the stored procedure to get all the documents with embedding 0


    try:
       
        baseurl=os.getenv("BaseApiUrl", "")
        url = baseurl+'/api/DataOperation/Getdata'
        param_handler = ParamHandler()  

        
        dbrequest = dbserviceRequest(
            procedureName="usp_getfiles_to_create_embeddings",  # Assuming you have a stored procedure for saving journeys
            keyValuePairs=[],
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
        print(response_data)

        for record in response_data["result"]:
            if record["types"] == "FILE":
                ingest_file(
                    file_url=record["blobUrl"],
                    client_name=record["ClientName"],
                    client_id=record["clientId"],
                    file_id=record["knowledge_id"],
                    chroma_path="./chroma_langchain_db",
                    APIKey = record["APIKey"], 
                    flag = "FILE"
                )

            elif record["types"] == "URL":
                  print("Inside URL")
                  ingest_file(
                    file_url=record["url"],
                    client_name=record["ClientName"],
                    client_id=record["clientId"],
                    file_id=record["knowledge_id"],
                    chroma_path="./chroma_langchain_db",
                    APIKey = record["APIKey"], 
                    flag = "URL"
                )
                    
    
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
                "data": response_data
            }
    except requests.RequestException as e:
            # logger.error(f"DB service call failed for message {message.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"DB service error: {str(e)}")
    except Exception as e:
            # logger.error(f"Processing failed for message {message.id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        print("Client active list process completed.") 



def create_vectorstore_by_file(file_id):
    """Create or load vector store for document retrieval."""

    # First call the stored procedure to get all the documents with embedding 0


    try:
       
        baseurl=os.getenv("BaseApiUrl", "")
        url = baseurl+'/api/DataOperation/Getdata'
        param_handler = ParamHandler()  

        
        dbrequest = dbserviceRequest(
            procedureName="usp_getfiles_to_create_embeddings",  # Assuming you have a stored procedure for saving journeys
            keyValuePairs=[],
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
        print(response_data)

        for record in response_data["result"]:
            if record["types"] == "FILE":
                ingest_file(
                    file_url=record["blobUrl"],
                    client_name=record["ClientName"],
                    client_id=record["clientId"],
                    file_id=record["knowledge_id"],
                    chroma_path="./chroma_langchain_db",
                    flag = "FILE"
                )

            elif record["types"] == "URL":
                  ingest_file(
                    file_url=record["url"],
                    client_name=record["ClientName"],
                    client_id=record["clientId"],
                    file_id=record["knowledge_id"],
                    chroma_path="./chroma_langchain_db",
                    flag = "URL"
                )
                    
    
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
                "data": response_data
            }
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

