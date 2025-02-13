export enum QuestioningLevel {
  MINIMAL = 'minimal',    // Essential safety questions only
  MODERATE = 'moderate',  // Balance of guidance and efficiency
  DETAILED = 'detailed'   // Comprehensive guidance and explanations
}

export interface AIQuestioningStrategy {
  level: QuestioningLevel;
  adaptiveMode: boolean;  // Adjusts based on user expertise
  requireConfirmation: boolean;  // For critical items
  educationalPrompts: boolean;   // Include learning elements
}

export interface ContextualPrompt {
  type: 'safety' | 'educational' | 'confirmation' | 'dependency';
  priority: number;
  message: string;
  requiredResponse: boolean;
  dependencies?: string[];
} 