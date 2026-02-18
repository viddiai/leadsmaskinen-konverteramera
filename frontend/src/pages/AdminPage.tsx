import { useQuery } from '@tanstack/react-query'
import { getLeads, getReports, getDashboardStats } from '../utils/api'
import {
  Users,
  FileText,
  TrendingUp,
  Calendar,
  ExternalLink,
  Star,
  AlertTriangle,
  Download,
} from 'lucide-react'
import clsx from 'clsx'

export default function AdminPage() {
  const statsQuery = useQuery({
    queryKey: ['admin-stats'],
    queryFn: getDashboardStats,
  })

  const leadsQuery = useQuery({
    queryKey: ['admin-leads'],
    queryFn: () => getLeads(0, 20),
  })

  const reportsQuery = useQuery({
    queryKey: ['admin-reports'],
    queryFn: () => getReports(0, 20),
  })

  const stats = statsQuery.data
  const leads = leadsQuery.data || []
  const reports = reportsQuery.data || []

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('sv-SE', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="min-h-screen bg-softwhite">
      {/* Header */}
      <header className="bg-white border-b border-lightgrey">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-graphite">
              Admin Dashboard
            </h1>
            <a
              href="/"
              className="text-primary-500 hover:text-primary-600 text-sm transition-colors"
            >
              &larr; Tillbaka till startsidan
            </a>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Totala Leads"
            value={stats?.total_leads ?? '-'}
            icon={<Users size={24} />}
            color="blue"
          />
          <StatCard
            title="Totala Rapporter"
            value={stats?.total_reports ?? '-'}
            icon={<FileText size={24} />}
            color="green"
          />
          <StatCard
            title="Leads Idag"
            value={stats?.leads_today ?? '-'}
            icon={<Calendar size={24} />}
            color="purple"
          />
          <StatCard
            title="Snittbetyg"
            value={stats?.average_score ? `${stats.average_score}/5` : '-'}
            icon={<TrendingUp size={24} />}
            color="orange"
          />
        </div>

        {/* Top Issues */}
        {stats?.top_issues && stats.top_issues.length > 0 && (
          <div className="card mb-8">
            <h2 className="text-lg font-semibold text-graphite mb-4 flex items-center gap-2">
              <AlertTriangle className="text-warning" size={20} />
              Vanligaste Problemen
            </h2>
            <div className="flex flex-wrap gap-2">
              {stats.top_issues.map((issue) => (
                <span
                  key={issue.criterion}
                  className="px-3 py-1 bg-primary-50 text-primary-700 rounded-full text-sm font-medium"
                >
                  {issue.criterion}: {issue.count} st
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Two Column Layout */}
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Leads Table */}
          <div className="card">
            <h2 className="text-lg font-semibold text-graphite mb-4">
              Senaste Leads
            </h2>
            {leadsQuery.isLoading ? (
              <p className="text-steel">Laddar...</p>
            ) : leads.length === 0 ? (
              <p className="text-steel">Inga leads ännu</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-lightgrey">
                      <th className="text-left py-2 font-medium text-steel">
                        Namn
                      </th>
                      <th className="text-left py-2 font-medium text-steel">
                        E-post
                      </th>
                      <th className="text-left py-2 font-medium text-steel">
                        Datum
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((lead) => (
                      <tr
                        key={lead.id}
                        className="border-b border-lightgrey/50 hover:bg-softwhite"
                      >
                        <td className="py-3 text-graphite">
                          {lead.name}
                          {lead.company_name && (
                            <span className="text-steel text-xs block">
                              {lead.company_name}
                            </span>
                          )}
                        </td>
                        <td className="py-3 text-steel">
                          <a
                            href={`mailto:${lead.email}`}
                            className="hover:text-primary-500 transition-colors"
                          >
                            {lead.email}
                          </a>
                        </td>
                        <td className="py-3 text-steel text-xs">
                          {formatDate(lead.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Reports Table */}
          <div className="card">
            <h2 className="text-lg font-semibold text-graphite mb-4">
              Senaste Rapporter
            </h2>
            {reportsQuery.isLoading ? (
              <p className="text-steel">Laddar...</p>
            ) : reports.length === 0 ? (
              <p className="text-steel">Inga rapporter ännu</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-lightgrey">
                      <th className="text-left py-2 font-medium text-steel">
                        URL
                      </th>
                      <th className="text-left py-2 font-medium text-steel">
                        Betyg
                      </th>
                      <th className="text-left py-2 font-medium text-steel">
                        Lead
                      </th>
                      <th className="text-left py-2 font-medium text-steel">
                        PDF
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((report) => (
                      <tr
                        key={report.id}
                        className="border-b border-lightgrey/50 hover:bg-softwhite"
                      >
                        <td className="py-3">
                          <a
                            href={report.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-500 hover:text-primary-600 flex items-center gap-1 transition-colors"
                          >
                            {new URL(report.url).hostname.replace('www.', '')}
                            <ExternalLink size={12} />
                          </a>
                          {report.company_name_detected && (
                            <span className="text-steel text-xs block">
                              {report.company_name_detected}
                            </span>
                          )}
                        </td>
                        <td className="py-3">
                          {report.overall_score !== null ? (
                            <span className="flex items-center gap-1 text-graphite">
                              <Star
                                size={14}
                                className="text-primary-500 fill-primary-500"
                              />
                              {report.overall_score}/5
                            </span>
                          ) : (
                            <span className="text-steel">-</span>
                          )}
                        </td>
                        <td className="py-3 text-steel text-xs">
                          {report.lead_email || (
                            <span className="text-steel/50">Ej konverterad</span>
                          )}
                        </td>
                        <td className="py-3">
                          {report.access_token ? (
                            <a
                              href={`/api/report/${report.id}/pdf?token=${report.access_token}`}
                              className="inline-flex items-center gap-1 px-2 py-1 bg-softwhite text-steel rounded hover:bg-lightgrey transition-colors border border-lightgrey"
                              title="Ladda ner PDF"
                            >
                              <Download size={14} />
                            </a>
                          ) : (
                            <span className="text-lightgrey">
                              <Download size={14} />
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Widget Embed Code */}
        <div className="card mt-8">
          <h2 className="text-lg font-semibold text-graphite mb-4">
            Inbäddningskod för Widget
          </h2>
          <p className="text-steel text-sm mb-4">
            Kopiera och klistra in denna kod på din webbsida för att visa analyswidgeten.
          </p>
          <div className="bg-graphite rounded-lg p-4 overflow-x-auto">
            <pre className="text-primary-300 text-sm">
{`<!-- Conversion Analyzer Widget -->
<div id="conversion-analyzer-widget"></div>
<script>
  window.CAWidgetConfig = {
    theme: 'light',
    primaryColor: '#FF6A3D'
  };
</script>
<script src="${window.location.origin}/api/widget.js"></script>`}
            </pre>
          </div>
          <p className="text-steel text-xs mt-2">
            Eller använd iframe:{' '}
            <code className="bg-softwhite px-1 rounded text-graphite border border-lightgrey">
              {`<iframe src="${window.location.origin}/widget/embed" width="500" height="400"></iframe>`}
            </code>
          </p>
        </div>
      </main>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string
  value: string | number
  icon: React.ReactNode
  color: 'blue' | 'green' | 'purple' | 'orange'
}) {
  const colorClasses = {
    blue: 'bg-info/10 text-info',
    green: 'bg-success/10 text-success',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-primary-50 text-primary-500',
  }

  return (
    <div className="card">
      <div className="flex items-center gap-4">
        <div className={clsx('p-3 rounded-lg', colorClasses[color])}>
          {icon}
        </div>
        <div>
          <p className="text-sm text-steel">{title}</p>
          <p className="text-2xl font-bold text-graphite">
            {value}
          </p>
        </div>
      </div>
    </div>
  )
}
