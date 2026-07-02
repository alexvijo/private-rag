import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ChatRequest, ChatResponse, HealthResponse, ModelsResponse } from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  // Al hacer unsubscribe() del Observable devuelto, Angular aborta la petición
  // HTTP subyacente (XHR/fetch), permitiendo cancelar una pregunta en curso.
  ask(request: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.baseUrl}/chat`, request);
  }

  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.baseUrl}/health`);
  }

  models(): Observable<ModelsResponse> {
    return this.http.get<ModelsResponse>(`${this.baseUrl}/chat/models`);
  }
}
