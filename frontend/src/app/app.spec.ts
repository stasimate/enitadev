import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { App } from './app';
import { routes } from './app.routes';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });

  it('shows the split screen on the study route', async () => {
    const harness = await RouterTestingHarness.create('/');
    TestBed.inject(HttpTestingController).expectOne('/api/topics').flush([]);
    await new Promise((r) => setTimeout(r));
    harness.detectChanges();
    const el = harness.routeNativeElement as HTMLElement;
    expect(el.querySelector('#theory-title')).toBeTruthy();
    expect(el.querySelector('#practice-title')).toBeTruthy();
  });
});
