"""Owner: AC | Status: scaffold
TODO[AC]: 库存守恒、隔离、实物与预留分离；只依赖标准库。
尚未固定函数参数时在这里先记录职责；实现前复用 contracts 与 ports，不另发明接口。
"""
from app.common.errors import FeatureNotImplemented

def validate_inventory():
    raise FeatureNotImplemented('domain.inventory', 'AC')
