
export type FlowStepState = 'done' | 'active' | 'pending' | 'failed';

export type FlowStep = {
  title: string;
  desc?: string;
  state: FlowStepState;
  detail?: string;
};

export default function FlowSteps({ steps }: { steps: FlowStep[] }) {
  return (
    <div className="flow-steps">
      {steps.map((step, i) => (
        <div className={`flow-step-item is-${step.state}`} key={`${step.title}-${i}`}>
          <span className="step-dot">{step.state === 'failed' ? '!' : step.state === 'done' ? '✓' : i + 1}</span>
          <div className="step-body">
            <b>{step.title}</b>
            {step.desc && <small>{step.desc}</small>}
            {step.detail && <code>{step.detail}</code>}
          </div>
        </div>
      ))}
    </div>
  );
}
