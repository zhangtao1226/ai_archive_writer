# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : db.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm
import math
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Condition
from time import monotonic


class DatabasePool:
    def __init__(self, db_path, pool_size=5, acquire_timeout=10.0, busy_timeout=30.0):
        if isinstance(pool_size, bool) or not isinstance(pool_size, int) or pool_size < 1:
            raise ValueError('pool_size 必须为正整数')
        if any(not math.isfinite(v) or v < 0 for v in (acquire_timeout, busy_timeout)):
            raise ValueError('超时必须为有限非负数')
        if str(db_path) == ':memory:':
            raise ValueError('连接池需要文件数据库，不支持独立的 :memory: 连接')
        self.db_path = Path(db_path).expanduser().resolve()
        self.pool_size = pool_size
        self.acquire_timeout = acquire_timeout
        self.busy_timeout = busy_timeout
        self._condition = Condition()
        self._idle = []
        self._total = 0
        self._closed = False
        self._pid = os.getpid()

    def _check_process(self):
        if self._pid != os.getpid():
            raise RuntimeError('不能跨进程共享连接池，请在当前进程重新创建')

    def _new_connection(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=self.busy_timeout,
                               check_same_thread=False, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            # 普通回滚日志模式，不长期保留 -wal / -shm 文件。
            conn.execute('PRAGMA journal_mode = DELETE')
            return conn
        except BaseException:
            conn.close()
            raise

    def _acquire(self):
        self._check_process()
        deadline = monotonic() + self.acquire_timeout
        with self._condition:
            while True:
                if self._closed:
                    raise RuntimeError('连接池已关闭')
                if self._idle:
                    return self._idle.pop()
                if self._total < self.pool_size:
                    conn = self._new_connection()
                    self._total += 1
                    return conn
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError('等待数据库连接超时')
                self._condition.wait(remaining)

    def _release(self, conn):
        healthy = True
        try:
            if conn.in_transaction:
                conn.rollback()
        except sqlite3.Error:
            healthy = False
        with self._condition:
            if self._closed or not healthy:
                conn.close()
                self._total -= 1
            else:
                self._idle.append(conn)
            self._condition.notify_all()

    @contextmanager
    def connection(self):
        """借用连接；SQL 默认自动提交，多语句原子写入请使用 transaction。"""
        conn = self._acquire()
        try:
            yield conn
        finally:
            self._release(conn)

    @contextmanager
    def transaction(self, immediate=False):
        """成功提交，任何异常回滚。immediate=True 提前获取 SQLite 写锁。"""
        with self.connection() as conn:
            conn.execute('BEGIN IMMEDIATE' if immediate else 'BEGIN')
            try:
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def close(self):
        """禁止新借用并关闭空闲连接；已借出的连接归还时关闭。可重复调用。"""
        self._check_process()
        with self._condition:
            self._closed = True
            for conn in self._idle:
                conn.close()
                self._total -= 1
            self._idle.clear()
            self._condition.notify_all()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


_pools = {}
_pools_lock = Condition()


def get_database_pool(db_path):
    if str(db_path) == ':memory:':
        raise ValueError('公共连接池需要文件数据库')
    key = str(Path(db_path).expanduser().resolve())
    with _pools_lock:
        if key not in _pools or _pools[key]._closed:
            _pools[key] = DatabasePool(key)
        return _pools[key]


def close_database_pools():
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()


@contextmanager
def orm_session(pool, immediate=False):
    """ORM 使用公共池借出的连接，不创建第二个物理连接池。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    with pool.transaction(immediate=immediate) as raw:
        class BorrowedConnection:
            def __getattr__(self, name):
                return getattr(raw, name)

            def close(self):
                pass

            def commit(self):
                pass

            def rollback(self):
                pass

        engine = create_engine('sqlite://', creator=BorrowedConnection,
                               poolclass=StaticPool, pool_reset_on_return=None)
        try:
            with Session(engine, expire_on_commit=False) as session:
                yield session
                session.flush()
        finally:
            engine.dispose()
