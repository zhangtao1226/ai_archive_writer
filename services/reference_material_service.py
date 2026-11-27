# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : reference_material_service.py
# @Desc     : 解析素材详情响应；HTTP 地址及鉴权确认后再接入调用方
# @Time     : 2026/11/18 16:07
# @Software : PyCharm

from pathlib import Path
from rag.readers import extract_text


def parse_material_response(payload, reference, read_attachment):
    """校验返回的分类和素材ID，提取所有附件为模型引用资料。

    read_attachment(attachment) 返回 bytes；由调用方提供本地读取或下载实现。
    任一附件失败即报错，避免静默遗漏用户明确指定的资料。
    """
    if not isinstance(payload, dict) or not isinstance(payload.get('material'), dict):
        raise ValueError('素材详情响应格式无效')

    material = payload['material']
    if payload.get('catalog_id') != reference['category_id'] or material.get('id') != reference['material_id']:
        raise ValueError('素材详情的分类或素材ID与请求不一致')

    attachments = material.get('attachments')
    if not isinstance(attachments, list) or not attachments:
        raise ValueError('引用素材没有可读取附件')

    hits = []
    for attachment in attachments:
        if not isinstance(attachment, dict) or not attachment.get('attachment_id'):
            raise ValueError('附件信息或附件ID缺失')

        extension = str(attachment.get('file_ext', '')).lower().lstrip('.')
        if extension not in {'pdf', 'docx', 'txt', 'md'}:
            raise ValueError(f'暂不支持引用附件格式：{extension}')

        text = extract_text(read_attachment(attachment), '.' + extension)
        hits.append({
            'id': f"{payload['catalog_id']}:{material['id']}:{attachment['attachment_id']}",
            'text': text,
            'metadata': {
                'category_id': payload['catalog_id'],
                'material_id': material['id'],
                'catalog_name': payload.get('catalog_name', ''),
                'catalog_path': payload.get('catalog_path', ''),
                'title': material.get('title', ''),
                'attachment_id': attachment['attachment_id'],
                'file_name': attachment.get('file_name', ''),
                'source': attachment.get('file_path', ''),
            },
        })
    return hits


def read_local_attachment(attachment, allowed_root, max_bytes=20 * 1024 * 1024):
    """仅读取配置素材根目录内的文件，限制体积；不可读取时明确报错。"""
    root = Path(allowed_root).expanduser().resolve(strict=True)
    raw = attachment.get('file_path')
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('附件路径缺失')

    path = Path(raw).expanduser().resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('附件不在配置的素材目录内或不是文件')

    with path.open('rb') as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError('附件超过单文件读取大小限制')

    return data


class ReferenceMaterialService:
    """通过素材详情 GET 接口获取附件信息，再读取服务主机可见的附件。"""

    def __init__(self, config):
        """保存接口、鉴权、附件根目录及大小限制配置。"""
        self.config = config

    def validate_config(self):
        """在调用模型前检查必要部署配置，避免误用相对 URL 或任意目录。"""
        from urllib.parse import urlsplit
        base = getattr(self.config, 'material_api_base_url', '')
        parsed = urlsplit(base)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError('请配置 material_api_base_url 为素材服务的 HTTP(S) 地址')

        root = getattr(self.config, 'material_attachment_root', '')
        if not root or not Path(root).is_dir():
            raise ValueError('请配置可由本机读取的 material_attachment_root 素材根目录')

    def load(self, references, user_id):
        """逐个获取指定素材；全部成功才返回，重复 ID 对仅请求一次。

        user_id 为调用方身份上下文；当前上游协议没有用户字段，不擅自传递。
        """
        import httpx
        self.validate_config()
        token = self.config.material_api_token
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        url = self.config.material_api_base_url.rstrip('/') + '/api/v1/public/materials/detail'
        results, seen = [], set()
        def read(attachment):
            """按配置的根目录与体积限制读取单个附件。"""
            return read_local_attachment(attachment, self.config.material_attachment_root,
                                         self.config.material_attachment_max_bytes)
        with httpx.Client(timeout=self.config.material_api_timeout_seconds, headers=headers) as client:
            for reference in references:
                key = (reference['category_id'], reference['material_id'])
                if key in seen:
                    continue
                seen.add(key)
                response = client.get(url, params={'category_id':key[0], 'material_id':key[1]})
                response.raise_for_status()
                results.extend(parse_material_response(response.json(), reference, read))
        return results
