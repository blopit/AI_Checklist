import React, { useState, useEffect } from 'react';
import { ProgressSummary, DependencyView, CategoryProgress } from '../components';
import { progressService, dependencyManager } from '../services';
import { ChecklistProgress, DependencyNode } from '../types';

interface ProgressDashboardProps {
  checklistId: string;
  refreshInterval?: number;
  showDependencies?: boolean;
}

const ProgressDashboard: React.FC<ProgressDashboardProps> = ({
  checklistId,
  refreshInterval = 5000,
  showDependencies = true
}) => {
  const [progress, setProgress] = useState<ChecklistProgress>();
  const [dependencies, setDependencies] = useState<DependencyNode[]>();

  useEffect(() => {
    const fetchProgress = async () => {
      const progressData = await progressService.getProgress(checklistId);
      const dependencyData = showDependencies ? 
        await dependencyManager.getDependencies(checklistId) : 
        undefined;

      setProgress(progressData);
      setDependencies(dependencyData);
    };

    fetchProgress();
    const interval = setInterval(fetchProgress, refreshInterval);
    return () => clearInterval(interval);
  }, [checklistId, refreshInterval, showDependencies]);

  return (
    <div className="progress-dashboard">
      <ProgressSummary progress={progress} />
      {showDependencies && (
        <DependencyView 
          dependencies={dependencies}
          onItemClick={handleItemClick}
        />
      )}
      <CategoryProgress 
        categories={progress?.categories}
        onCategoryClick={handleCategoryClick}
      />
    </div>
  );
};

export default ProgressDashboard; 