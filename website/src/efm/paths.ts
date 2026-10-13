/** Hide .kiro / KIROCREW_HOME in user-visible strings. Does not move files. */
export function hideKiroPath(value: string | undefined | null): string {
  if (!value) return ''
  return value
    .replace(/\$KIROCREW_HOME/g, 'namų aplankas')
    .replace(/KIROCREW_HOME/g, 'namų aplankas')
    .replace(/~\/\.kiro[^\s`]*/g, 'duomenų aplankas')
    .replace(/[A-Za-z]:\\[^\s`]*\\.kiro[^\s`]*/gi, 'duomenų aplankas')
    .replace(/\/(?:home|Users)\/[^\s`]*\/\.kiro[^\s`]*/g, 'duomenų aplankas')
    .replace(/\.kiro\/crew[^\s`]*/g, 'duomenų aplankas')
}
