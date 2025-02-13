interface ChecklistItem {
  id: string;
  category: string;
  description: string;
  required: boolean;
  aiPrompts: string[];
  verificationMethod: 'manual' | 'photo' | 'both';
  dependencies?: string[];  // IDs of items that must be completed first
}

interface ChecklistCategory {
  id: string;
  name: string;
  items: ChecklistItem[];
  completionRules: CompletionRule[];
}

interface Checklist {
  id: string;
  name: string;
  categories: ChecklistCategory[];
  metadata: {
    vesselType: string;
    requiredCrew: number;
    weatherDependent: boolean;
  };
} 