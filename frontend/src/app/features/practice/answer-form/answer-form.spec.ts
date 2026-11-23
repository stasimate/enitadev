import { TestBed } from '@angular/core/testing';
import { Exercise } from '../../../core/models';
import { AnswerForm } from './answer-form';

const BASE: Exercise = {
  id: 'e',
  topic_id: 't',
  type: 'fill_blank',
  instruction: 'i',
  prompt: 'I ___ home.',
  options: [],
};

async function create(exercise: Exercise, disabled = false) {
  const fixture = TestBed.createComponent(AnswerForm);
  fixture.componentRef.setInput('exercise', exercise);
  fixture.componentRef.setInput('disabled', disabled);
  const answers: string[] = [];
  fixture.componentInstance.answered.subscribe((a) => answers.push(a));
  await fixture.whenStable();
  return { fixture, el: fixture.nativeElement as HTMLElement, answers };
}

describe('AnswerForm', () => {
  it('emits the typed text for fill_blank', async () => {
    const { fixture, el, answers } = await create(BASE);
    const input = el.querySelector('input') as HTMLInputElement;
    expect(input.maxLength).toBe(300);
    expect(el.querySelector('label')).toBeTruthy();
    input.value = ' went ';
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    expect(answers).toEqual(['went']);
  });

  it('does not emit an empty answer', async () => {
    const { el, answers } = await create(BASE);
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    expect(answers).toEqual([]);
  });

  it('emits the option text for multiple_choice', async () => {
    const { el, answers } = await create({
      ...BASE,
      type: 'multiple_choice',
      options: ['go', 'went', 'gone'],
    });
    const buttons = el.querySelectorAll('button');
    expect(buttons.length).toBe(3);
    buttons[1].click();
    expect(answers).toEqual(['went']);
  });

  it('disables the controls while checking', async () => {
    const { el } = await create(BASE, true);
    expect((el.querySelector('input') as HTMLInputElement).disabled).toBe(true);
    expect((el.querySelector('button') as HTMLButtonElement).disabled).toBe(true);
  });
});
