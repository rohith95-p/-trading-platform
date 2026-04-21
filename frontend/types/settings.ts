/**
 * Settings Types
 */

export interface UserSettings {
  userId: string;
  account: AccountSettings;
  trading: TradingSettings;
  notifications: NotificationSettings;
  display: DisplaySettings;
  createdAt: number;
  updatedAt: number;
}

export interface AccountSettings {
  email: string;
  twoFactorEnabled: boolean;
  passwordLastChanged?: number;
}

export interface TradingSettings {
  defaultLeverage: number;
  positionSizingMethod: 'fixed' | 'percentage' | 'kelly';
  maxPositionSize: number;
  maxDailyLoss: number;
  maxDrawdown: number;
}

export interface NotificationSettings {
  emailNotifications: boolean;
  emailFrequency: 'immediate' | 'daily' | 'weekly';
  alertTypes: string[];
  quietHoursStart?: string;
  quietHoursEnd?: string;
}

export interface DisplaySettings {
  theme: 'light' | 'dark' | 'auto';
  defaultTimeframe: '1m' | '5m' | '15m' | '1h' | '4h' | '1d';
  defaultChartType: 'candlestick' | 'ohlc' | 'line' | 'area';
  defaultIndicators: string[];
  language: string;
}
