'use client';

import React, { useState, useEffect } from 'react';
import { Alert, AlertTemplate, AlertHistory, AlertFormData, AlertCondition, NotificationMethod } from '@/types/alerts';

/**
 * AlertManagement Component
 * Manages alert creation, editing, deletion, and history
 */
export const AlertManagement: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [templates, setTemplates] = useState<AlertTemplate[]>([]);
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);

  useEffect(() => {
    fetchAlerts();
    fetchTemplates();
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await fetch('/api/alerts');
      if (!response.ok) throw new Error('Failed to fetch alerts');
      const data = await response.json();
      setAlerts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/alerts/templates');
      if (!response.ok) throw new Error('Failed to fetch templates');
      const data = await response.json();
      setTemplates(data);
    } catch (err) {
      console.error('Error fetching templates:', err);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/alerts/history');
      if (!response.ok) throw new Error('Failed to fetch history');
      const data = await response.json();
      setHistory(data);
    } catch (err) {
      console.error('Error fetching history:', err);
    }
  };

  const handleCreateAlert = async (formData: AlertFormData) => {
    try {
      const response = await fetch('/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error('Failed to create alert');
      const newAlert = await response.json();
      setAlerts([...alerts, newAlert]);
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleUpdateAlert = async (alertId: string, formData: AlertFormData) => {
    try {
      const response = await fetch(`/api/alerts/${alertId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error('Failed to update alert');
      const updatedAlert = await response.json();
      setAlerts(alerts.map(a => (a.id === alertId ? updatedAlert : a)));
      setEditingAlert(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleDeleteAlert = async (alertId: string) => {
    try {
      const response = await fetch(`/api/alerts/${alertId}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Failed to delete alert');
      setAlerts(alerts.filter(a => a.id !== alertId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  if (loading) {
    return <div className="alert-management loading">Loading alerts...</div>;
  }

  return (
    <div className="alert-management">
      <div className="management-header">
        <h1>Alert Management</h1>
        <div className="header-actions">
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            ➕ Create Alert
          </button>
          <button className="btn btn-secondary" onClick={() => {
            setShowHistory(!showHistory);
            if (!showHistory) fetchHistory();
          }}>
            📋 History
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {showForm && (
        <AlertForm
          templates={templates}
          onSubmit={handleCreateAlert}
          onCancel={() => setShowForm(false)}
        />
      )}

      {editingAlert && (
        <AlertForm
          alert={editingAlert}
          templates={templates}
          onSubmit={(data) => handleUpdateAlert(editingAlert.id, data)}
          onCancel={() => setEditingAlert(null)}
        />
      )}

      <div className="alerts-section">
        <h2>Active Alerts ({alerts.length})</h2>
        {alerts.length === 0 ? (
          <div className="empty-state">No alerts created yet</div>
        ) : (
          <div className="alerts-list">
            {alerts.map(alert => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onEdit={() => setEditingAlert(alert)}
                onDelete={() => handleDeleteAlert(alert.id)}
              />
            ))}
          </div>
        )}
      </div>

      {showHistory && (
        <div className="history-section">
          <h2>Alert History</h2>
          <AlertHistoryTable history={history} />
        </div>
      )}
    </div>
  );
};

/**
 * AlertForm Component
 */
const AlertForm: React.FC<{
  alert?: Alert;
  templates: AlertTemplate[];
  onSubmit: (data: AlertFormData) => void;
  onCancel: () => void;
}> = ({ alert, templates, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState<AlertFormData>({
    asset: alert?.asset || '',
    condition: alert?.condition || 'price_above',
    threshold: alert?.threshold || 0,
    notificationMethod: alert?.notificationMethod || 'email',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="alert-form-container">
      <form className="alert-form" onSubmit={handleSubmit}>
        <h3>{alert ? 'Edit Alert' : 'Create New Alert'}</h3>

        <div className="form-group">
          <label>Asset</label>
          <input
            type="text"
            placeholder="e.g., BTC/USD"
            value={formData.asset}
            onChange={e => setFormData({ ...formData, asset: e.target.value })}
            required
          />
        </div>

        <div className="form-group">
          <label>Condition</label>
          <select
            value={formData.condition}
            onChange={e => setFormData({ ...formData, condition: e.target.value as AlertCondition })}
          >
            <option value="price_above">Price Above</option>
            <option value="price_below">Price Below</option>
            <option value="indicator_above">Indicator Above</option>
            <option value="indicator_below">Indicator Below</option>
            <option value="divergence_detected">Divergence Detected</option>
            <option value="signal_generated">Signal Generated</option>
          </select>
        </div>

        <div className="form-group">
          <label>Threshold</label>
          <input
            type="number"
            step="0.01"
            value={formData.threshold}
            onChange={e => setFormData({ ...formData, threshold: parseFloat(e.target.value) })}
            required
          />
        </div>

        <div className="form-group">
          <label>Notification Method</label>
          <select
            value={formData.notificationMethod}
            onChange={e => setFormData({ ...formData, notificationMethod: e.target.value as NotificationMethod })}
          >
            <option value="email">Email</option>
            <option value="sms">SMS</option>
            <option value="webhook">Webhook</option>
            <option value="in_app">In-App</option>
          </select>
        </div>

        <div className="form-group">
          <label>Use Template (Optional)</label>
          <select onChange={e => {
            const template = templates.find(t => t.id === e.target.value);
            if (template) {
              setFormData({
                asset: formData.asset,
                condition: template.condition,
                threshold: template.threshold,
                notificationMethod: template.notificationMethod,
              });
            }
          }}>
            <option value="">Select a template...</option>
            {templates.map(template => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary">
            {alert ? 'Update Alert' : 'Create Alert'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

/**
 * AlertCard Component
 */
const AlertCard: React.FC<{
  alert: Alert;
  onEdit: () => void;
  onDelete: () => void;
}> = ({ alert, onEdit, onDelete }) => {
  const statusColors = {
    armed: '#10b981',
    triggered: '#f59e0b',
    disabled: '#6b7280',
  };

  return (
    <div className="alert-card">
      <div className="alert-header">
        <h4>{alert.asset}</h4>
        <span className="status" style={{ backgroundColor: statusColors[alert.status] }}>
          {alert.status}
        </span>
      </div>
      <div className="alert-details">
        <p><strong>Condition:</strong> {alert.condition}</p>
        <p><strong>Threshold:</strong> {alert.threshold}</p>
        <p><strong>Notification:</strong> {alert.notificationMethod}</p>
        {alert.triggeredAt && (
          <p><strong>Last Triggered:</strong> {new Date(alert.triggeredAt).toLocaleString()}</p>
        )}
      </div>
      <div className="alert-actions">
        <button className="btn btn-sm btn-secondary" onClick={onEdit}>
          ✏️ Edit
        </button>
        <button className="btn btn-sm btn-danger" onClick={onDelete}>
          🗑️ Delete
        </button>
      </div>
    </div>
  );
};

/**
 * AlertHistoryTable Component
 */
const AlertHistoryTable: React.FC<{ history: AlertHistory[] }> = ({ history }) => {
  return (
    <table className="history-table">
      <thead>
        <tr>
          <th>Alert ID</th>
          <th>Triggered At</th>
          <th>Value</th>
          <th>Notification Sent</th>
        </tr>
      </thead>
      <tbody>
        {history.map(entry => (
          <tr key={entry.id}>
            <td>{entry.alertId}</td>
            <td>{new Date(entry.triggeredAt).toLocaleString()}</td>
            <td>{entry.value.toFixed(2)}</td>
            <td>{entry.notificationSent ? '✅' : '❌'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default AlertManagement;
