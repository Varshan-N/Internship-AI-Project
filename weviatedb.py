import weaviate, requests, os, pprint, time, difflib
from weaviate.classes.config import Property, DataType, ReferenceProperty
from langchain_weaviate import WeaviateVectorStore
from langchain.embeddings.base import Embeddings
from react_ast import code_snippet, parser,normalize_ast
from langchain.chains.retrieval import create_retrieval_chain
from langchain.llms.base import LLM
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from weaviate.classes.query import Filter, QueryReference

# Embedding mmodel
class QwenEmbedding(Embeddings):
    def embed_documents(self, code):
        return [self.embedding(t) for t in code]
    def embed_query(self, query):
        return self.embedding(query)
    def embedding(self,text):
        body={
            'model': 'dengcao/Qwen3-Embedding-8B:Q8_0',
            'prompt': text
        }
        headers={'content-type':'application/json'}
        response=requests.post('http://ai-test-3.csez.zohocorpin.com:11435/api/embeddings',
                               headers=headers,
                               json=body
                               )
        return response.json()['embedding']

embedding=QwenEmbedding()

# Qwen model
class Qwenmodel(LLM):
    def _call(self,prompt:str,stop=None):
        body = {
        "model": "qwen-2.5-32b-instruct-zlabs", 
        "messages": [
            {"role": "system", "content": "You are a helpful code generator. Convert the retrieved AST to a working React JSX code snippet."},
            {"role": "user", "content": prompt}
        ]
    }
        headers={'content-type':'application/json'}
        response=requests.post("http://infinity-sm4:8091/v1/chat/completions",
                               headers=headers,
                               json=body)
        output=response.json()
        return output['choices'][0]['message']['content']
    @property
    def _llm_type(self) -> str:
        return "qwen-custom"

llm=Qwenmodel()

#connecting to weviate
client= weaviate.connect_to_local()
collection_name = 'reactcode_snippet'

client.collections.delete(collection_name)
print('collection deleted')

# creating collection
if collection_name not in client.collections.list_all():
    client.collections.create(
        name=collection_name,
        description="AST of react code",
        vectorizer_config=None,
        properties=[
            Property(name='component_name', data_type=DataType.TEXT),
            Property(name='ast_code', data_type=DataType.TEXT),
            Property(name='org_code', data_type=DataType.TEXT),
        ]
    )
    print("Collection created.")
else:
    print("Collection already exists.")

collection=client.collections.get(collection_name)

#Create Cross-Reference property to create relationship between objects
collection.config.add_reference(
    ReferenceProperty(
        name='uses_components',
        target_collection=collection_name
    )
)
# collection.config.add_reference(
#         ReferenceProperty(
#         name='used_by',
#         target_collection=collection_name
#     )
# )

#Inserting data into weaviate client with relationship
elapsed_time=0
def import_with_relationship():
    ids = {}
    for item in code_snippet:
        start_time=time.time()
        vec=embedding.embed_query(item['ast_code'])
        end_time=time.time()
        obj = collection.data.insert(
            properties={
                'component_name': item['component_name'],
                'org_code': item['org_code'],
                'ast_code': item['ast_code']
            },
            vector=vec
        )
        ids[item['component_name']] = str(obj)
        _time=end_time-start_time
        global elapsed_time 
        elapsed_time+=_time
    print(f"Embedding took: {elapsed_time:.4f} seconds")

    # Filter out any None keys from component_names
    component_names = [name for name in ids.keys() if name]

    for item in code_snippet:
        source_uuid = ids[item['component_name']]
        for dep in item.get('used_components', []):
            if not dep:
                continue  # skip None or empty used components

            target_uuid = None

            # First try exact match
            if dep in ids:
                target_uuid = ids[dep]
            else:
                # Perform partial/fuzzy match using difflib
                # Ensure dep is a string
                if isinstance(dep, str):
                    matches = difflib.get_close_matches(dep, component_names, n=1, cutoff=0.6)
                    if matches:
                        target_uuid = ids[matches[0]]

            if target_uuid:
                collection.data.reference_add(
                    from_uuid=source_uuid,
                    from_property='uses_components',
                    to=target_uuid
                )

import_with_relationship()

