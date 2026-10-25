"""Owner: AC | Status: scaffold
TODO[AC]: 区分计算、计划、执行状态；旧版本和非法迁移拒绝。
尚未固定函数参数时在这里先记录职责；实现前复用 contracts 与 ports，不另发明接口。
"""
from app.common.errors import FeatureNotImplemented

def transition():
    raise FeatureNotImplemented('domain.state_transitions', 'AC')
