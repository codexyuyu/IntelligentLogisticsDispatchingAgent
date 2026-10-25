"""Owner: AC | Status: scaffold
TODO[AC]: 有界并发与数据库租约；依赖未实现时明确退出。
尚未固定函数参数时在这里先记录职责；实现前复用 contracts 与 ports，不另发明接口。
"""
from app.common.errors import FeatureNotImplemented

def run_worker():
    raise FeatureNotImplemented('worker', 'AC')
