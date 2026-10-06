const UNAUTHORIZED_STATUS = 401
export const UNAUTHORIZED_EVENT = 'api:unauthorized'

export async function apiFetch(url, options) {
  const res = await fetch(url, options)
  if (res.status === UNAUTHORIZED_STATUS) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
  return res
}
