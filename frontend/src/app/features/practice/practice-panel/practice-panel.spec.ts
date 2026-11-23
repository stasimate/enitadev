import { TestBed } from '@angular/core/testing';
import { PracticePanel } from './practice-panel';

describe('PracticePanel', () => {
  it('shows the selected topic', async () => {
    const fixture = TestBed.createComponent(PracticePanel);
    fixture.componentRef.setInput('topicTitle', 'Past simple');
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Past simple');
  });
});
