export enum InteractionMode {
  MANUAL = 'manual',
  CONVERSATIONAL_TEXT = 'conversational_text',
  CONVERSATIONAL_VOICE = 'conversational_voice'
}

export interface InteractionState {
  mode: InteractionMode;
  aiAssistEnabled: boolean;
  lastInteraction: Date;
  currentChecklistItem?: string;
} 