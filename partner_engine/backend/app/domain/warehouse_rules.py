"""Owner: AC | Status: scaffold
TODO[AC]: 独立检查作业先后、互斥、容量与已执行事实。
尚未固定函数参数时在这里先记录职责；实现前复用 contracts 与 ports，不另发明接口。
"""
from app.common.errors import FeatureNotImplemented

def validate_warehouse():
    raise FeatureNotImplemented('domain.warehouse_rules', 'AC')
