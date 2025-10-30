from tree_sitter import Language, Parser
import os,pprint
from ast_relationship import import_map,parse_component_name
base_dir = 'D:/downloads1/vectordb_ast/test_react_data' 
imap = import_map(base_dir)

# Compile the JavaScript grammar (run once to generate shared library)
Language.build_library(
    'build/my-languages.so',  # Output shared library
    [
        './tree-sitter-javascript'  # Path to grammar
    ]
)

# Load the compiled language
JS_LANGUAGE = Language('build/my-languages.so', 'javascript')
parser = Parser()
parser.set_language(JS_LANGUAGE)

# Normalize the AST (convert to string, mask identifiers)
def normalize_ast(node):
    # if node.type == "identifier":
    #     return "var"
    # elif node.type == "string":
    #     return "str"
    if node.child_count == 0:
        return node.text.decode("utf-8")
    else:
        return f"({node.type} {' '.join([normalize_ast(child) for child in node.children])})"


# React Dataset 
code_snippet = []

for folder_path, dirs, files in os.walk(r'D:/downloads1/vectordb_ast/test_react_data'):
    for x in files:
        if x.endswith(('.js', '.jsx','.ts','.tsx')):
            file_path = os.path.join(folder_path, x)
            with open(file_path, 'r', encoding='utf-8') as file:
                code = file.read()
                ast_code = parser.parse(code.encode('utf-8'))
                root_node = ast_code.root_node
                normalized_ast_string = normalize_ast(root_node)
                comp_name = parse_component_name(code)
                used = imap[comp_name]['used'] if comp_name in imap else []
                code_snippet.append({
                    'component_name':comp_name,
                    'ast_code':normalized_ast_string,
                    'org_code':code,
                    'used_components': used
                })

# pprint.pprint(code_snippet)