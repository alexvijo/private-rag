import { Injectable, signal } from '@angular/core';

/** Estado compartido entre el panel de documentos (que marca los checkbox) y
 * el chat (que restringe la pregunta a los documentos seleccionados). */
@Injectable({ providedIn: 'root' })
export class SelectedDocumentsService {
  selectedDocIds = signal<Set<string>>(new Set());

  isSelected(docId: string): boolean {
    return this.selectedDocIds().has(docId);
  }

  toggle(docId: string): void {
    this.selectedDocIds.update((current) => {
      const next = new Set(current);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  }

  /** Quita del set cualquier doc_id que ya no exista (tras borrar/reindexar). */
  pruneToExisting(existingDocIds: string[]): void {
    const existing = new Set(existingDocIds);
    this.selectedDocIds.update((current) => {
      const next = new Set([...current].filter((id) => existing.has(id)));
      return next.size === current.size ? current : next;
    });
  }
}
