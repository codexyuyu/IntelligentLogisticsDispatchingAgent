"""Owner: AC | Status: scaffold
TODO[AC]: 只读快照与版本；冻结后的对象不原地修改。
尚未固定函数参数时在这里先记录职责；实现前复用 contracts 与 ports，不另发明接口。
"""
from app.common.errors import FeatureNotImplemented

def load_snapshot():
    raise FeatureNotImplemented('adapters.persistence.snapshots', 'AC')
