import { Component } from '@angular/core';
import { DocumentsPanelComponent } from './features/documents/documents-panel.component';
import { ChatWindowComponent } from './features/chat/chat-window.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [DocumentsPanelComponent, ChatWindowComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {}
