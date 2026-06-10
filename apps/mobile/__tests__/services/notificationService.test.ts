import notificationService from '@services/notificationService';

describe('Notification Service', () => {
  beforeEach(() => {
    notificationService.clearAll();
  });

  it('should initialize successfully', () => {
    expect(() => notificationService.initialize()).not.toThrow();
  });

  it('should send local notification', () => {
    const listener = jest.fn();
    notificationService.on(listener);

    notificationService.sendLocalNotification({
      title: 'Test',
      body: 'Test notification',
    });

    expect(listener).toHaveBeenCalled();
    expect(notificationService.getNotifications().length).toBe(1);
  });

  it('should track unread count', () => {
    notificationService.sendLocalNotification({
      title: 'Test 1',
      body: 'Unread notification',
    });

    expect(notificationService.getUnreadCount()).toBe(1);

    const notifications = notificationService.getNotifications();
    notificationService.markAsRead(notifications[0].id);

    expect(notificationService.getUnreadCount()).toBe(0);
  });

  it('should clear notifications', () => {
    notificationService.sendLocalNotification({
      title: 'Test',
      body: 'To be cleared',
    });

    expect(notificationService.getNotifications().length).toBe(1);

    const notifications = notificationService.getNotifications();
    notificationService.clearNotification(notifications[0].id);

    expect(notificationService.getNotifications().length).toBe(0);
  });

  it('should mark all as read', () => {
    notificationService.sendLocalNotification({
      title: 'Test 1',
      body: 'Notification 1',
    });

    notificationService.sendLocalNotification({
      title: 'Test 2',
      body: 'Notification 2',
    });

    expect(notificationService.getUnreadCount()).toBe(2);

    notificationService.markAllAsRead();

    expect(notificationService.getUnreadCount()).toBe(0);
  });
});
