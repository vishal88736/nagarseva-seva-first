import assert from 'node:assert/strict'
import { test } from 'node:test'
import { messages } from '../src/i18n/catalog.ts'
import { errorText, formatDate, formatDecimal, formatMoney, formatNumber, getLanguage, setLanguage, statusText, storedLanguage, translate, validLanguage } from '../src/i18n/locale.ts'

test('Every catalogue message has Hindi and Marathi text with matching parameters', () => {
  const params = value => [...new Set(value.match(/\{\w+\}/g))].sort()
  for (const [key,values] of Object.entries(messages)) for (const lang of ['hi','mr']) {
    assert.equal(typeof values[lang],'string', key); assert.ok(values[lang].trim(),key); assert.deepEqual(params(values[lang]),params(key),key)
  }
})
test('Direct, interpolated and already-formatted errors translate without changing unknown source text', () => {
  assert.equal(translate('hi','Settlement map'),'बस्ती का नक्शा')
  assert.equal(translate('mr','Reference boundary request failed ({status}).',{status:404}),'संदर्भ सीमा विनंती अयशस्वी (404).')
  assert.equal(translate('hi','Reference boundary request failed (404).'),'संदर्भ सीमा अनुरोध विफल (404)।')
  assert.equal(translate('mr','Custom imported name'),'Custom imported name')
  setLanguage('mr'); assert.equal(errorText('Officer access key required'),'अधिकारी प्रवेश कळ आवश्यक आहे')
  assert.match(errorText('Unexpected token in JSON'),/JSON/)
  assert.equal(errorText('Unrecognized provider traceback'),translate('mr','The request could not be completed. Check the supplied values and retry.'))
  setLanguage('en')
})
test('Locale-aware numbers, money, dates and statuses retain machine data semantics', () => {
  setLanguage('en'); assert.equal(formatDecimal(51),'51.0'); assert.equal(formatMoney(1199),'₹1,199'); assert.equal(formatNumber(null),'Unavailable')
  setLanguage('hi'); assert.equal(statusText('reported_complete'),translate('hi','Reported complete')); assert.match(formatDate('2015-12-31'),/2015/)
  setLanguage('mr'); assert.equal(formatDecimal(51),'५१.०'); assert.equal(formatDate('2015'),'२०१५'); assert.equal(getLanguage(),'mr')
  assert.equal(validLanguage('xx'),false); assert.equal(validLanguage('hi'),true); assert.equal(storedLanguage(),'en')
  setLanguage('en')
})
