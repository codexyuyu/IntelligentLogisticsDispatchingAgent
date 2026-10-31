"""Pure intent boundary checks; no database, OR-Tools, network or model calls."""
import pytest

from logistics_agents.llm import LLMReply, ToolCall
from logistics_backend.application.natural_dispatch import parse_intent
from logistics_backend.errors import ServiceError


class Offline:
    configured = False


class MockDeepSeek:
    configured = True

    def __init__(self, arguments):
        import json
        self.arguments = json.dumps(arguments)

    def complete(self, messages, tools):
        assert tools[0]['function']['name'] == 'parse_dispatch_intent'
        return LLMReply(content='', model='fixture', tool_calls=(
            ToolCall('call_1', 'parse_dispatch_intent', self.arguments),))


def test_joint_command_offline_is_explicitly_rule_based():
    intent, parser = parse_intent('按当前场景的全部订单重新进行联合调度', Offline())
    assert intent == {'action': 'joint_dispatch', 'constraints': 'unchanged_checked_scenario'}
    assert parser == 'rule_based'


def test_unsupported_vehicle_assignment_is_rejected():
    with pytest.raises(ServiceError):
        parse_intent('指定一辆车去新的客户地址送货', Offline())
    with pytest.raises(ServiceError):
        parse_intent('指定车辆去新地点联合调度', MockDeepSeek({'action': 'joint_dispatch'}))


def test_delay_parsed_without_invented_vehicle_or_time():
    vehicle = 'b62f848e-dc0d-53df-a592-2127d8f8006a'
    intent, parser = parse_intent(f'车辆 {vehicle} 在第 396 秒延误 90 秒，请重规划', Offline())
    assert parser == 'rule_based'
    assert intent['vehicle_id'] == vehicle
    assert (intent['time_s'], intent['delay_s']) == (396, 90)
    with pytest.raises(ServiceError):
        parse_intent('车子延误90秒，重新调度', Offline())


def test_deepseek_function_call_is_validated():
    intent, parser = parse_intent('请重新联合调度', MockDeepSeek({'action': 'joint_dispatch'}))
    assert parser == 'deepseek_tool_call'
    assert intent['constraints'] == 'unchanged_checked_scenario'
    with pytest.raises(ServiceError):
        parse_intent('帮我安排车', MockDeepSeek({'action': 'delay_replan', 'time_s': True}))
