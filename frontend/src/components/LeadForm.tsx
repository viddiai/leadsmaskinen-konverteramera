import { useState } from 'react'
import { Loader2, ArrowLeft, Check } from 'lucide-react'
import type { LeadRequest } from '../utils/types'

interface LeadFormProps {
  reportId: number
  onSubmit: (data: LeadRequest) => Promise<void>
  onBack: () => void
  isLoading: boolean
  isSuccess: boolean
}

export function LeadForm({ reportId, onSubmit, onBack, isLoading, isSuccess }: LeadFormProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!name.trim()) {
      setError('Namn krävs')
      return
    }

    if (!email.trim()) {
      setError('E-post krävs')
      return
    }

    if (!email.includes('@') || !email.includes('.')) {
      setError('Ange en giltig e-postadress')
      return
    }

    await onSubmit({
      name: name.trim(),
      email: email.trim(),
      company_name: company.trim() || null,
      report_id: reportId,
    })
  }

  if (isSuccess) {
    return (
      <div className="card animate-slide-up max-w-md mx-auto text-center">
        <div className="w-16 h-16 bg-success/10 rounded-full flex items-center justify-center mx-auto mb-4">
          <Check className="text-success" size={32} />
        </div>
        <h2 className="text-xl font-bold text-graphite mb-2">
          Tack!
        </h2>
        <p className="text-steel">
          Din fullständiga rapport laddas nu...
        </p>
      </div>
    )
  }

  return (
    <div className="card animate-slide-up max-w-md mx-auto">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-steel hover:text-graphite text-sm mb-4 transition-colors"
      >
        <ArrowLeft size={16} />
        Tillbaka
      </button>

      <h2 className="text-xl font-bold text-graphite mb-2">
        Fyll i för att få rapporten
      </h2>
      <p className="text-steel text-sm mb-6">
        Vi skickar inga spam &ndash; bara din rapport.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-graphite mb-1">
            Namn *
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ditt namn"
            className="input-field"
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-graphite mb-1">
            E-post *
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="din@email.se"
            className="input-field"
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="company" className="block text-sm font-medium text-graphite mb-1">
            Företagsnamn (valfritt)
          </label>
          <input
            id="company"
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Ditt företag AB"
            className="input-field"
            disabled={isLoading}
          />
        </div>

        {error && (
          <p className="text-red-500 text-sm font-medium">{error}</p>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              Skickar...
            </>
          ) : (
            'Få den fullständiga rapporten'
          )}
        </button>
      </form>
    </div>
  )
}
