/** Keep source text unchanged; only web URLs without embedded credentials become links. */
export function sourceUrl(value: string | null | undefined): string | undefined {
  if(!value)return undefined
  try {const url=new URL(value);return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password?url.href:undefined} catch {return undefined}
}
