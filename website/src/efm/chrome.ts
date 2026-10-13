/**
 * EFM Go chrome — product name + Lithuanian labels.
 * Call setEfmProductName() from extensions.ts BEFORE initI18n().
 * Call applyEfmChromeLabels() from main.tsx AFTER initI18n().
 * Does not touch chat transport / OpenZiti.
 */
import { setProductName } from '../i18n'
import { i18next } from '../i18n/lazy'

export const EFM_PRODUCT_NAME = 'EFM Go'

export function setEfmProductName(): void {
  setProductName(EFM_PRODUCT_NAME)
}

/** Flat i18n keys → Lithuanian chrome. Internal IDs unchanged. */
export const EFM_CHROME_LABELS: Record<string, string> = {
  'nav.sessions': 'Pokalbiai',
  'nav.schedule': 'Tvarkaraštis',
  'nav.artifacts': 'Failai',
  'nav.discover': 'Priedai',
  'nav.library': 'Įdiegta',
  'nav.task_runner': 'Užduotys',
  'nav.settings': 'Nustatymai',
  'nav.agent_capabilities': 'Derinimas',
  'nav.crew_members': 'Komanda',
  'nav.notifications': 'Pranešimai',
  'nav.apps': 'Programos',
  'nav.webhooks': 'Webhookai',

  'components.chatInput.message_placeholder': 'Rašyk EFM Go…',
  'app.notifications': 'Pranešimai',
  'app.notifications_failed_to_load': 'Pranešimų nepavyko įkelti',
  'app.open_inbox': 'Dėžutė',
  'app.open_the_full_inbox': 'Visa dėžutė',
  'app.notifications_ask_agent_help': 'Atidaro pokalbį su šios klaidos ataskaita, paruošta siųsti.',
  'components.askAgent.ask_the_agent': 'Klausti',
  'app.request_a_feature_2': 'Prašyti funkcijos',
  'app.report_issue': 'Pranešti',
  'pages.settingsPage.kirocrew_v': '{{productName}} v',
  'pages.settingsPage.settings': 'Nustatymai',

  'pages.capabilitiesPage.crews_label': 'Komanda',
  'pages.capabilitiesPage.skills_label': 'Įgūdžiai',
  'pages.capabilitiesPage.connections_label': 'Jungtys',
  'pages.capabilitiesPage.knowledge_label': 'Žinios',
  'pages.capabilitiesPage.prompts_label': 'Promptai',
  'pages.capabilitiesPage.steering_label': 'Nurodymai',
  'pages.capabilitiesPage.hooks_label': 'Kabliukai',
  'pages.capabilitiesPage.workflows_label': 'Eigos',

  'settings.tabs.overview.label': 'Apžvalga',
  'settings.tabs.imports.label': 'Atsarginė kopija',
  'settings.tabs.agent.label': 'Pokalbio variklis',
  'settings.tabs.chat.label': 'Pokalbis',
  'settings.tabs.display.label': 'Išvaizda',
  'settings.tabs.voice.label': 'Balsas',
  'settings.tabs.notifications.label': 'Pranešimai',
  'settings.tabs.shortcuts.label': 'Klavišai',
  'settings.tabs.skills.label': 'Įgūdžiai',
  'settings.tabs.channels.label': 'Kanalai',
  'settings.tabs.browser.label': 'Naršyklė',
  'settings.tabs.computerUse.label': 'Kompiuterio valdymas',
  'settings.tabs.webhooks.label': 'Webhookai',
  'settings.tabs.instances.label': 'Nuotolis',
  'settings.tabs.security.label': 'Sauga',
  'settings.tabs.connections.label': 'Jungtys',
  'settings.tabs.secrets.label': 'Paslaptys',
  'settings.tabs.developer.label': 'Kūrėjams',
  'settings.tabs.releases.label': 'Versijos',
  'settings.tabs.about.label': 'Apie',

  'app.resource_posture_tooltip_critical':
    'Kompiuteriui trūksta atminties ({{gb}} GB laisva). Venk sunkių darbų.',
  'app.resource_posture_tooltip_tight':
    'Atmintis ankšta ({{gb}} GB laisva). Sunkūs darbai gali lėtėti.',

  'pages.settings.slackPanel.kirocrew': 'efm',
  'pages.settings.slackPanel.slash_command': 'Slash komanda',

  'components.reportProblemModal.open_github_issue': 'Siųsti EFM',
  'components.shortcutsModal.show_or_focus_the_kiro_crew_window': 'Rodyti EFM Go langą',
  'components.mobileConnectModal.title': 'Naudok EFM Go telefone',
  'components.mobileConnectModal.use_kiro_crew_on_your_phone': 'Naudok EFM Go telefone',
  'pages.overview.use_this_on_your_phone': 'Naudok EFM Go telefone',
  'pages.settings.voicePanel.openai_tts': 'OpenAI (tts-1, ash / moteris)',
  'components.mobileConnect.use_kiro_crew_on_your_phone': 'Naudok EFM Go telefone',
  'components.mobileConnect.checking_remote_access': 'Tikrinamas OpenZiti ryšys…',
  'components.mobileConnect.could_not_check_remote_access': 'Nepavyko patikrinti OpenZiti ryšio.',
  'components.mobileConnect.scan_with_your_phone_camera_to_continue_with_the_s': 'Nuskenuok. Kelias: OpenZiti → Contabo. Ne Kiro, ne Tailscale, ne SSH.',
}

export function applyEfmChromeLabels(): void {
  const langs = new Set<string>(['en', i18next.language || 'en'])
  for (const lng of langs) {
    for (const [key, value] of Object.entries(EFM_CHROME_LABELS)) {
      i18next.addResource(lng, 'translation', key, value)
    }
  }
}
