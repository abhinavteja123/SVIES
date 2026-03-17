export default function PipelineStep({ step, name, detail, status, icon: Icon, flags }) {
  return (
    <div className="pipeline-step">
      <div className={`pipeline-step-icon ${status}`}>
        {step}
      </div>
      <div className="pipeline-step-content">
        <div className="pipeline-step-name">{name}</div>
        {detail && <div className="pipeline-step-detail">{detail}</div>}
        {flags && flags.length > 0 && (
          <div className="pipeline-step-flags">
            {flags.map((flag) => (
              <span key={flag} className="pipeline-flag">
                {flag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
