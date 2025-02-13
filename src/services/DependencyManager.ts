interface DependencyNode {
  itemId: string;
  dependencies: string[];
  status: 'pending' | 'completed' | 'blocked';
  completionData?: ProgressUpdate;
}

class DependencyManager {
  private dependencyGraph: Map<string, DependencyNode> = new Map();

  async validateDependencies(
    checklistId: string,
    itemId: string
  ): Promise<{
    canProceed: boolean;
    blockers: string[];
    suggestions: ContextualPrompt[];
  }> {
    const node = this.dependencyGraph.get(itemId);
    if (!node) return { canProceed: true, blockers: [], suggestions: [] };

    const blockers = node.dependencies.filter(depId => {
      const depNode = this.dependencyGraph.get(depId);
      return !depNode || depNode.status !== 'completed';
    });

    if (blockers.length > 0) {
      const suggestions = await this.generateDependencySuggestions(blockers);
      return {
        canProceed: false,
        blockers,
        suggestions
      };
    }

    return { canProceed: true, blockers: [], suggestions: [] };
  }

  private async generateDependencySuggestions(
    blockers: string[]
  ): Promise<ContextualPrompt[]> {
    return blockers.map(blockerId => ({
      type: 'dependency',
      priority: 1,
      message: `Would you like to complete ${blockerId} first?`,
      requiredResponse: true,
      dependencies: [blockerId]
    }));
  }
} 