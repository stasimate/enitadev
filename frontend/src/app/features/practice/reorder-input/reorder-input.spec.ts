import { TestBed } from '@angular/core/testing';
import { ReorderInput } from './reorder-input';

async function create(chunks: string[]) {
  const fixture = TestBed.createComponent(ReorderInput);
  fixture.componentRef.setInput('chunks', chunks);
  const answers: string[] = [];
  fixture.componentInstance.answered.subscribe((a) => answers.push(a));
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  const buttons = () => Array.from(el.querySelectorAll('button'));
  const named = (label: string) => buttons().find((b) => b.textContent!.includes(label))!;
  const click = async (b: HTMLButtonElement) => {
    b.click();
    await fixture.whenStable();
  };
  return { fixture, answers, buttons, named, click };
}

describe('ReorderInput', () => {
  it('builds the answer in click order and handles duplicate chunks', async () => {
    const { buttons, named, click, answers } = await create(['the', 'cat', 'the', 'dog']);
    expect(named('Verifica').disabled).toBe(true);
    // Click order: the(2), dog, the(0), cat
    for (const i of [2, 3, 0, 1]) await click(buttons()[i]);
    expect(named('Verifica').disabled).toBe(false);
    await click(named('Verifica'));
    expect(answers).toEqual(['the dog the cat']);
  });

  it('uses each chunk once', async () => {
    const { buttons, click, named } = await create(['a', 'b']);
    await click(buttons()[0]);
    expect(buttons()[0].disabled).toBe(true);
    buttons()[0].click();
    await click(buttons()[1]);
    expect(named('Verifica').disabled).toBe(false);
  });

  it('removes the last chunk and resets', async () => {
    const { buttons, named, click, answers } = await create(['a', 'b', 'c']);
    await click(buttons()[1]);
    await click(buttons()[0]);
    await click(named('Annulla'));
    expect(buttons()[0].disabled).toBe(false);
    expect(buttons()[1].disabled).toBe(true);
    await click(named('Ricomincia'));
    expect(buttons()[1].disabled).toBe(false);
    expect(answers).toEqual([]);
  });

  it('emits nothing when the sentence is not complete', async () => {
    const { buttons, click, answers, fixture } = await create(['a', 'b']);
    await click(buttons()[0]);
    (fixture.componentInstance as unknown as { submit(): void }).submit();
    expect(answers).toEqual([]);
  });
});
