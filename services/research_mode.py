"""统一生成与查询的编研类型判断，防止大事记退回正文流程。"""
def resolve_research_mode(snapshot, research_type=''):
    if not isinstance(snapshot, dict):
        raise ValueError('任务大纲快照必须是对象')
    original = snapshot.get('original_request') or {}
    if not isinstance(original, dict):
        raise ValueError('原始立项参数格式无效')
    saved_mode = snapshot.get('direction_model')
    original_mode = original.get('direction_model')
    if saved_mode and original_mode and saved_mode != original_mode:
        raise ValueError('任务类型与原始立项参数冲突')
    mode = saved_mode or original_mode
    if research_type in ('大事记', '大事件'):
        if mode and mode != 'single_node':
            raise ValueError('大事记类型与 direction_model 冲突')
        mode = 'single_node'
    mode = mode or 'multi_level'
    if mode not in ('multi_level', 'single_node'):
        raise ValueError('任务 direction_model 无效')
    columns = snapshot.get('columns')
    if mode == 'single_node':
        if columns is None:
            nodes = original.get('nodes', [])
            if not isinstance(nodes, list) or any(not isinstance(n, dict) for n in nodes):
                raise ValueError('大事记原始表头格式无效')
            columns = [n.get('title') for n in nodes]
        if not isinstance(columns, list) or not columns or any(not isinstance(c, str) or not c.strip() for c in columns) or len(set(columns)) != len(columns):
            raise ValueError('大事记缺少有效表头，不能按文本生成，请检查立项快照')
    return mode, columns or []
