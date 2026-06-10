import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { apiClient } from './apiClient';

export interface OfflineAction {
  id: string;
  type: 'CREATE' | 'UPDATE' | 'DELETE';
  resource: string;
  resourceId?: string;
  data: any;
  timestamp: number;
  retries: number;
}

class OfflineSyncService {
  private queue: OfflineAction[] = [];
  private isOnline = false;
  private isSyncing = false;
  private syncInterval: NodeJS.Timeout | null = null;
  private maxRetries = 3;

  async initialize(): Promise<void> {
    // Load queue from storage
    await this.loadQueue();

    // Monitor connectivity
    NetInfo.addEventListener(state => {
      const wasOnline = this.isOnline;
      this.isOnline = state.isConnected ?? false;

      if (this.isOnline && !wasOnline) {
        console.log('Connectivity restored, syncing offline changes...');
        this.startSync();
      }
    });

    // Check initial connectivity
    const state = await NetInfo.fetch();
    this.isOnline = state.isConnected ?? false;
  }

  addAction(action: Omit<OfflineAction, 'id' | 'timestamp' | 'retries'>): void {
    const offlineAction: OfflineAction = {
      ...action,
      id: `${action.resource}_${Date.now()}_${Math.random()}`,
      timestamp: Date.now(),
      retries: 0,
    };

    this.queue.push(offlineAction);
    this.saveQueue();
    console.log(`Added offline action: ${offlineAction.id}`);
  }

  async sync(): Promise<void> {
    if (this.isSyncing || !this.isOnline) {
      return;
    }

    this.isSyncing = true;

    try {
      const failedActions: OfflineAction[] = [];

      for (const action of this.queue) {
        try {
          await this.syncAction(action);
        } catch (error) {
          action.retries++;
          if (action.retries < this.maxRetries) {
            failedActions.push(action);
          } else {
            console.error(`Max retries reached for action ${action.id}`);
          }
        }
      }

      this.queue = failedActions;
      await this.saveQueue();

      console.log(`Sync completed. ${this.queue.length} actions remaining.`);
    } finally {
      this.isSyncing = false;
    }
  }

  private async syncAction(action: OfflineAction): Promise<void> {
    const { type, resource, resourceId, data } = action;

    switch (type) {
      case 'CREATE':
        await apiClient.post(`/api/v1/${resource}`, data);
        break;
      case 'UPDATE':
        await apiClient.put(`/api/v1/${resource}/${resourceId}`, data);
        break;
      case 'DELETE':
        await apiClient.delete(`/api/v1/${resource}/${resourceId}`);
        break;
    }
  }

  private startSync(): void {
    if (this.syncInterval) {
      return;
    }

    this.sync();

    this.syncInterval = setInterval(() => {
      if (this.isOnline) {
        this.sync();
      }
    }, 30000); // Sync every 30 seconds
  }

  private stopSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  private async saveQueue(): Promise<void> {
    try {
      await AsyncStorage.setItem('neurex_offline_queue', JSON.stringify(this.queue));
    } catch (error) {
      console.error('Failed to save offline queue:', error);
    }
  }

  private async loadQueue(): Promise<void> {
    try {
      const data = await AsyncStorage.getItem('neurex_offline_queue');
      if (data) {
        this.queue = JSON.parse(data);
        console.log(`Loaded ${this.queue.length} offline actions`);
      }
    } catch (error) {
      console.error('Failed to load offline queue:', error);
    }
  }

  getQueueLength(): number {
    return this.queue.length;
  }

  getQueueItems(): OfflineAction[] {
    return this.queue;
  }

  clearQueue(): void {
    this.queue = [];
    this.saveQueue();
  }

  isConnected(): boolean {
    return this.isOnline;
  }
}

export default new OfflineSyncService();
