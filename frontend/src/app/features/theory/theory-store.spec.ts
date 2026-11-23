import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { TheoryStore } from './theory-store';

/** Lets the resource process the flushed response. */
async function settle(): Promise<void> {
  await new Promise((r) => setTimeout(r));
  TestBed.tick();
}

describe('TheoryStore', () => {
  let store: TheoryStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    store = TestBed.inject(TheoryStore);
    http = TestBed.inject(HttpTestingController);
  });

  it('loads topics, selects the first one and loads its card', async () => {
    TestBed.tick();
    http.expectOne('/api/topics').flush([
      { id: 'b', title: 'B', level: 'A2', tags: [] },
      { id: 'a', title: 'A', level: 'A1', tags: [] },
    ]);
    await settle();

    expect(store.groups().map((g) => g.level)).toEqual(['A1', 'A2']);
    expect(store.selectedId()).toBe('b');

    TestBed.tick();
    http
      .expectOne('/api/topics/b')
      .flush({ id: 'b', title: 'B', level: 'A2', tags: [], sections: [] });
    await settle();
    expect(store.card.value()?.title).toBe('B');
  });

  it('clears the highlight when the topic changes', () => {
    store.highlighted.set('regola');
    store.select('x');
    expect(store.selectedId()).toBe('x');
    expect(store.highlighted()).toBeNull();
  });
});
