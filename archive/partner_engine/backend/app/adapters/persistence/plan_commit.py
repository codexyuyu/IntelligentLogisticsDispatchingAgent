"""Owner: AC | Status: scaffold
TODO[AC]: 锁新旧资源，净占用校验，幂等键与事务回滚。
尚未固定函数参数时在这里先记录职责；实现前复用 contracts 与 ports，不另发明接口。
"""
from app.common.errors import FeatureNotImplemented

def commit_plan():
    raise FeatureNotImplemented('adapters.persistence.plan_commit', 'AC')
