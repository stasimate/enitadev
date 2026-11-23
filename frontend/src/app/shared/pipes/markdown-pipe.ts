import { Pipe, PipeTransform } from '@angular/core';
import { marked } from 'marked';

/**
 * Converts markdown to HTML. Use the output only with `[innerHTML]`:
 * Angular sanitizes it there.
 */
@Pipe({
  name: 'markdown',
})
export class MarkdownPipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    return value ? (marked.parse(value, { async: false, gfm: true }) as string) : '';
  }
}
