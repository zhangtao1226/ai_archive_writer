"""目录结构由后端维护，模型仅生成节点正文。"""
from copy import deepcopy


def flatten(tree):
    result = []
    def walk(nodes, parents):
        for node in nodes:
            path = parents + [node['node_title']]
            result.append({'id':node['node_id'], 'title':node['node_title'],
                'content':node.get('content',''), 'generate_body':node.get('generate_content',True),
                'path':' → '.join(path),
                'writing_requirements':'仅写本章导语，不重复展开子章节' if node.get('children') else '展开当前章节具体内容'})
            walk(node.get('children',[]), path)
    walk(tree, [])
    return result


def fill(tree, contents):
    tree = deepcopy(tree)
    by_id = {row['section_id']:row for row in contents}
    def walk(nodes):
        for node in nodes:
            row = by_id.get(node['node_id'])
            if row:
                node['content'] = row['body']
                node['citations'] = row['citations']
                node['revision'] = row['revision']
            else:
                node['citations'] = []
            walk(node.get('children',[]))
    walk(tree)
    return tree
