class VoiceService {
  async startVoiceInteraction(checklistId: string): Promise<VoiceSession> {
    const session = await this.initializeVoiceSession();
    
    return {
      listen: async () => {
        const audioInput = await this.audioCapture.start();
        const transcription = await this.speechToText.convert(audioInput);
        return this.aiConversation.handleUserInput(transcription, {
          checklistId,
          mode: InteractionMode.CONVERSATIONAL_VOICE
        });
      },
      
      speak: async (response: AIResponse) => {
        const audio = await this.textToSpeech.convert(response.text);
        await this.audioOutput.play(audio);
      }
    };
  }
} 