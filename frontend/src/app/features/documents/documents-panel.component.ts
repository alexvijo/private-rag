import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { DocumentService } from '../../core/services/document.service';
import { DocumentInfo } from '../../core/models/api.models';

@Component({
  selector: 'app-documents-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './documents-panel.component.html',
  styleUrl: './documents-panel.component.css',
})
export class DocumentsPanelComponent implements OnInit {
  private documentService = inject(DocumentService);

  documents = signal<DocumentInfo[]>([]);
  isUploading = signal(false);
  isDragging = signal(false);
  errorMessages = signal<string[]>([]);
  statusMessage = signal<string | null>(null);

  readonly acceptedFormats = '.pdf,.docx,.xlsx,.xls,.txt,.csv,.epub';

  ngOnInit(): void {
    this.refreshDocuments();
  }

  refreshDocuments(): void {
    this.documentService.list().subscribe({
      next: (res) => this.documents.set(res.documents),
      error: () => this.errorMessages.set(['No se pudo conectar con el backend. ¿Está en ejecución?']),
    });
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.uploadFiles(Array.from(files));
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFiles(Array.from(input.files));
      input.value = '';
    }
  }

  uploadFiles(files: File[]): void {
    this.isUploading.set(true);
    this.errorMessages.set([]);
    this.statusMessage.set(null);

    this.documentService.upload(files).subscribe({
      next: (res) => {
        this.isUploading.set(false);
        if (res.indexed.length > 0) {
          this.statusMessage.set(`${res.indexed.length} documento(s) indexado(s) correctamente.`);
        }
        if (res.errors.length > 0) {
          this.errorMessages.set(res.errors);
        }
        this.refreshDocuments();
      },
      error: (err) => {
        this.isUploading.set(false);
        this.errorMessages.set([err?.error?.detail ?? 'Error al subir los documentos.']);
      },
    });
  }

  deleteDocument(docId: string): void {
    this.documentService.delete(docId).subscribe({
      next: () => this.refreshDocuments(),
      error: (err) => this.errorMessages.set([err?.error?.detail ?? 'Error al borrar el documento.']),
    });
  }

  reindexAll(): void {
    this.statusMessage.set('Reindexando todos los documentos...');
    this.documentService.reindexAll().subscribe({
      next: (res) => {
        this.statusMessage.set(
          `Reindexado completo: ${res.reindexed_documents} documentos, ${res.total_chunks} chunks.`
        );
        this.refreshDocuments();
      },
      error: (err) => this.errorMessages.set([err?.error?.detail ?? 'Error al reindexar.']),
    });
  }

  clearAll(): void {
    if (!confirm('¿Seguro que quieres borrar TODOS los documentos e índices? Esta acción no se puede deshacer.')) {
      return;
    }
    this.documentService.clearAll().subscribe({
      next: () => {
        this.statusMessage.set('Índice borrado completamente.');
        this.refreshDocuments();
      },
      error: (err) => this.errorMessages.set([err?.error?.detail ?? 'Error al borrar el índice.']),
    });
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
