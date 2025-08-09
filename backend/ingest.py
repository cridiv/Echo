import os
import glob
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.openai import OpenAIEmbeddings
from langchain.schema import Document
import json
from dotenv import load_dotenv

load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "false"

def load_metrics_data():
    with open("data/sample_metrics.json", "r") as f:
        metrics = json.load(f)
    print(f"🔍 Loaded {len(metrics)} metrics from sample_metrics.json")

    documents = []
    for metric in metrics:
        service = metric["service"]
        metric_type = metric["metric"]
        value = metric["value"]
        timestamp = metric["timestamp"]

        content = f"{service} reported {metric_type} = {value} at {timestamp}"
        metadata = {
            "timestamp": timestamp,
            "service": service,
            "metric": metric_type
        }
        documents.append(Document(page_content=content, metadata=metadata))
    
    print(f"📄 Created {len(documents)} metric documents.")
    return documents


def load_traces_data():
    with open("data/sample_traces.json", "r") as f:
        traces = json.load(f)
    print(f"🔗 Loaded {len(traces)} traces")

    documents = []
    for trace in traces:
        trace_id = trace["trace_id"]
        spans = trace["spans"]

        content_lines = []
        for span in spans:
            line = f"{span['service']} - {span['operation']} from {span['start']} to {span['end']}"
            if "error" in span:
                line += f" [ERROR: {span['error']}]"
            content_lines.append(line)
        
        full_content = f"Trace {trace_id} includes the following spans:\n" + "\n".join(content_lines)
        metadata = {
            "trace_id": trace_id,
            "services": ", ".join(set(span["service"] for span in spans)),
            "start_time": spans[0]["start"],
            "end_time": spans[-1]["end"]
        }
        documents.append(Document(page_content=full_content, metadata=metadata))
    
    print(f"📄 Created {len(documents)} trace documents.")
    return documents


def load_observability_data():
    with open("data/sample_logs.json", "r") as f:
        logs = json.load(f)
    print(f"🔍 Loaded {len(logs)} logs from sample_logs.json")

    documents = []
    for log in logs:
        content = f"{log['message']} Context: {log['context']}"
        metadata = {
            "timestamp": log["timestamp"],
            "service": log["service"],
            "level": log["level"],
            "trace_id": log.get("trace_id", ""),
            "log_id": log["id"]
        }
        documents.append(Document(page_content=content, metadata=metadata))
    print(f"📄 Created {len(documents)} documents from logs.")
    return documents

def ingest_documents():
    openai_key = os.getenv("OPENAI_API_KEY")
    print("🔑 OpenAI Key loaded:", bool(openai_key))
    if not openai_key:
        raise ValueError("OPENAI_API_KEY is not set in this environment")
    
    print("🔍 Loading observability logs...")

    logs = load_observability_data()
    metrics = load_metrics_data()
    traces = load_traces_data()

    documents = logs + metrics + traces

    print(f"✅ Loaded {len(documents)} documents.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    print(f" 📄 Split into {len(chunks)} chunks.")

    print("✨ Generating embeddings...")
    embeddings = OpenAIEmbeddings(openai_api_key=openai_key)

    print("💾 Saving to Chroma index...")
    db = Chroma.from_documents(
    chunks,
    embeddings,
    persist_directory="vectorstore"
    )
    db.persist()
    print("📁 Saved index contents:", os.listdir("vectorstore"))

    print("✅ Ingestion complete.")


if __name__ == "__main__":
    ingest_documents()