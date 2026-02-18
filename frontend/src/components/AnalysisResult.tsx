import { Star, AlertTriangle, ArrowRight, Lock } from 'lucide-react'
import type { AnalyzeResponse } from '../utils/types'
import clsx from 'clsx'

interface AnalysisResultProps {
  data: AnalyzeResponse
  onGetFullReport: () => void
}

export function AnalysisResult({ data, onGetFullReport }: AnalysisResultProps) {
  const stars = Math.round(data.overall_score)

  return (
    <div className="card animate-slide-up max-w-2xl mx-auto">
      {/* Company info with score */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-bold text-graphite">
            {data.company_name || 'Analysresultat'}
          </h2>
          <div className="flex items-center gap-2">
            <div className="flex">
              {[1, 2, 3, 4, 5].map((i) => (
                <Star
                  key={i}
                  size={22}
                  className={clsx(
                    i <= stars
                      ? 'text-primary-500 fill-primary-500'
                      : 'text-lightgrey'
                  )}
                />
              ))}
            </div>
            <span className="text-lg font-bold text-graphite">
              {data.overall_score}/5
            </span>
          </div>
        </div>
        {data.company_description && (
          <p className="text-steel text-sm">
            {data.company_description.substring(0, 200)}
            {data.company_description.length > 200 && '...'}
          </p>
        )}
      </div>

      {/* Issues */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-2 text-red-600 font-medium mb-3">
          <AlertTriangle size={20} />
          <span>Identifierade problem ({data.issues_count})</span>
        </div>
        <ul className="space-y-2">
          {data.logical_errors.map((error, index) => (
            <li
              key={index}
              className="text-red-700 text-sm flex items-start gap-2"
            >
              <span className="text-red-500 font-bold">&bull;</span>
              {error}
            </li>
          ))}
        </ul>
      </div>

      {/* Sammanfattande bedömning */}
      <div className="mb-6 bg-softwhite border border-lightgrey rounded-lg p-4">
        <h3 className="text-base font-semibold text-graphite mb-3">
          Sammanfattande bedömning:
        </h3>
        <div className="text-steel text-base leading-relaxed space-y-3">
          <p>{data.short_description || data.teaser_text}</p>
          {data.logical_errors.length > 0 && (
            <p>
              De mest kritiska problemen inkluderar: {data.logical_errors.slice(0, 2).join('. ')}.
              Detta påverkar direkt er förmåga att konvertera besökare till leads.
            </p>
          )}
          <p className="text-steel/60 italic">
            Den fullständiga rapporten innehåller detaljerad analys av era leadmagneter,
            formulärdesign, CTAs och konkreta rekommendationer för att öka er konvertering.
          </p>
        </div>
      </div>

      {/* Blurred Report Preview */}
      <div className="relative mb-6 rounded-lg overflow-hidden border border-lightgrey">
        <div className="blur-[2px] select-none pointer-events-none p-4 bg-softwhite">
          <div className="space-y-3">
            <div className="flex justify-between items-center mb-2">
              <div className="h-5 bg-lightgrey rounded w-48"></div>
              <div className="flex gap-1">
                <div className="h-4 w-4 bg-primary-200 rounded"></div>
                <div className="h-4 w-4 bg-primary-200 rounded"></div>
                <div className="h-4 w-4 bg-lightgrey rounded"></div>
              </div>
            </div>
            <div className="h-3 bg-lightgrey rounded w-full"></div>
            <div className="h-3 bg-lightgrey rounded w-11/12"></div>
            <div className="h-3 bg-lightgrey rounded w-4/5"></div>
            <div className="mt-4 pt-3 border-t border-lightgrey">
              <div className="h-4 bg-lightgrey rounded w-56 mb-3"></div>
              <div className="h-3 bg-lightgrey/70 rounded w-full"></div>
              <div className="h-3 bg-lightgrey/70 rounded w-5/6 mt-1"></div>
            </div>
            <div className="mt-4 pt-3 border-t border-lightgrey">
              <div className="h-4 bg-lightgrey rounded w-44 mb-3"></div>
              <div className="grid grid-cols-3 gap-2 mb-2">
                <div className="h-6 bg-lightgrey/50 rounded"></div>
                <div className="h-6 bg-lightgrey/50 rounded"></div>
                <div className="h-6 bg-lightgrey/50 rounded"></div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="h-6 bg-lightgrey/50 rounded"></div>
                <div className="h-6 bg-lightgrey/50 rounded"></div>
                <div className="h-6 bg-lightgrey/50 rounded"></div>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-lightgrey">
              <div className="h-4 bg-primary-100 rounded w-40 mb-3"></div>
              <div className="flex gap-2 items-center mb-2">
                <div className="h-5 w-5 bg-primary-100 rounded-full flex-shrink-0"></div>
                <div className="h-3 bg-lightgrey/70 rounded w-full"></div>
              </div>
              <div className="flex gap-2 items-center">
                <div className="h-5 w-5 bg-primary-100 rounded-full flex-shrink-0"></div>
                <div className="h-3 bg-lightgrey/70 rounded w-5/6"></div>
              </div>
            </div>
          </div>
        </div>
        {/* Overlay with lock icon */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/40 to-white/80 flex items-center justify-center">
          <div className="text-center bg-white border border-lightgrey px-6 py-4 rounded-lg shadow-sm">
            <Lock className="mx-auto text-steel mb-2" size={24} />
            <p className="text-sm text-graphite font-medium">
              Fullständig rapport
            </p>
          </div>
        </div>
      </div>

      {/* CTA */}
      <button
        onClick={onGetFullReport}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        Få den fullständiga rapporten
        <ArrowRight size={20} />
      </button>
    </div>
  )
}
