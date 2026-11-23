import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { TheoryStore } from '../theory/theory-store';
import { ExplainStore } from './explain-store';

async function settle(): Promise<void> {
  await new Promise((r) => setTimeout(r));
  TestBed.tick();
}

describe('ExplainStore', () => {
  let store: ExplainStore;
  let theory: TheoryStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    theory = TestBed.inject(TheoryStore);
    store = TestBed.inject(ExplainStore);
    theory.selectedId.set('past-simple');
    TestBed.tick();
  });

  it('posts to the explain endpoint and keeps the explanation and the sources', () => {
    store.explain();
    expect(store.status()).toBe('loading');
    const req = http.expectOne('/api/topics/past-simple/explain');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({
      explanation: 'Ciao **mondo**',
      sources: [{ rule_ref: 'past-simple#regola', title: 'Past simple · Regola' }],
    });
    expect(store.status()).toBe('ready');
    expect(store.explanation()).toBe('Ciao **mondo**');
    expect(store.sources()[0].rule_ref).toBe('past-simple#regola');
  });

  it('maps 504 to a retryable error and 503 to the backend detail', () => {
    store.explain();
    http
      .expectOne('/api/topics/past-simple/explain')
      .flush({}, { status: 504, statusText: 'Gateway Timeout' });
    expect(store.status()).toBe('error');
    expect(store.retryable()).toBe(true);

    store.explain();
    http
      .expectOne('/api/topics/past-simple/explain')
      .flush({ detail: 'Servizio non disponibile' }, { status: 503, statusText: 'Unavailable' });
    expect(store.error()).toBe('Servizio non disponibile');
    expect(store.retryable()).toBe(false);
  });

  it('resets when the topic changes', async () => {
    store.explain();
    http.expectOne('/api/topics/past-simple/explain').flush({ explanation: 'x', sources: [] });
    theory.select('other');
    await settle();
    expect(store.status()).toBe('idle');
    expect(store.explanation()).toBeNull();
  });
});
