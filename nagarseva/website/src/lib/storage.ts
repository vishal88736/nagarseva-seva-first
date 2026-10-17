const temporary = new Map<string, string>()
export let browserStorageAvailable = true

function unavailable() {
  browserStorageAvailable = false
  window.dispatchEvent(new Event('nagarseva-storage-limited'))
}

function storage(kind: 'localStorage' | 'sessionStorage') {
  return {
    getItem(key: string): string | null {
      const memoryKey = `${kind}:${key}`
      if (temporary.has(memoryKey)) return temporary.get(memoryKey) ?? null
      try { return window[kind].getItem(key) } catch { unavailable(); return null }
    },
    setItem(key: string, value: string) {
      const memoryKey = `${kind}:${key}`
      try { window[kind].setItem(key, value); temporary.delete(memoryKey) }
      catch { temporary.set(memoryKey, value); unavailable() }
    },
    removeItem(key: string) {
      temporary.delete(`${kind}:${key}`)
      try { window[kind].removeItem(key) } catch { unavailable() }
    },
  }
}

export const localStore = storage('localStorage')
export const sessionStore = storage('sessionStorage')
