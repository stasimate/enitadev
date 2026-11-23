import { TestBed } from '@angular/core/testing';
import { TopicCard } from '../../../core/models';
import { TheoryCard } from './theory-card';

const CARD: TopicCard = {
  id: 'demo',
  title: 'Demo',
  level: 'A1',
  tags: [],
  sections: [
    { slug: 'regola', title: 'Regola', markdown: 'Rule **text**' },
    { slug: 'esempi', title: 'Esempi', markdown: 'Example' },
  ],
};

describe('TheoryCard', () => {
  it('renders all sections and highlights one', async () => {
    const fixture = TestBed.createComponent(TheoryCard);
    fixture.componentRef.setInput('card', CARD);
    fixture.componentRef.setInput('highlighted', 'esempi');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;

    expect(el.querySelectorAll('section').length).toBe(2);
    expect(el.querySelector('#sec-regola strong')?.textContent).toBe('text');
    expect(el.querySelector('#sec-esempi')?.getAttribute('aria-current')).toBe('true');
    expect(el.querySelector('#sec-regola')?.getAttribute('aria-current')).toBeNull();
  });
});
