"""
Script to check ChromaDB memory contents
Run: python check_memory.py
"""

import chromadb
from datetime import datetime

def main():
    print("=" * 60)
    print("CMMS Query Memory Inspector")
    print("=" * 60)
    print()
    
    try:
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path="./query_memory_chroma")
        collection = client.get_or_create_collection(name="cmms_query_memory")
        
        # Get count
        count = collection.count()
        print(f"📊 Total queries stored: {count}")
        print()
        
        if count == 0:
            print("⚠️  No queries found in memory yet.")
            print("   Queries will be saved after successful LLM generations.")
            return
        
        # Get all items
        results = collection.get(
            include=["documents", "metadatas"]
        )
        
        print("=" * 60)
        print("Stored Queries:")
        print("=" * 60)
        
        for idx, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"]), 1):
            print(f"\n{'─' * 60}")
            print(f"Query #{idx}")
            print(f"{'─' * 60}")
            print(f"🔍 User Query: {doc}")
            print(f"📦 Resource: {meta.get('resource', 'N/A')}")
            print(f"🤖 Model: {meta.get('model', 'N/A')}")
            print(f"⏱️  Execution Time: {meta.get('execution_time_ms', 'N/A')}ms")
            print(f"📅 Created: {meta.get('created_at', 'N/A')}")
            print(f"✅ Status: {meta.get('status', 'N/A')}")
            print(f"\n📝 Pipeline:")
            
            pipeline = meta.get('pipeline', 'N/A')
            if pipeline != 'N/A':
                import json
                try:
                    formatted = json.dumps(json.loads(pipeline), indent=2)
                    print(formatted)
                except:
                    print(pipeline)
        
        print(f"\n{'=' * 60}")
        print(f"✅ Total: {count} queries in memory")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\nMake sure ChromaDB is installed:")
        print(f"  pip install chromadb")


if __name__ == "__main__":
    main()