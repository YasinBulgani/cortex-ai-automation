interface NotificationRequest {
  title: string;
  body: string;
  data?: Record<string, any>;
  badge?: number;
  sound?: string;
}

interface PushNotification {
  id: string;
  title: string;
  body: string;
  data?: Record<string, any>;
  timestamp: number;
  read: boolean;
}

type NotificationListener = (notification: PushNotification) => void;

class NotificationService {
  private notifications: PushNotification[] = [];
  private listeners: Set<NotificationListener> = new Set();
  private notificationId = 0;

  initialize(): void {
    console.log('Notification service initialized');
    // In a real app, this would initialize Firebase Cloud Messaging or similar
  }

  requestPermissions(): Promise<boolean> {
    // In a real app, this would request device notification permissions
    return Promise.resolve(true);
  }

  sendLocalNotification(request: NotificationRequest): void {
    const notification: PushNotification = {
      id: `local_${this.notificationId++}`,
      title: request.title,
      body: request.body,
      data: request.data,
      timestamp: Date.now(),
      read: false,
    };

    this.notifications.push(notification);
    this.emit(notification);
  }

  getNotifications(): PushNotification[] {
    return this.notifications;
  }

  getUnreadCount(): number {
    return this.notifications.filter(n => !n.read).length;
  }

  markAsRead(id: string): void {
    const notification = this.notifications.find(n => n.id === id);
    if (notification) {
      notification.read = true;
    }
  }

  markAllAsRead(): void {
    this.notifications.forEach(n => {
      n.read = true;
    });
  }

  clearNotification(id: string): void {
    const index = this.notifications.findIndex(n => n.id === id);
    if (index !== -1) {
      this.notifications.splice(index, 1);
    }
  }

  clearAll(): void {
    this.notifications = [];
  }

  on(listener: NotificationListener): void {
    this.listeners.add(listener);
  }

  off(listener: NotificationListener): void {
    this.listeners.delete(listener);
  }

  private emit(notification: PushNotification): void {
    this.listeners.forEach(listener => {
      try {
        listener(notification);
      } catch (error) {
        console.error('Error in notification listener:', error);
      }
    });
  }
}

export default new NotificationService();
