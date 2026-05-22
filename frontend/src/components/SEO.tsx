import { useEffect } from 'react'

interface SEOProps {
  title: string
  description: string
  path?: string
  image?: string
  type?: 'website' | 'article'
  jsonLd?: Record<string, any> | Record<string, any>[]
}

const BASE_URL = 'https://meridian.tips'
const DEFAULT_IMAGE = `${BASE_URL}/og-image.png`

function setMeta(name: string, content: string) {
  let el = document.querySelector(`meta[property="${name}"], meta[name="${name}"]`) as HTMLMetaElement | null
  if (!el) {
    el = document.createElement('meta')
    if (name.startsWith('og:') || name.startsWith('twitter:')) {
      el.setAttribute('property', name)
    } else {
      el.setAttribute('name', name)
    }
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

function setCanonical(url: string) {
  let el = document.querySelector('link[rel="canonical"]') as HTMLLinkElement | null
  if (!el) {
    el = document.createElement('link')
    el.setAttribute('rel', 'canonical')
    document.head.appendChild(el)
  }
  el.setAttribute('href', url)
}

const JSONLD_ID = 'seo-jsonld'

export default function SEO({ title, description, path = '/', image, type = 'website', jsonLd }: SEOProps) {
  useEffect(() => {
    document.title = title

    setMeta('description', description)
    setMeta('og:title', title)
    setMeta('og:description', description)
    setMeta('og:url', `${BASE_URL}${path}`)
    setMeta('og:image', image || DEFAULT_IMAGE)
    setMeta('og:type', type)
    setMeta('twitter:title', title)
    setMeta('twitter:description', description)
    setMeta('twitter:image', image || DEFAULT_IMAGE)
    setCanonical(`${BASE_URL}${path}`)

    // JSON-LD
    let script = document.getElementById(JSONLD_ID) as HTMLScriptElement | null
    if (jsonLd) {
      if (!script) {
        script = document.createElement('script')
        script.id = JSONLD_ID
        script.type = 'application/ld+json'
        document.head.appendChild(script)
      }
      script.textContent = JSON.stringify(
        Array.isArray(jsonLd)
          ? { '@context': 'https://schema.org', '@graph': jsonLd }
          : { '@context': 'https://schema.org', ...jsonLd }
      )
    } else if (script) {
      script.remove()
    }

    return () => {
      const s = document.getElementById(JSONLD_ID)
      if (s) s.remove()
    }
  }, [title, description, path, image, type, jsonLd])

  return null
}