#Graph Traversal to print the main component and its connected dependencies
def print_component_with_dependencies(component_name):
    """Retrieve a component and all its dependencies' source code"""
    try:
        # Get the collection
        collection = client.collections.get("reactcode_snippet")
        
        # 1. Get the component with its direct dependencies
        response = collection.query.fetch_objects(
            limit=1,
            filters=Filter.by_property("component_name").equal(component_name),
            return_properties=["component_name", "org_code"],
            return_references=[
                QueryReference(
                    link_on="uses_components",
                    return_properties=["component_name", "org_code"]
                )
            ]
        )
        
        if not response.objects:
            return f"Component {component_name} not found"

        main_component = response.objects[0]
        
        # 2. Extract all unique dependencies (BFS traversal)
        dependencies = []
        seen = set()
        queue = []
        
        # Initialize queue with direct dependencies
        if "uses_components" in main_component.references:
            for ref in main_component.references["uses_components"].objects:
                dep = ref.properties
                if dep["component_name"] not in seen:
                    seen.add(dep["component_name"])
                    dependencies.append(dep)
                    queue.append(dep["component_name"])
        
        # Process nested dependencies
        while queue:
            current_name = queue.pop(0)
            current_response = collection.query.fetch_objects(
                limit=1,
                filters=Filter.by_property("component_name").equal(current_name),
                return_properties=["component_name"],
                return_references=[
                    QueryReference(
                        link_on="uses_components",
                        return_properties=["component_name", "org_code"]
                    )
                ]
            )
            
            if not current_response.objects:
                continue
                
            current_component = current_response.objects[0]
            
            if "uses_components" in current_component.references:
                for ref in current_component.references["uses_components"].objects:
                    dep = ref.properties
                    if dep["component_name"] not in seen:
                        seen.add(dep["component_name"])
                        dependencies.append(dep)
                        queue.append(dep["component_name"])
        
        # 3. Format the output
        output = []
        
        # Main component first
        output.append(f"=== {main_component.properties['component_name']} ===\n")
        output.append(main_component.properties['org_code'])
        output.append("\n\n")
        
        # Then dependencies
        for dep in dependencies:
            output.append(f"=== {dep['component_name']} (used by {component_name}) ===\n")
            output.append(dep['org_code'])
            output.append("\n\n")
        
        return "".join(output)
    
    finally:
        # Ensure client is properly closed
        client.close()

#Weaviate langchain vector store to create a RAG retriever pipeline 
vectordb=WeaviateVectorStore(client=client,index_name=collection_name,text_key='ast_code',embedding=embedding)

#Retriever object 
retriever=vectordb.as_retriever(search_type='similarity_score_threshold',search_kwargs={'score_threshold':0.5,'k':2})

#RAG pipeline  to pass the context with user query to LLM
# prompt = ChatPromptTemplate.from_messages([
#         #("system", "You are a helpful code generator. Convert the given AST to a working React JSX code snippet."),
#         ("user", "Here is the AST:\n{context}\n\nTask:{input}\n\nRespond only with the final React JSX code without explanations.")
#     ])

# combine_docs_chain = create_stuff_documents_chain(llm, prompt)

# qa_chain = create_retrieval_chain(retriever, combine_docs_chain)

# User query
user_query = input('Ask Something:').strip()
#if the user query is in code snippet parse the query to ast
def parse_query(user_query):
    try:
        tree = parser.parse(user_query.encode('utf-8'))
        root = tree.root_node
        if root.child_count == 0 or 'ERROR' in root.sexp():
            print("Input code is incomplete or invalid JS code.")
            return None
        normalized_user_query = normalize_ast(root)
        return normalized_user_query
    except Exception:
        return None

ast_query = parse_query(user_query)

#If the user query is in complete code snippet retrieve the document based on code snippet

# if ast_query:
#     retriever = vectordb.as_retriever(search_type='similarity_score_threshold', search_kwargs={'score_threshold':0.5, 'k':2})
  
#     docs = retriever.invoke(ast_query)
#     print(docs)
#     if docs:
#         component_name= docs[0].metadata.get('component_name')
#         print(component_name)
#     else:
#         print('No relevant Data Found') 
# else:
#If the query is a natural english text query the database on the provided user query
docs = retriever.invoke(user_query)
print(docs)
retrieve_start_time=time.time()
if docs:
    component_name= docs[0].metadata.get('component_name')
    print(component_name)
    print(len(docs))
    result = print_component_with_dependencies(component_name)
    print(result)
else:
    print('No relevant Data found')
retrieve_end_time=time.time()
elapsed_time_retrieve= retrieve_end_time - retrieve_start_time
print(f"Embedding took: {elapsed_time_retrieve:.4f} seconds")    

client.close()

