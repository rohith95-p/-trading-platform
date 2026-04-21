'use client';

import React, { useState, useEffect } from 'react';
import { UserSettings } from '@/types/settings';

/**
 * SettingsPanel Component
 * Manages user settings across account, trading, notifications, and display
 */
export const SettingsPanel: React.FC = () => {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'account' | 'trading' | 'notifications' | 'display'>('account');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/settings');
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      setSettings(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!settings) return;

    try {
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!response.ok) throw new Error('Failed to save settings');
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleExportSettings = () => {
    if (!settings) return;
    const json = JSON.stringify(settings, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'settings.json';
    a.click();
  };

  const handleImportSettings = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const imported = JSON.parse(text);
      setSettings(imported);
      setSaved(false);
    } catch (err) {
      setError('Failed to import settings');
    }
  };

  if (loading) {
    return <div className="settings-panel loading">Loading settings...</div>;
  }

  if (!settings) {
    return <div className="settings-panel error">Failed to load settings</div>;
  }

  return (
    <div className="settings-panel">
      <div className="settings-header">
        <h1>Settings</h1>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleExportSettings}>
            📥 Export
          </button>
          <label className="btn btn-secondary">
            📤 Import
            <input
              type="file"
              accept=".json"
              onChange={handleImportSettings}
              style={{ display: 'none' }}
            />
          </label>
          <button className="btn btn-primary" onClick={handleSaveSettings}>
            💾 Save Settings
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {saved && <div className="success-message">Settings saved successfully!</div>}

      <div className="settings-tabs">
        <button
          className={`tab ${activeTab === 'account' ? 'active' : ''}`}
          onClick={() => setActiveTab('account')}
        >
          Account
        </button>
        <button
          className={`tab ${activeTab === 'trading' ? 'active' : ''}`}
          onClick={() => setActiveTab('trading')}
        >
          Trading
        </button>
        <button
          className={`tab ${activeTab === 'notifications' ? 'active' : ''}`}
          onClick={() => setActiveTab('notifications')}
        >
          Notifications
        </button>
        <button
          className={`tab ${activeTab === 'display' ? 'active' : ''}`}
          onClick={() => setActiveTab('display')}
        >
          Display
        </button>
      </div>

      <div className="settings-content">
        {activeTab === 'account' && (
          <AccountSettings
            settings={settings}
            onChange={setSettings}
          />
        )}
        {activeTab === 'trading' && (
          <TradingSettings
            settings={settings}
            onChange={setSettings}
          />
        )}
        {activeTab === 'notifications' && (
          <NotificationSettings
            settings={settings}
            onChange={setSettings}
          />
        )}
        {activeTab === 'display' && (
          <DisplaySettings
            settings={settings}
            onChange={setSettings}
          />
        )}
      </div>
    </div>
  );
};

/**
 * AccountSettings Component
 */
const AccountSettings: React.FC<{
  settings: UserSettings;
  onChange: (settings: UserSettings) => void;
}> = ({ settings, onChange }) => {
  return (
    <div className="settings-section">
      <h2>Account Settings</h2>
      <div className="form-group">
        <label>Email</label>
        <input
          type="email"
          value={settings.account.email}
          onChange={e => onChange({
            ...settings,
            account: { ...settings.account, email: e.target.value }
          })}
        />
      </div>
      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={settings.account.twoFactorEnabled}
            onChange={e => onChange({
              ...settings,
              account: { ...settings.account, twoFactorEnabled: e.target.checked }
            })}
          />
          Enable Two-Factor Authentication
        </label>
      </div>
    </div>
  );
};

/**
 * TradingSettings Component
 */
const TradingSettings: React.FC<{
  settings: UserSettings;
  onChange: (settings: UserSettings) => void;
}> = ({ settings, onChange }) => {
  return (
    <div className="settings-section">
      <h2>Trading Preferences</h2>
      <div className="form-group">
        <label>Default Leverage</label>
        <input
          type="number"
          min="1"
          max="125"
          step="0.1"
          value={settings.trading.defaultLeverage}
          onChange={e => onChange({
            ...settings,
            trading: { ...settings.trading, defaultLeverage: parseFloat(e.target.value) }
          })}
        />
      </div>
      <div className="form-group">
        <label>Position Sizing Method</label>
        <select
          value={settings.trading.positionSizingMethod}
          onChange={e => onChange({
            ...settings,
            trading: { ...settings.trading, positionSizingMethod: e.target.value as any }
          })}
        >
          <option value="fixed">Fixed</option>
          <option value="percentage">Percentage</option>
          <option value="kelly">Kelly Criterion</option>
        </select>
      </div>
      <div className="form-group">
        <label>Max Position Size (%)</label>
        <input
          type="number"
          min="0"
          max="100"
          step="0.1"
          value={settings.trading.maxPositionSize}
          onChange={e => onChange({
            ...settings,
            trading: { ...settings.trading, maxPositionSize: parseFloat(e.target.value) }
          })}
        />
      </div>
      <div className="form-group">
        <label>Max Daily Loss ($)</label>
        <input
          type="number"
          min="0"
          step="100"
          value={settings.trading.maxDailyLoss}
          onChange={e => onChange({
            ...settings,
            trading: { ...settings.trading, maxDailyLoss: parseFloat(e.target.value) }
          })}
        />
      </div>
      <div className="form-group">
        <label>Max Drawdown (%)</label>
        <input
          type="number"
          min="0"
          max="100"
          step="0.1"
          value={settings.trading.maxDrawdown}
          onChange={e => onChange({
            ...settings,
            trading: { ...settings.trading, maxDrawdown: parseFloat(e.target.value) }
          })}
        />
      </div>
    </div>
  );
};

