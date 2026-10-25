"""Owner: AC | Status: scaffold
TODO[AC]: 持久化领取/租约/超时；单独工作进程，不能HTTP内存排队。
尚未固定函数参数时在这里先记录职责；实现前复用 contracts 与 ports，不另发明接口。
"""
from app.common.errors import FeatureNotImplemented

def claim_job():
    raise FeatureNotImplemented('adapters.persistence.jobs', 'AC')
