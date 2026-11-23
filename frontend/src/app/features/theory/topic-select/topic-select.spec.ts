import { TestBed } from '@angular/core/testing';
import { TopicSelect } from './topic-select';

describe('TopicSelect', () => {
  it('groups topics by level and updates the selection', async () => {
    const fixture = TestBed.createComponent(TopicSelect);
    fixture.componentRef.setInput('groups', [
      { level: 'A1', topics: [{ id: 'a', title: 'A', level: 'A1', tags: [] }] },
      { level: 'A2', topics: [{ id: 'b', title: 'B', level: 'A2', tags: [] }] },
    ]);
    fixture.componentRef.setInput('selected', 'a');
    await fixture.whenStable();
    const select = (fixture.nativeElement as HTMLElement).querySelector('select')!;

    expect(select.querySelectorAll('optgroup').length).toBe(2);
    select.value = 'b';
    select.dispatchEvent(new Event('change'));
    expect(fixture.componentInstance.selected()).toBe('b');
  });
});
