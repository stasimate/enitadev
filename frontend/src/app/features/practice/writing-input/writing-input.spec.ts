import { TestBed } from '@angular/core/testing';
import { WritingInput } from './writing-input';

async function create(disabled = false) {
  const fixture = TestBed.createComponent(WritingInput);
  fixture.componentRef.setInput('disabled', disabled);
  const answers: string[] = [];
  fixture.componentInstance.answered.subscribe((a) => answers.push(a));
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  const area = el.querySelector('textarea') as HTMLTextAreaElement;
  const type = async (value: string) => {
    area.value = value;
    area.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  };
  return { el, area, answers, type };
}

describe('WritingInput', () => {
  it('limits the text to 600 characters and counts them', async () => {
    const { el, area, type } = await create();
    expect(area.getAttribute('maxlength')).toBe('600');
    await type('Hello');
    expect(el.textContent).toContain('5/600');
  });

  it('sends the trimmed text with Ctrl+Enter or Cmd+Enter', async () => {
    const { area, answers, type } = await create();
    await type('  I went home.\nIt was late. ');
    area.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(answers).toEqual([]);
    area.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }));
    area.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', metaKey: true }));
    expect(answers).toEqual(['I went home.\nIt was late.', 'I went home.\nIt was late.']);
  });

  it('does not send an empty text or when disabled', async () => {
    const empty = await create();
    await empty.type('   ');
    empty.area.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }));
    expect(empty.answers).toEqual([]);

    const off = await create(true);
    await off.type('Hi');
    off.area.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }));
    expect(off.answers).toEqual([]);
  });
});
