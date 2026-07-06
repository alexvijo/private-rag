import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { ChatService } from '../../core/services/chat.service';
import { SelectedDocumentsService } from '../../core/services/selected-documents.service';
import { ChatMessage } from '../../core/models/api.models';

type HealthState = 'checking' | 'ok' | 'degraded' | 'error';

@Component({
  selector: 'app-chat-window',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-window.component.html',
  styleUrl: './chat-window.component.css',
})
export class ChatWindowComponent implements OnInit, OnDestroy {
  private chatService = inject(ChatService);
  private selection = inject(SelectedDocumentsService);
  private healthPoll?: ReturnType<typeof setInterval>;
  private askSubscription?: Subscription;

  @ViewChild('scrollAnchor') private scrollAnchor?: ElementRef<HTMLDivElement>;

  messages = signal<ChatMessage[]>([]);
  currentQuestion = '';
  isThinking = signal(false);
  expandedSources = new Set<number>();

  llmProvider = signal<string>('...');
  llmModel = signal<string>('...');
  healthState = signal<HealthState>('checking');

  availableModels = signal<string[]>([]);
  selectedModel = signal<string>('');
  webSearchEnabled = signal<boolean>(false);

  ngOnInit(): void {
    this.refreshHealth();
    this.refreshModels();
    // Reconsulta la salud periódicamente para reflejar si Ollama/OpenAI dejan de responder.
    this.healthPoll = setInterval(() => this.refreshHealth(), 30000);
  }

  ngOnDestroy(): void {
    if (this.healthPoll) clearInterval(this.healthPoll);
    this.askSubscription?.unsubscribe();
  }

  refreshHealth(): void {
    this.chatService.health().subscribe({
      next: (res) => {
        this.llmProvider.set(res.llm_provider);
        this.llmModel.set(res.llm_model);
        this.healthState.set(res.llm_reachable ? 'ok' : 'degraded');
      },
      error: () => {
        this.llmProvider.set('desconocido');
        this.llmModel.set('desconocido');
        this.healthState.set('error');
      },
    });
  }

  refreshModels(): void {
    this.chatService.models().subscribe({
      next: (res) => {
        this.availableModels.set(res.available_models);
        this.selectedModel.set(res.current_model);
      },
      error: () => this.availableModels.set([]),
    });
  }

  sendQuestion(): void {
    const question = this.currentQuestion.trim();
    if (!question || this.isThinking()) return;

    this.messages.update((msgs) => [...msgs, { role: 'user', text: question, timestamp: new Date() }]);
    this.currentQuestion = '';
    this.isThinking.set(true);
    this.scrollToBottom();

    const model = this.selectedModel() || undefined;
    const webSearch = this.webSearchEnabled();
    const selectedDocIds = Array.from(this.selection.selectedDocIds());
    const docIds = selectedDocIds.length > 0 ? selectedDocIds : undefined;

    this.askSubscription = this.chatService
      .ask({ question, model, web_search: webSearch, doc_ids: docIds })
      .subscribe({
        next: (res) => {
          this.messages.update((msgs) => [
            ...msgs,
            {
              role: 'assistant',
              text: res.answer,
              sources: res.sources,
              webSources: res.web_sources,
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

  stopRequest(): void {
    // unsubscribe() aborta la petición HTTP en curso (XHR/fetch subyacente).
    // El backend puede seguir generando unos segundos más, pero se descarta la respuesta.
    this.askSubscription?.unsubscribe();
    this.isThinking.set(false);
    this.messages.update((msgs) => [
      ...msgs,
      {
        role: 'assistant',
        text: 'Solicitud interrumpida por el usuario.',
        hasSufficientContext: false,
        timestamp: new Date(),
      },
    ]);
    this.scrollToBottom();
  }

  toggleWebSearch(): void {
    this.webSearchEnabled.update((v) => !v);
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