/**
 * NotificationSettings Component
 */
const NotificationSettings: React.FC<{
  settings: UserSettings;
  onChange: (settings: UserSettings) => void;
}> = ({ settings, onChange }) => {
  return (
    <div className="settings-section">
      <h2>Notification Preferences</h2>
      <div className="form-group">
        <label>
          <input
            type="checkbox"
            checked={settings.notifications.emailNotifications}
            onChange={e => onChange({
              ...settings,
              notifications: { ...settings.notifications, emailNotifications: e.target.checked }
            })}
          />
          Enable Email Notifications
        </label>
      </div>
      <div className="form-group">
        <label>Email Frequency</label>
        <select
          value={settings.notifications.emailFrequency}
          onChange={e => onChange({
            ...settings,
            notifications: { ...settings.notifications, emailFrequency: e.target.value as any }
          })}
        >
          <option value="immediate">Immediate</option>
          <option value="daily">Daily Digest</option>
          <option value="weekly">Weekly Digest</option>
        </select>
      </div>
      <div className="form-group">
        <label>Quiet Hours Start (HH:MM)</label>
        <input
          type="time"
          value={settings.notifications.quietHoursStart || ''}
          onChange={e => onChange({
            ...settings,
            notifications: { ...settings.notifications, quietHoursStart: e.target.value }
          })}
        />
      </div>
      <div className="form-group">
        <label>Quiet Hours End (HH:MM)</label>
        <input
          type="time"
          value={settings.notifications.quietHoursEnd || ''}
          onChange={e => onChange({
            ...settings,
            notifications: { ...settings.notifications, quietHoursEnd: e.target.value }
          })}
        />
      </div>
    </div>
  );
};

/**
 * DisplaySettings Component
 */
const DisplaySettings: React.FC<{
  settings: UserSettings;
  onChange: (settings: UserSettings) => void;
}> = ({ settings, onChange }) => {
  return (
    <div className="settings-section">
      <h2>Display Preferences</h2>
      <div className="form-group">
        <label>Theme</label>
        <select
          value={settings.display.theme}
          onChange={e => onChange({
            ...settings,
            display: { ...settings.display, theme: e.target.value as any }
          })}
        >
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          <option value="auto">Auto (System)</option>
        </select>
      </div>
      <div className="form-group">
        <label>Default Timeframe</label>
        <select
          value={settings.display.defaultTimeframe}
          onChange={e => onChange({
            ...settings,
            display: { ...settings.display, defaultTimeframe: e.target.value as any }
          })}
        >
          <option value="1m">1 Minute</option>
          <option value="5m">5 Minutes</option>
          <option value="15m">15 Minutes</option>
          <option value="1h">1 Hour</option>
          <option value="4h">4 Hours</option>
          <option value="1d">1 Day</option>
        </select>
      </div>
      <div className="form-group">
        <label>Default Chart Type</label>
        <select
          value={settings.display.defaultChartType}
          onChange={e => onChange({
            ...settings,
            display: { ...settings.display, defaultChartType: e.target.value as any }
          })}
        >
          <option value="candlestick">Candlestick</option>
          <option value="ohlc">OHLC</option>
          <option value="line">Line</option>
          <option value="area">Area</option>
        </select>
      </div>
      <div className="form-group">
        <label>Language</label>
        <select
          value={settings.display.language}
          onChange={e => onChange({
            ...settings,
            display: { ...settings.display, language: e.target.value }
          })}
        >
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="fr">French</option>
          <option value="de">German</option>
          <option value="ja">Japanese</option>
          <option value="zh">Chinese</option>
        </select>
      </div>
    </div>
  );
};

export default SettingsPanel;
