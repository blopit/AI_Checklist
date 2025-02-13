class AIPromptService {
  private readonly basePrompts = {
    clarification: "I notice you mentioned {topic}. Could you please clarify {detail}?",
    suggestion: "Based on {condition}, you might want to check {item}",
    warning: "Important: {safety_item} requires verification before proceeding"
  };

  async generateContextualPrompt(
    checklistItem: ChecklistItem,
    context: ChecklistContext
  ): Promise<string> {
    const promptTemplate = await this.selectAppropriatePrompt(checklistItem, context);
    return this.fillPromptTemplate(promptTemplate, {
      item: checklistItem,
      context,
      userHistory: await this.getUserHistory(context.userId)
    });
  }

  private async selectAppropriatePrompt(
    item: ChecklistItem,
    context: ChecklistContext
  ): Promise<string> {
    // Select prompt based on item importance, user experience, and context
    if (item.required && !context.completedItems.includes(item.id)) {
      return this.basePrompts.warning;
    }
    // ... additional prompt selection logic
  }
} 