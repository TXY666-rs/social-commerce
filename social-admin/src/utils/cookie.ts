/**
 * Cookie 操作工具 — 与 social-frontend 统一
 * 
 * 安全策略：
 * - SameSite=Strict：防止 CSRF 攻击中携带 cookie
 * - Path=/：限定 cookie 作用域
 */

interface CookieOptions {
  days?: number
  path?: string
  sameSite?: 'Strict' | 'Lax' | 'None'
  secure?: boolean
}

const DEFAULTS: CookieOptions = {
  days: 7,
  path: '/',
  sameSite: 'Strict',
  secure: location.protocol === 'https:',
}

export function setCookie(name: string, value: string, options: CookieOptions = {}): void {
  const opts = { ...DEFAULTS, ...options }
  const expires = new Date()
  expires.setTime(expires.getTime() + opts.days! * 24 * 60 * 60 * 1000)

  let cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`
  cookie += `; expires=${expires.toUTCString()}`
  cookie += `; path=${opts.path}`
  cookie += `; SameSite=${opts.sameSite}`
  if (opts.secure) {
    cookie += '; Secure'
  }

  document.cookie = cookie
}

export function getCookie(name: string): string | null {
  const encodedName = encodeURIComponent(name) + '='
  const cookies = document.cookie.split(';')
  for (let i = 0; i < cookies.length; i++) {
    const c = cookies[i].trim()
    if (c.startsWith(encodedName)) {
      return decodeURIComponent(c.substring(encodedName.length))
    }
  }
  return null
}

export function removeCookie(name: string, path: string = '/'): void {
  document.cookie = `${encodeURIComponent(name)}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=${path}`
}
