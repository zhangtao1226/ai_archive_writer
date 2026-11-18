"""纯参数转换，不写数据库、不调用模型。"""
from copy import deepcopy
from schemas.research_request import ResearchRequest

def normalize_research_request(payload, context=None):
    if 'direction_model' not in payload:
        return deepcopy(payload)
    data = deepcopy(payload)
    if 'desciription' in data:
        typo = data.pop('desciription')
        if 'description' in data and data['description'] != typo:
            raise ValueError('description 与 desciription 内容冲突')
        data['description'] = typo
    request = ResearchRequest.model_validate(data)
    identity = {k: (context or {}).get(k) or getattr(request, k) for k in ('user_id', 'person', 'group')}
    count = 0
    def convert(nodes, depth=1, prefix=''):
        nonlocal count
        result = []
        for index, node in enumerate(nodes, 1):
            count += 1
            if count > 500 or depth > 20 or node.level != depth:
                raise ValueError('目录层级不一致或超过20层、500个节点')
            node_id = f'{prefix}.{index}' if prefix else str(index)
            result.append(
                dict(
                    node_id=node_id,
                    node_title=node.title,
                    content='\n\n'.join(node.content),
                    children=convert(node.children, depth+1, node_id)
                )
            )
        return result

    columns = []
    if request.direction_model == 'multi_level':
        tree = convert(request.nodes)
    else:
        for node in request.nodes:
            if node.level != 1 or node.children or node.content or node.source:
                raise ValueError('大事记 nodes 仅定义一级表头，content/source 必须为空')
            columns.append(node.title)
        if len(set(columns)) != len(columns):
            raise ValueError('大事记表头不能重复')
        tree = [dict(node_id='1', node_title=request.task_name, content='', children=[])]
    return dict(
        **identity,
        taskid=request.taskid,
        title=request.task_name,
        type='文本' if request.direction_model == 'multi_level' else '大事记',
        time_range=request.time_range,
        description=request.description,
        directory_template=tree,
        outline_snapshot={
            'direction_model': request.direction_model,
            'external_task_id': request.taskid,
            'columns': columns,
            'original_request': deepcopy(payload)
        }
    )
