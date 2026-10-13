/**
 * EFM Go surface flags. HIDE/REMOVE of Kiro leftover chrome.
 * Internal IDs, API routes, and SKILL.md are not renamed here.
 */

/** Built-in Discover apps to hide (Kiro shelf). Keep command-bar, task-runner, files, notes. */
export const EFM_HIDDEN_BUILTIN_APPS = new Set([
  'issue-radar',
  'crew-companion',
  'crew-manager',
  'crew-companion-manager',
  'agent-world',
  'dev-fleet',
  'devfleet',
  'mochi',
  'meetings',
  'auto-research',
])

export const EFM_HIDDEN_SETTINGS_TABS = new Set([
  'instances', // SSH Remote Crew
])

export const EFM_HIDDEN_HARNESS_IDS = new Set([
  'kiro',
  'kiro-cli',
  'kiro_cli',
  'kas',
  'kiro-agent',
  'kiro_agent',
])

export function isHiddenBuiltinApp(name: string | undefined | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  if (EFM_HIDDEN_BUILTIN_APPS.has(n)) return true
  if (n.includes('issue-radar') || n.includes('dev-fleet') || n.includes('devfleet')) return true
  if (n.includes('crew-companion') || n.includes('crew-manager')) return true
  if (n.includes('agent-world') || n.includes('mochi')) return true
  return false
}
