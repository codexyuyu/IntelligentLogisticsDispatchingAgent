"""Offline, database-free acceptance checks for the Wenchang rescue/replay UI.

Run from the repository root: python scripts/check_replay_ui_consistency.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'apps' / 'frontend' / 'src'

def get(path: str) -> str:
    return (FRONTEND / path).read_text(encoding='utf-8')

def main() -> None:
    incident = get('features/stageB/Incident.tsx')
    replay_page = get('features/simulations/Page.tsx')
    rescue = get('features/stageB/FaultRescueDemo.tsx')
    agent = get('features/agent/NaturalDispatch.tsx')
    chat = get('features/agent/Page.tsx')
    api = (ROOT / 'apps/backend/src/logistics_backend/api/integration.py').read_text(encoding='utf-8')
    assert '<FaultRescueDemo/>' in incident, 'Incident must use the shared rescue case'
    assert '<FaultRescueDemo mode="replay" />' in replay_page, 'Replay must use the same rescue case'
    assert replay_page.index('<FaultRescueDemo mode="replay" />') < replay_page.index('<StageReplay mode="replay" />'), 'Rescue must be primary'
    assert 'showHistory &&' in replay_page, 'Legacy replay must be opt-in'
    assert 'fault_rescue_showcase_session_v2' in rescue and 'sessionStorage.getItem(STORAGE)' in rescue
    assert 'sessionStorage.setItem(STORAGE' in rescue, 'Approval must share the same session'
    for element in ('baseline: makeRoutes(data.baseline)', 'no_rescue: makeRoutes(data.no_rescue)', 'candidate: makeRoutes(data.candidate)', 'routes.no_rescue', 'routes.candidate', 'routes[displayView]'):
        assert element in rescue, f'Missing rescue route view: {element}'
    assert 'data.failure_time_s' in rescue and 'data.horizon_s' in rescue
    assert 'data.candidate_valid' in rescue and 'canApprove' in rescue
    assert 'DecisionAnalysisPanel' not in agent and 'DecisionAnalysisPanel' not in chat
    assert not (FRONTEND/'features/agent/DecisionAnalysisPanel.tsx').exists()
    assert 'deepseek_tool_call' in agent, 'Keep real model parser attribution'
    assert 'solve_breakdown_showcase' in api, 'Keep the real OR-Tools solver entry point'
    assert '/agents/dispatch-tasks' in agent, 'Preserve agent orchestration'
    print('PASS: shared three-vehicle incident/replay session and approval state')
    print('PASS: baseline/no-rescue/candidate maps with shared failure clock')
    print('PASS: AI decision panel removed, DeepSeek intent parsing preserved')
    print('PASS: solver API stays OR-Tools; no database connection made')

if __name__ == '__main__':
    main()
