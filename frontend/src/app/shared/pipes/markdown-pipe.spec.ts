import { MarkdownPipe } from './markdown-pipe';

describe('MarkdownPipe', () => {
  const pipe = new MarkdownPipe();

  it('converts markdown to HTML', () => {
    const html = pipe.transform('- ~~he work~~ → `he works`');
    expect(html).toContain('<li>');
    expect(html).toContain('<del>he work</del>');
    expect(html).toContain('<code>he works</code>');
  });

  it('returns an empty string for no value', () => {
    expect(pipe.transform(null)).toBe('');
  });
});
