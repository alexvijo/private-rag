import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DocumentListResponse, ReindexResponse, UploadResponse } from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class DocumentService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/documents`;

  upload(files: File[]): Observable<UploadResponse> {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file, file.name);
    }
    return this.http.post<UploadResponse>(`${this.baseUrl}/upload`, formData);
  }

  list(): Observable<DocumentListResponse> {
    return this.http.get<DocumentListResponse>(this.baseUrl);
  }

  delete(docId: string): Observable<{ deleted: boolean; doc_id: string }> {
    return this.http.delete<{ deleted: boolean; doc_id: string }>(`${this.baseUrl}/${docId}`);
  }

  reindexAll(): Observable<ReindexResponse> {
    return this.http.post<ReindexResponse>(`${this.baseUrl}/reindex`, {});
  }

  clearAll(): Observable<{ cleared: boolean }> {
    return this.http.delete<{ cleared: boolean }>(this.baseUrl);
  }
}
