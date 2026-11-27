# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : material_catalog_service.py
# @Desc      : 素材目录 API 与数据转换；不猜测附件服务器本地路径
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

import json
from urllib.parse import quote
import requests
from functools import wraps
from time import monotonic
from core.LoggerDetector import logger
from services.reference_material_service import read_local_attachment


def iter_materials(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise ValueError('素材分类接口 data 必须是数组')

    seen = set()
    def walk(node):
        if not isinstance(node, dict) or not isinstance(node.get('catalog_info'), dict):
            raise ValueError('素材目录结构无效')

        category = node.get('catalog_id')
        if not isinstance(category,str) or not category:
            raise ValueError('目录缺少 catalog_id')

        rows = node.get('catalog_data',[])
        children = node.get('children',[])
        if not isinstance(rows,list) or not isinstance(children,list):
            raise ValueError('目录数据必须为数组')

        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id']:
                raise ValueError('素材缺少 id')

            key=(category,row['id'])
            if key in seen:
                continue
            seen.add(key)
            yield category,node['catalog_info'],row
        for child in children:
            yield from walk(child)
    for root in payload['data']:
        if isinstance(root,dict) and root.get('catalog_info',{}).get('catalog_name') == '个人素材库':
            continue
        yield from walk(root)


def material_text(info, row):
    fields = info.get('catalog_fields') or []
    aliases = {f['name']:f.get('alias') or f['name'] for f in fields}
    ignored = {'id','attachments','created_by','created_at','updated_at','sync_status'}
    lines = [f"目录：{info.get('catalog_path','')}"]
    for key,value in row.items():
        if key not in ignored and value is not None and value != '':
            lines.append(f"{aliases.get(key,key)}：{value if isinstance(value,(str,int,float)) else json.dumps(value,ensure_ascii=False)}")
    if len(lines)==1:
        raise ValueError('素材没有可入库的档案字段')
    return '\n'.join(lines)


def log_material_operation(operation):
    """只记录业务标识和统计信息，不输出请求头、URL参数或正文。"""
    def decorate(func):
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            started = monotonic()
            data = args[0] if args and isinstance(args[0], dict) else {}
            if operation == '素材回调':
                context = f"category_id={data.get('category_id')} material_id={data.get('material_id')} success={data.get('success')}"
            elif operation == '附件读取':
                context = f"attachment_id={data.get('attachment_id')} mode={'http' if self.config.material_attachment_download_path else 'local'}"
            else:
                context = f"contain_row={self.config.material_contain_row} unlimited_row={self.config.material_unlimited_row}"
            logger.info(f"{operation}开始 {context}")

            try:
                result = func(self, *args, **kwargs)
            except InterruptedError:
                logger.warning(f"{operation}中断 {context} elapsed={monotonic()-started:.3f}s")
                raise

            except Exception as exc:
                response = getattr(exc, 'response', None)
                status = getattr(response, 'status_code', None)
                logger.error(f"{operation}失败 {context} error_type={type(exc).__name__} http_status={status} elapsed={monotonic()-started:.3f}s")
                raise

            detail = ''
            if isinstance(result, bytes):
                detail = f" bytes={len(result)}"
            elif isinstance(result, dict) and isinstance(result.get('data'), list):
                detail = f" root_count={len(result['data'])}"

            logger.info(f"{operation}完成 {context}{detail} elapsed={monotonic()-started:.3f}s")
            return result
        return wrapped
    return decorate


class MaterialCatalogClient:
    def __init__(self, config):
        self.config=config
        self.base=config.material_api_base_url.rstrip('/')
        self.client=requests.Session()
        self.client.headers.update(
            {
                'X-API-Key':getattr(config, 'material_api_key', 'erren_lantai_2026')
            }
        )
        self.timeout=config.material_api_timeout_seconds

    def _check_response(self, response):
        response.raise_for_status()
        if 300 <= response.status_code < 400:
            raise ValueError('素材接口返回重定向，请配置实际接口地址')

    def __enter__(self): return self

    def __exit__(self,*args): self.client.close()

    @log_material_operation('素材分类拉取')
    def categories(self):
        r = self.client.get(
            self.base + self.config.material_api_url,
            params={
                'contain_row':str(self.config.material_contain_row).lower(),
                'unlimited_row':self.config.material_unlimited_row
            },
            timeout=self.timeout,
            allow_redirects=False
        )

        print(f"content = {r.content.decode('utf-8')}")
        self._check_response(r)
        return r.json()

    @log_material_operation('素材回调')
    def callback(self,payload):
        r = self.client.post(
            self.base + self.config.material_api_callback_url,
            json=payload,
            timeout=self.timeout,
            allow_redirects=False
        )

        self._check_response(r)

        if r.content:
            body=r.json()
            logger.info(f"素材回调结果: {body}")

            if isinstance(body,dict) and (body.get('success') is False or ('code' in body and body['code'] not in (0,200,'0','200'))):
                raise ValueError('素材回调业务响应失败')

    @log_material_operation('附件读取')
    def attachment(self,attachment,allowed):
        path=self.config.material_attachment_download_path

        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('附件下载接口必须为同一素材服务的相对路径')

        url = self.base + path + "/" + attachment['attachment_id']
        print(f"下载附件 url = {url}")
        data=bytearray()

        with self.client.get(url, stream=True, timeout=self.timeout, allow_redirects=False) as response:
            self._check_response(response)
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not allowed(): raise InterruptedError('入库窗口结束')
                data.extend(chunk)
                if len(data)>self.config.material_attachment_max_bytes:
                    logger.warning("附件超过大小限制")
                    raise ValueError('附件超过大小限制')
        return bytes(data)
