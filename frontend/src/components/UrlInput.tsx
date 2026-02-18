import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'

interface UrlInputProps {
  onSubmit: (url: string) => void
  isLoading: boolean
}

export function UrlInput({ onSubmit, isLoading }: UrlInputProps) {
  const [url, setUrl] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    let processedUrl = url.trim()

    if (!processedUrl) {
      setError('Ange en URL')
      return
    }

    // Add https:// if missing
    if (!processedUrl.startsWith('http://') && !processedUrl.startsWith('https://')) {
      processedUrl = 'https://' + processedUrl
    }

    // Validate URL
    try {
      new URL(processedUrl)
    } catch {
      setError('Ogiltig URL')
      return
    }

    onSubmit(processedUrl)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-steel/50" size={20} />
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Ange URL att analysera, t.ex. www.example.se"
            className="input-field pl-12 shadow-sm"
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary flex items-center justify-center gap-2 min-w-[160px]"
        >
          {isLoading ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              Analyserar...
            </>
          ) : (
            'Analysera'
          )}
        </button>
      </div>
      {error && (
        <p className="mt-2 text-red-500 text-sm font-medium">{error}</p>
      )}
    </form>
  )
}
