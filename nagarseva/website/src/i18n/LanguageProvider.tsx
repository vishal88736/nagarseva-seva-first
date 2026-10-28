import { createContext, useContext, useEffect, useState } from 'react'
import type { InputHTMLAttributes, ReactNode } from 'react'
import { useRef } from 'react'
import { getLanguage, LANGUAGE_LABELS, LANGUAGES, setLanguage as saveLanguage, storedLanguage, t, validLanguage } from './locale'
import type { Language } from './locale'

const LanguageContext = createContext({ language: 'en' as Language, changeLanguage: (_language: Language) => {} })
export const useLanguage = () => useContext(LanguageContext)
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, update] = useState<Language>(() => { const initial = storedLanguage(); saveLanguage(initial); return initial })
  function changeLanguage(next: Language) { if (validLanguage(next)) { saveLanguage(next); update(next) } }
  useEffect(() => { document.documentElement.lang = language }, [language])
  useEffect(() => {
    function clear(event: Event) { const field = event.target; if (field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement) field.setCustomValidity('') }
    function invalid(event: Event) {
      const field = event.target
      if (!(field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement)) return
      const validity = field.validity
      field.setCustomValidity(validity.valueMissing ? t('This field is required.') : validity.rangeOverflow || validity.rangeUnderflow ? t('Enter a value within the allowed range.') : validity.tooShort ? t('Please enter a longer value.') : t('Use the requested format.'))
    }
    document.addEventListener('invalid', invalid, true); document.addEventListener('input', clear, true); document.addEventListener('change', clear, true)
    return () => { document.removeEventListener('invalid', invalid, true); document.removeEventListener('input', clear, true); document.removeEventListener('change', clear, true) }
  }, [])
  return <LanguageContext.Provider value={{ language, changeLanguage }}>{children}</LanguageContext.Provider>
}
export function LanguageSwitcher() {
  const { language, changeLanguage } = useLanguage()
  return <label className="us-language"><span>{language === 'en' ? 'Language' : 'भाषा'}</span><select aria-label="Language / भाषा" value={language} onChange={event => changeLanguage(event.target.value as Language)}>{LANGUAGES.map(code => <option key={code} value={code} lang={code}>{LANGUAGE_LABELS[code]}</option>)}</select></label>
}
export function FileInput({ fileName, onChange, ...props }: InputHTMLAttributes<HTMLInputElement> & { fileName?: string }) {
  const [selected, setSelected] = useState(''), input = useRef<HTMLInputElement>(null)
  const { language } = useLanguage()
  const name = fileName === undefined ? selected : fileName
  useEffect(() => { if (fileName === '' && input.current) input.current.value = '' }, [fileName])
  return <span className="us-file-input" lang={language}><input {...props} ref={input} type="file" className="us-file-native" onChange={event => { setSelected(event.target.files?.[0]?.name || ''); onChange?.(event) }} /><button type="button" className="us-button" disabled={props.disabled} onClick={event => { event.preventDefault(); input.current?.click() }}>{t('Choose file')}</button><span>{name || t('No file selected')}</span></span>
}
export function localizedPageTitle(page: string) { return `${t('UrbanSaarthi')} · ${t(page)}` }
export { getLanguage }
