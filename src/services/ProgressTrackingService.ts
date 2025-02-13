interface ProgressUpdate {
  itemId: string;
  status: 'completed' | 'skipped' | 'flagged';
  verificationMethod: 'manual' | 'ai_assisted';
  timestamp: Date;
  notes?: string;
  photoEvidence?: string;
}

class ProgressTrackingService {
  async updateProgress(
    checklistId: string,
    update: ProgressUpdate
  ): Promise<void> {
    await this.validateUpdate(update);
    await this.storeProgress(checklistId, update);
    await this.notifyDependentItems(checklistId, update);
    
    if (update.status === 'completed') {
      await this.checkCategoryCompletion(checklistId, update.itemId);
    }
  }
} 