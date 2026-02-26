import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { UrlInput } from '../components/UrlInput'
import { AnalysisResult } from '../components/AnalysisResult'
import { LeadForm } from '../components/LeadForm'
import { analyzeUrl, submitLead } from '../utils/api'
import type { AnalyzeResponse, LeadRequest } from '../utils/types'
import { BarChart2, Target, TrendingUp } from 'lucide-react'

type ViewState = 'input' | 'result' | 'form' | 'success'

export default function HomePage() {
  const [view, setView] = useState<ViewState>('input')
  const [analysisData, setAnalysisData] = useState<AnalyzeResponse | null>(null)

  const analyzeMutation = useMutation({
    mutationFn: analyzeUrl,
    onSuccess: (data) => {
      setAnalysisData(data)
      setView('result')
    },
  })

  const leadMutation = useMutation({
    mutationFn: submitLead,
    onSuccess: (data) => {
      setView('success')
      if (data.access_token && analysisData) {
        const apiBase = import.meta.env.VITE_API_URL || ''
        const reportUrl = `${apiBase}/report/${analysisData.report_id}?token=${data.access_token}`
        const redirectTarget = `https://leadsmaskinen-website.vercel.app/konverteringsanalys/?report=${encodeURIComponent(reportUrl)}`
        setTimeout(() => {
          window.location.href = redirectTarget
        }, 1500)
      }
    },
  })

  const handleAnalyze = (url: string) => {
    analyzeMutation.mutate(url)
  }

  const handleLeadSubmit = async (data: LeadRequest) => {
    await leadMutation.mutateAsync(data)
  }

  return (
    <div className="min-h-screen bg-softwhite">
      {/* Hero Section */}
      <header className="pt-16 pb-12 px-4 bg-softwhite">
        <div className="container mx-auto max-w-4xl text-center">
          <span className="inline-block text-primary-500 font-semibold text-sm px-4 py-1.5 rounded-full border border-primary-100 bg-primary-50 mb-6 animate-fade-slide-in">
            Gratis verktyg
          </span>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold mb-6 text-graphite animate-fade-slide-in leading-tight">
            Testa din webbsidas konverteringsförmåga
          </h1>
          <p className="text-lg text-steel mb-10 max-w-2xl mx-auto leading-relaxed">
            Få en obarmhärtig analys av vad som hindrar din webbsida från att konvertera besökare till leads.
          </p>

          {view === 'input' && (
            <div className="card max-w-2xl mx-auto text-left">
              <h2 className="text-lg font-bold text-graphite mb-4">
                Analysera din webbsidas konverteringsförmåga
              </h2>
              <UrlInput
                onSubmit={handleAnalyze}
                isLoading={analyzeMutation.isPending}
              />
            </div>
          )}

          {analyzeMutation.isError && (
            <p className="mt-4 text-red-500 font-medium">
              {(analyzeMutation.error as Error).message || 'Något gick fel. Försök igen.'}
            </p>
          )}
        </div>
      </header>

      {/* Result/Form Section */}
      {(view === 'result' || view === 'form' || view === 'success') && (
        <section className="py-12 px-4 bg-softwhite">
          {view === 'result' && analysisData && (
            <AnalysisResult
              data={analysisData}
              onGetFullReport={() => setView('form')}
            />
          )}

          {(view === 'form' || view === 'success') && analysisData && (
            <LeadForm
              reportId={analysisData.report_id}
              onSubmit={handleLeadSubmit}
              onBack={() => setView('result')}
              isLoading={leadMutation.isPending}
              isSuccess={view === 'success'}
            />
          )}
        </section>
      )}

      {/* Features Section - Only show on input view */}
      {view === 'input' && (
        <section className="py-20 px-4 bg-softwhite">
          <div className="container mx-auto max-w-5xl">
            <h2 className="font-display text-3xl font-bold text-center text-graphite mb-4">
              Vad vi analyserar
            </h2>
            <p className="text-steel text-center mb-12 max-w-2xl mx-auto">
              Förutsägbara leads. Mätbar ROI. Inga gissningar.
            </p>
            <div className="grid md:grid-cols-3 gap-8">
              <FeatureCard
                icon={<Target className="text-primary-500" size={32} />}
                title="Leadmagneter & Formulär"
                description="Vi hittar läckande trattar - mailto-länkar och öppna PDF:er som ger bort värde utan att fånga leads."
              />
              <FeatureCard
                icon={<BarChart2 className="text-primary-500" size={32} />}
                title="Konverteringselement"
                description="CTA-knappar, värdeerbjudande, social proof - allt som påverkar om besökare konverterar eller studsar."
              />
              <FeatureCard
                icon={<TrendingUp className="text-primary-500" size={32} />}
                title="Konkreta Rekommendationer"
                description="Inga fluffiga tips. Fem konkreta åtgärder prioriterade efter påverkan på din konvertering."
              />
            </div>
          </div>
        </section>
      )}

      {/* Guide Value Proposition */}
      {view === 'input' && (
        <section className="py-16 px-4 bg-white border-t border-lightgrey">
          <div className="container mx-auto max-w-5xl">
            <div className="bg-softwhite rounded-2xl p-8 md:p-12 flex flex-col md:flex-row gap-8 items-center border border-lightgrey">
              {/* Guide Cover Image */}
              <div className="flex-shrink-0 w-full md:w-80">
                <div className="bg-graphite rounded-xl p-6 text-center">
                  <div className="w-8 h-8 mx-auto mb-4">
                    <svg viewBox="0 0 24 24" fill="none" className="text-primary-500">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.3"/>
                      <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <h3 className="text-white font-display text-xl font-bold mb-2 leading-tight">
                    7 beprövade sätt att öka konverteringen och vinna fler affärer
                  </h3>
                  <p className="text-gray-400 text-sm">
                    En strategisk guide för VD:ar och säljchefer på medelstora svenska företag
                  </p>
                  <div className="mt-6 flex justify-center">
                    <div className="relative w-32 h-32">
                      <svg viewBox="0 0 100 100" className="w-full h-full">
                        <polygon points="20,20 80,20 65,50 35,50" fill="#FF6A3D" opacity="0.8"/>
                        <polygon points="35,50 65,50 55,80 45,80" fill="#2ECC71" opacity="0.8"/>
                        <polygon points="45,80 55,80 50,95 50,95" fill="#F4D03F" opacity="0.8"/>
                        <path d="M70,30 Q90,40 85,60" stroke="#FF6A3D" strokeWidth="3" fill="none" markerEnd="url(#arrow)"/>
                        <defs>
                          <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                            <path d="M0,0 L0,6 L9,3 z" fill="#FF6A3D"/>
                          </marker>
                        </defs>
                      </svg>
                    </div>
                  </div>
                </div>
              </div>

              {/* Guide Content */}
              <div className="flex-1">
                <h2 className="font-display text-2xl md:text-3xl font-bold text-graphite mb-4">
                  7 beprövade sätt att öka konverteringen och vinna fler affärer
                </h2>
                <h3 className="text-lg font-semibold text-graphite mb-4">
                  Denna guide ger dig
                </h3>
                <p className="text-steel mb-3">Konkreta verktyg för att:</p>
                <ul className="space-y-2 text-steel mb-6">
                  <li className="flex items-start gap-2">
                    <span className="text-primary-500 mt-1 font-bold">&bull;</span>
                    <span>Formulera ett värdeerbjudande som faktiskt övertygar svenska beslutsfattare</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary-500 mt-1 font-bold">&bull;</span>
                    <span>Fånga upp potentiella kunder innan de är redo att köpa</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary-500 mt-1 font-bold">&bull;</span>
                    <span>Eliminera friktion som dödar affärer</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary-500 mt-1 font-bold">&bull;</span>
                    <span>Bygga systematiskt förtroende genom sociala bevis</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary-500 mt-1 font-bold">&bull;</span>
                    <span>Skapa handlingsdriven kommunikation som leder till avslut</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary-500 mt-1 font-bold">&bull;</span>
                    <span>Strukturera komplex information utan att överväldiga</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary-500 mt-1 font-bold">&bull;</span>
                    <span>Använda avancerade strategier för dramatisk tillväxt</span>
                  </li>
                </ul>
                <div className="flex items-start gap-2 text-steel mb-6">
                  <span className="text-warning">💡</span>
                  <span className="text-sm">
                    Kom ihåg: Varje kapitel avslutas med "3 saker du kan göra imorgon" – konkreta åtgärder som ger omedelbar effekt.
                  </span>
                </div>
                <div className="flex flex-col sm:flex-row gap-4">
                  <input
                    type="email"
                    placeholder="Din e-postadress"
                    className="input-field flex-1"
                  />
                  <button className="btn-primary whitespace-nowrap">
                    Hämta guiden
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="border-t border-lightgrey py-8 px-4 bg-white">
        <div className="container mx-auto max-w-5xl text-center text-steel text-sm">
          <p>Leadsmaskinen.se</p>
          <p className="mt-2">
            <a href="/admin" className="hover:text-primary-500 transition-colors">Admin Dashboard</a>
          </p>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="card text-center hover:shadow-md transition-shadow">
      <div className="w-16 h-16 bg-primary-50 rounded-xl flex items-center justify-center mx-auto mb-4">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-graphite mb-2">
        {title}
      </h3>
      <p className="text-steel text-sm leading-relaxed">
        {description}
      </p>
    </div>
  )
}
