import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../core/services/chat.service';
import { ChatMessage } from '../../core/models/api.models';

@Component({
  selector: 'app-chat-window',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-window.component.html',
  styleUrl: './chat-window.component.css',
})
export class ChatWindowComponent implements OnInit {
  private chatService = inject(ChatService);

  @ViewChild('scrollAnchor') private scrollAnchor?: ElementRef<HTMLDivElement>;

  messages = signal<ChatMessage[]>([]);
  currentQuestion = '';
  isThinking = signal(false);
  llmProvider = signal<string>('...');
  expandedSources = new Set<number>();

  ngOnInit(): void {
    this.chatService.health().subscribe({
      next: (res) => this.llmProvider.set(res.llm_provider),
      error: () => this.llmProvider.set('desconocido'),
    });
  }

  sendQuestion(): void {
    const question = this.currentQuestion.trim();
    if (!question || this.isThinking()) return;

    this.messages.update((msgs) => [...msgs, { role: 'user', text: question, timestamp: new Date() }]);
    this.currentQuestion = '';
    this.isThinking.set(true);
    this.scrollToBottom();

    this.chatService.ask({ question }).subscribe({
      next: (res) => {
        this.messages.update((msgs) => [
          ...msgs,
          {
            role: 'assistant',
            text: res.answer,
            sources: res.sources,
            hasSufficientContext: res.has_sufficient_context,
            timestamp: new Date(),
          },
        ]);
        this.isThinking.set(false);
        this.scrollToBottom();
      },
      error: (err) => {
        this.messages.update((msgs) => [
          ...msgs,
          {
            role: 'assistant',
            text: `Error: ${err?.error?.detail ?? 'No se pudo obtener respuesta del servidor.'}`,
            hasSufficientContext: false,
            timestamp: new Date(),
          },
        ]);
        this.isThinking.set(false);
        this.scrollToBottom();
      },
    });
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendQuestion();
    }
  }

  toggleSources(index: number): void {
    if (this.expandedSources.has(index)) {
      this.expandedSources.delete(index);
    } else {
      this.expandedSources.add(index);
    }
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      this.scrollAnchor?.nativeElement.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  }
}
