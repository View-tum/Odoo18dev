import os
import ast

base_dir = r'C:\365_project\TheCool18e\Dev\custom\goldmints_addon-main\mrp_parallel_console'

class NPlusOneVisitor(ast.NodeVisitor):
    def __init__(self, filepath):
        self.filepath = filepath
        self.in_loop = False
        self.loop_node = None
        self.issues = []

    def visit_For(self, node):
        old_in_loop = self.in_loop
        old_loop_node = self.loop_node
        self.in_loop = True
        self.loop_node = node
        self.generic_visit(node)
        self.in_loop = old_in_loop
        self.loop_node = old_loop_node

    def visit_While(self, node):
        old_in_loop = self.in_loop
        old_loop_node = self.loop_node
        self.in_loop = True
        self.loop_node = node
        self.generic_visit(node)
        self.in_loop = old_in_loop
        self.loop_node = old_loop_node

    def visit_Call(self, node):
        if self.in_loop:
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
                if func_name in ['search', 'search_count', 'search_read', 'create']:
                    self.issues.append({
                        'line': node.lineno,
                        'method': func_name,
                        'code': ast.get_source_segment(open(self.filepath, encoding='utf-8').read(), node)
                    })
        self.generic_visit(node)

total_issues = 0
files_with_issues = {}

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source)
                visitor = NPlusOneVisitor(filepath)
                visitor.visit(tree)
                if visitor.issues:
                    rel_path = os.path.relpath(filepath, base_dir)
                    files_with_issues[rel_path] = visitor.issues
                    total_issues += len(visitor.issues)
            except SyntaxError:
                pass
            except Exception as e:
                pass

print(f'Found {total_issues} potential N+1 query issues in {len(files_with_issues)} files.')
print('-' * 40)
sorted_files = sorted(files_with_issues.items(), key=lambda x: len(x[1]), reverse=True)
for rel_path, issues in sorted_files:
    print(f'File: {rel_path} ({len(issues)} issues)')
    for issue in issues:
        code_snippet = issue["code"].replace(chr(10), " ").strip() if issue["code"] else ""
        if len(code_snippet) > 80:
            code_snippet = code_snippet[:77] + "..."
        print(f'  Line {issue["line"]}: .{issue["method"]}(...) -> {code_snippet}')
    print('')
