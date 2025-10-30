import os,re
#component name extracter from the code snippet 
def parse_component_name(code):
    # Match function or class component name
    match = re.search(r'(function|class)\s+(\w+)\s*\(', code)
    if match:
        return match.group(2)
    # Match export default if directly named
    match = re.search(r'export\s+default\s+(\w+)', code)
    if match:
        return match.group(1)
    return None
# Code parser to split Import statement 
def code_parser(code):
    imports={}
    used_components=set()
    lines=code.split('\n')
    for line in lines:
        line=line.strip()
        if line.startswith('import'):
            parts=line.split('from')
            if len(parts)==2:
                name=parts[0].replace('import','').strip()
                path=parts[1].strip().strip(';').strip('"').strip("'")
                name=name.replace('{','').replace('}','').strip()
                imports[name]=path
    
    for x in imports.keys():
        if x in code:
            used_components.add(x)
    return imports, used_components
#Import map to store all the required details to traver the dependencies
def import_map(base_dir):
    import_map = {}      # Initialize empty dictionary to store all files' data

    for filedir,file_path,filenames in os.walk(base_dir):   # Loop through all files in folder
        for filename in filenames:
            if filename.endswith(('.js','.jsx','.ts','.tsx')):

                file_path = os.path.join(filedir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()             # Read the file content as text

                # Parse imports and used components in this file
                imports, used_components = code_parser(code)

                exported_name = parse_component_name(code)

                # Store both as a dict in import_map for this file
                name_without_ext=os.path.splitext(filename)[0]
                import_map[name_without_ext] = {
                    'imports': imports,
                    'used': used_components,
                    'path':file_path,
                    'exported':exported_name
                }

    return import_map   # Return final dictionary mapping each file ➔ its imports + used components