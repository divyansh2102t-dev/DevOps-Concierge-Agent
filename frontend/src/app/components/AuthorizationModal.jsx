'use client';
import { useApp } from '../context/AppContext';
import { approveAction, denyAction } from '../services/api';

export default function AuthorizationModal() {
  const { state, dispatch } = useApp();
  const req = state.authRequest;
  if (!req) return null;

  async function handleApprove() {
    try {
      await approveAction(req.action_id);
    } catch {}
    dispatch({ type: 'CLEAR_AUTH_REQUEST' });
  }

  async function handleDeny() {
    try {
      await denyAction(req.action_id);
    } catch {}
    dispatch({ type: 'CLEAR_AUTH_REQUEST' });
  }

  return (
    <div className="modal-overlay">
      <div className="auth-modal">
        <h3>🔐 Authorization Required</h3>
        <p>The agent wants to perform an external action:</p>
        <p><strong>{req.tool || req.tool_name}</strong></p>
        <p>{req.description}</p>
        {req.arguments && (
          <div className="details">
            {JSON.stringify(req.arguments, null, 2)}
          </div>
        )}
        <div className="auth-modal-actions">
          <button className="btn-approve" onClick={handleApprove}>✓ Approve</button>
          <button className="btn-deny" onClick={handleDeny}>✕ Deny</button>
        </div>
      </div>
    </div>
  );
}
