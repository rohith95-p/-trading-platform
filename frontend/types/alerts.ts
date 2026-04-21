/**
 * Alert Types
 */

export type AlertCondition = 'price_above' | 'price_below' | 'indicator_above' | 'indicator_below' | 'divergence_detected' | 'signal_generated';
export type NotificationMethod = 'email' | 'sms' | 'webhook' | 'in_app';
export type AlertStatus = 'armed' | 'triggered' | 'disabled';

export interface Alert {
  id: string;
  userId: string;
  asset: string;
  condition: AlertCondition;
  threshold: number;
  notificationMethod: NotificationMethod;
  status: AlertStatus;
  createdAt: number;
  triggeredAt?: number;
  templateId?: string;
}

export interface AlertTemplate {
  id: string;
  name: string;
  description?: string;
  condition: AlertCondition;
  threshold: number;
  notificationMethod: NotificationMethod;
  createdAt: number;
}

export interface AlertHistory {
  id: string;
  alertId: string;
  triggeredAt: number;
  value: number;
  notificationSent: boolean;
}

export interface AlertFormData {
  asset: string;
  condition: AlertCondition;
  threshold: number;
  notificationMethod: NotificationMethod;
  templateId?: string;
}
