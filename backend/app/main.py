"""
FastAPI main application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from app.core.config import settings
from app.core.database import engine, Base
from app.core.auth import verify_admin
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Creates database tables on startup.
    """
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print(f"✓ Database tables created")
    print(f"✓ {settings.APP_NAME} v{settings.APP_VERSION} started")

    yield

    # Cleanup on shutdown
    print("Shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Analysera webbsidors konverteringsförmåga och fånga leads",
    lifespan=lifespan,
)

# Configure CORS - allow all origins for widget embedding
# In production, CORS_ORIGINS can be set to "*" or specific domains
cors_origins = settings.CORS_ORIGINS.strip()
if cors_origins == "*":
    # Allow all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # Must be False when using wildcard
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Specific origins
    origins = [origin.strip() for origin in cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(router, prefix="/api", tags=["api"])


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


# Simple report viewer page
REPORT_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Konverteringsrapport – Leadsmaskinen</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#fff4f0',
                            100: '#ffe8df',
                            200: '#ffd0bf',
                            300: '#ffb89f',
                            400: '#ff916e',
                            500: '#FF6A3D',
                            600: '#e55a2f',
                            700: '#cc4a21',
                        },
                        graphite: '#2B2F33',
                        steel: '#6E7378',
                        softwhite: '#FAFAFA',
                        lightgrey: '#E7E7E7',
                        success: '#2ECC71',
                        warning: '#F4D03F',
                        info: '#3498DB',
                    },
                    fontFamily: {
                        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
                        display: ['Poppins', 'system-ui', '-apple-system', 'sans-serif'],
                    }
                }
            }
        }
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=Poppins:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.3s ease-out forwards; }
        .stars { font-size: 1.1em; letter-spacing: 2px; }
        .stars-large { font-size: 1.8em; letter-spacing: 3px; }
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
        ::selection { background-color: rgba(255, 106, 61, 0.15); color: #FF6A3D; }
    </style>
</head>
<body class="bg-softwhite min-h-screen text-steel">
    <div id="app" class="container mx-auto px-4 py-8 max-w-4xl">
        <div id="loading" class="text-center py-20">
            <div class="inline-block w-12 h-12 border-4 border-lightgrey border-t-primary-500 rounded-full animate-spin"></div>
            <p class="mt-4 text-steel">Laddar rapport...</p>
        </div>
        <div id="error" class="hidden text-center py-20">
            <div class="text-6xl mb-4">🔒</div>
            <h2 class="text-2xl font-bold text-graphite mb-2">Åtkomst nekad</h2>
            <p class="text-steel" id="error-message"></p>
        </div>
        <div id="report" class="hidden"></div>
    </div>

    <script>
        let pollCount = 0;
        const MAX_POLLS = 30;

        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        async function loadReport() {
            const pathParts = window.location.pathname.split('/');
            const reportId = pathParts[pathParts.length - 1];
            const token = new URLSearchParams(window.location.search).get('token');

            if (!token) {
                showError('Ingen åtkomsttoken angiven');
                return;
            }

            try {
                const response = await fetch('/api/report/' + reportId + '?token=' + token);
                if (!response.ok) {
                    const data = await response.json();
                    showError(data.detail || 'Kunde inte ladda rapporten');
                    return;
                }

                const data = await response.json();
                console.log('Report data loaded:', data);
                try {
                    renderReport(data);
                } catch (renderErr) {
                    console.error('Render error:', renderErr);
                    showError('Kunde inte rendera rapporten: ' + renderErr.message);
                }

                if (!data.ai_generated && pollCount < MAX_POLLS) {
                    pollCount++;
                    setTimeout(() => {
                        refreshReport(reportId, token);
                    }, 2000);
                }
            } catch (err) {
                showError('Något gick fel: ' + err.message);
            }
        }

        async function refreshReport(reportId, token) {
            try {
                const response = await fetch('/api/report/' + reportId + '?token=' + token);
                if (response.ok) {
                    const data = await response.json();
                    renderReport(data);

                    if (!data.ai_generated && pollCount < MAX_POLLS) {
                        pollCount++;
                        setTimeout(() => {
                            refreshReport(reportId, token);
                        }, 2000);
                    }
                }
            } catch (err) {
                console.error('Error refreshing report:', err);
            }
        }

        function showError(message) {
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('error').classList.remove('hidden');
            document.getElementById('error-message').textContent = message;
        }

        function renderReport(data) {
            document.getElementById('loading').classList.add('hidden');
            const container = document.getElementById('report');
            container.classList.remove('hidden');

            const stars = (score, large = false) => {
                const filled = Math.round(score);
                const empty = 5 - filled;
                const filledStars = '<span class="text-primary-500">' + '★'.repeat(filled) + '</span>';
                const emptyStars = '<span class="text-lightgrey">' + '☆'.repeat(empty) + '</span>';
                const sizeClass = large ? 'stars-large' : 'stars';
                return '<span class="' + sizeClass + '">' + filledStars + emptyStars + '</span>';
            };

            const criteriaExplanations = data.criteria_explanations || {};

            container.innerHTML = `
                <div class="fade-in">
                    <header class="mb-8">
                        <h1 class="font-display text-2xl font-bold text-graphite mb-2">
                            Analys av leadgenerering och konverteringsoptimering för ${escapeHtml(data.company_name) || 'Er Webbsida'}
                        </h1>
                        ${data.industry_label ? `<p class="text-primary-500 text-sm font-medium mb-2">Bransch: ${escapeHtml(data.industry_label)}</p>` : ''}
                        <p class="text-steel text-sm">Analyserad: ${new Date(data.created_at).toLocaleDateString('sv-SE')}</p>
                        <p class="text-steel text-sm">URL: <a href="${escapeHtml(data.url)}" target="_blank" class="text-primary-500 hover:text-primary-600 transition-colors">${escapeHtml(data.url)}</a></p>
                    </header>

                    <!-- Kort beskrivning -->
                    <section class="mb-8">
                        <h2 class="text-lg font-semibold text-graphite mb-3">Kort beskrivning:</h2>
                        <p class="text-steel leading-relaxed">${escapeHtml(data.short_description || data.company_description) || 'Ingen beskrivning tillgänglig.'}</p>
                    </section>

                    <!-- Resultat: Leadmagneter, formulär och innehåll -->
                    <section class="mb-8">
                        <h2 class="text-lg font-semibold text-graphite mb-4">Resultat: Leadmagneter, nyhetsbrev, värdeskapande innehåll och formulär</h2>

                        ${data.lead_magnets_analysis ? `
                        <div class="text-steel leading-relaxed mb-4">${escapeHtml(data.lead_magnets_analysis)}</div>
                        ` : `
                        <p class="text-steel mb-4">${escapeHtml(data.company_name) || 'Webbplatsen'} har ${data.lead_magnets?.length || 0} identifierade leadmagneter.</p>
                        `}

                        <ul class="space-y-2 mb-4 text-steel">
                            <li><strong class="text-graphite">Leadmagneter:</strong> ${data.lead_magnets?.length || 0} identifierade. ${escapeHtml((data.lead_magnets || []).slice(0, 3).map(lm => lm.text || '').join(', ')) || 'Inga specifika hittades.'}</li>
                            <li><strong class="text-graphite">Formulär:</strong> ${data.forms?.length || 0} st identifierade.</li>
                            <li><strong class="text-graphite">CTA:</strong> ${escapeHtml((data.cta_buttons || []).slice(0, 5).map(c => '"' + (c.text || '') + '"').join(', ')) || 'Inga tydliga CTAs hittades.'}</li>
                        </ul>

                        ${data.forms_analysis ? `
                        <div class="text-steel leading-relaxed mb-4">${escapeHtml(data.forms_analysis)}</div>
                        ` : ''}

                        ${data.cta_analysis ? `
                        <div class="text-steel leading-relaxed">${escapeHtml(data.cta_analysis)}</div>
                        ` : ''}
                    </section>

                    <!-- Avgörande insikter -->
                    <section class="mb-8">
                        <h2 class="text-lg font-semibold text-graphite mb-3">Avgörande insikter:</h2>
                        <div class="text-steel leading-relaxed whitespace-pre-line">
                            ${data.logical_verdict ? escapeHtml(data.logical_verdict) : (data.ai_generated ? 'Ingen detaljerad analys tillgänglig.' : '<div class="flex items-center gap-2 text-steel"><svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Genererar AI-analys...</div>')}
                        </div>
                    </section>

                    <!-- Konverteringsanalys tabell -->
                    <section class="mb-8">
                        <h2 class="text-lg font-semibold text-graphite mb-4">Konverteringsanalys (tabell)</h2>
                        <div class="overflow-x-auto bg-white rounded-xl border border-lightgrey shadow-sm">
                            <table class="w-full text-left">
                                <thead class="bg-softwhite">
                                    <tr class="border-b border-lightgrey">
                                        <th class="py-3 px-4 font-medium text-graphite">Kriterium</th>
                                        <th class="py-3 px-4 font-medium text-graphite">Betyg</th>
                                        <th class="py-3 px-4 font-medium text-graphite">Logisk förklaring (hård och direkt)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${(data.criteria_analysis || []).map(c => {
                                        const criterionKey = c.criterion.toLowerCase().replace(/_/g, '_');
                                        const aiExplanation = criteriaExplanations[criterionKey] || criteriaExplanations[c.criterion] || c.explanation;
                                        return `
                                        <tr class="border-b border-lightgrey hover:bg-softwhite">
                                            <td class="py-3 px-4 font-medium text-graphite">${escapeHtml(c.criterion_label)}</td>
                                            <td class="py-3 px-4">${stars(c.score)}</td>
                                            <td class="py-3 px-4 text-steel">${escapeHtml(aiExplanation)}</td>
                                        </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <!-- Sammanfattande bedömning -->
                    <section class="mb-8">
                        <h2 class="text-lg font-semibold text-graphite mb-4">Sammanfattande bedömning:</h2>
                        <div class="bg-white rounded-xl border border-lightgrey p-5 shadow-sm">
                            <div class="flex flex-col gap-4">
                                ${(data.summary_assessment || 'Ingen sammanfattning tillgänglig.').split(String.fromCharCode(10)).filter(line => line.trim()).map(line => `
                                <div class="flex items-start gap-3">
                                    <div class="w-2 h-2 bg-primary-500 rounded-full mt-2 flex-shrink-0"></div>
                                    <span class="text-steel leading-relaxed">${escapeHtml(line.trim())}</span>
                                </div>
                                `).join('')}
                            </div>
                        </div>
                    </section>

                    <!-- Rekommendationer -->
                    <section class="bg-primary-50 rounded-xl p-6 mb-6 border border-primary-100">
                        <h2 class="text-xl font-semibold text-primary-600 mb-4">Rekommendationer</h2>
                        <ol class="space-y-4">
                            ${(data.recommendations || []).map((r, i) => `
                            <li class="flex gap-3">
                                <span class="flex-shrink-0 w-6 h-6 bg-primary-500 text-white rounded-full flex items-center justify-center text-sm font-bold">${i + 1}</span>
                                <span class="text-steel">${escapeHtml(r)}</span>
                            </li>
                            `).join('')}
                        </ol>
                    </section>

                    <!-- Nästa steg med CTA -->
                    <section class="bg-white rounded-xl p-6 mb-6 border border-lightgrey shadow-sm">
                        <h2 class="text-xl font-semibold text-graphite mb-4">Nästa steg</h2>
                        <p class="text-steel leading-relaxed mb-4">
                            Vill du ha hjälp att åtgärda problemen och öka din konvertering?
                        </p>
                        <a href="https://calendly.com/stefan-245/30min"
                           target="_blank"
                           class="inline-block px-8 py-4 bg-primary-500 text-white font-semibold rounded-lg hover:bg-primary-600 transition-colors shadow-lg shadow-primary-500/20 text-lg">
                            Boka genomgång för ökad konvertering
                        </a>
                    </section>

                    <!-- Ladda ner PDF -->
                    <section class="text-center py-6 border-t border-lightgrey">
                        <a href="/api/report/${data.report_id}/pdf?token=${new URLSearchParams(window.location.search).get('token')}"
                           class="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-steel font-medium rounded-lg hover:bg-softwhite transition-colors border border-lightgrey shadow-sm">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            Ladda ner som PDF
                        </a>
                    </section>

                    <footer class="text-center text-steel text-sm py-8">
                        <p><a href="https://leadsmaskinen.se" target="_blank" class="text-primary-500 hover:text-primary-600 transition-colors">Leadsmaskinen.se</a></p>
                    </footer>
                </div>
            `;
        }

        loadReport();
    </script>
</body>
</html>
'''


@app.get("/report/{report_id}", response_class=HTMLResponse)
async def view_report_page(report_id: int):
    """
    Serve the report viewer page.
    The actual data is fetched via JavaScript.
    """
    return HTMLResponse(content=REPORT_PAGE_TEMPLATE)


# Widget embed page (for iframe embedding)
WIDGET_EMBED_TEMPLATE = '''
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conversion Analyzer Widget</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    </style>
</head>
<body>
    <div id="conversion-analyzer-widget"></div>
    <script>
        window.CAWidgetConfig = {
            theme: new URLSearchParams(window.location.search).get('theme') || 'light',
            primaryColor: new URLSearchParams(window.location.search).get('color') || '#2563eb'
        };
    </script>
    <script src="/api/widget.js"></script>
</body>
</html>
'''


@app.get("/widget/embed", response_class=HTMLResponse)
async def widget_embed_page():
    """
    Serve a standalone widget page for iframe embedding.
    Query params: theme (light/dark), color (hex color)
    """
    return HTMLResponse(content=WIDGET_EMBED_TEMPLATE)


# Admin Dashboard
ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard – Leadsmaskinen</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#fff4f0',
                            100: '#ffe8df',
                            200: '#ffd0bf',
                            300: '#ffb89f',
                            400: '#ff916e',
                            500: '#FF6A3D',
                            600: '#e55a2f',
                            700: '#cc4a21',
                        },
                        graphite: '#2B2F33',
                        steel: '#6E7378',
                        softwhite: '#FAFAFA',
                        lightgrey: '#E7E7E7',
                        success: '#2ECC71',
                        warning: '#F4D03F',
                        info: '#3498DB',
                    }
                }
            }
        }
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=Poppins:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
    </style>
</head>
<body class="bg-softwhite min-h-screen text-steel">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <!-- Header -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-graphite mb-2" style="font-family: 'Poppins', sans-serif;">Admin Dashboard</h1>
            <p class="text-steel">Leadsmaskinen Konverteringsoptimerare &ndash; Statistik och leads</p>
        </header>

        <!-- Loading state -->
        <div id="loading" class="text-center py-20">
            <div class="inline-block w-12 h-12 border-4 border-lightgrey border-t-primary-500 rounded-full animate-spin"></div>
            <p class="mt-4 text-steel">Laddar data...</p>
        </div>

        <!-- Dashboard content -->
        <div id="dashboard" class="hidden">
            <!-- Stats cards -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div class="bg-white rounded-xl p-5 border border-lightgrey shadow-sm">
                    <p class="text-steel text-sm mb-1">Totalt leads</p>
                    <p id="stat-leads" class="text-3xl font-bold text-primary-500">-</p>
                </div>
                <div class="bg-white rounded-xl p-5 border border-lightgrey shadow-sm">
                    <p class="text-steel text-sm mb-1">Totalt rapporter</p>
                    <p id="stat-reports" class="text-3xl font-bold text-graphite">-</p>
                </div>
                <div class="bg-white rounded-xl p-5 border border-lightgrey shadow-sm">
                    <p class="text-steel text-sm mb-1">Leads idag</p>
                    <p id="stat-leads-today" class="text-3xl font-bold text-primary-500">-</p>
                </div>
                <div class="bg-white rounded-xl p-5 border border-lightgrey shadow-sm">
                    <p class="text-steel text-sm mb-1">Snittbetyg</p>
                    <p id="stat-avg-score" class="text-3xl font-bold text-graphite">-</p>
                </div>
            </div>

            <!-- Top Issues -->
            <div class="bg-white rounded-xl p-6 border border-lightgrey shadow-sm mb-8">
                <h2 class="text-xl font-semibold text-graphite mb-4">Vanligaste problemen</h2>
                <div id="top-issues" class="space-y-3"></div>
            </div>

            <!-- Leads table -->
            <div class="bg-white rounded-xl p-6 border border-lightgrey shadow-sm mb-8">
                <h2 class="text-xl font-semibold text-graphite mb-4">Senaste leads</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead class="text-steel text-sm border-b border-lightgrey">
                            <tr>
                                <th class="py-3 px-2">Namn</th>
                                <th class="py-3 px-2">E-post</th>
                                <th class="py-3 px-2">Företag</th>
                                <th class="py-3 px-2">Analyserad URL</th>
                                <th class="py-3 px-2">Datum</th>
                            </tr>
                        </thead>
                        <tbody id="leads-table" class="text-sm"></tbody>
                    </table>
                </div>
            </div>

            <!-- Reports table -->
            <div class="bg-white rounded-xl p-6 border border-lightgrey shadow-sm">
                <h2 class="text-xl font-semibold text-graphite mb-4">Senaste rapporter</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead class="text-steel text-sm border-b border-lightgrey">
                            <tr>
                                <th class="py-3 px-2">ID</th>
                                <th class="py-3 px-2">URL</th>
                                <th class="py-3 px-2">Företag</th>
                                <th class="py-3 px-2">Betyg</th>
                                <th class="py-3 px-2">Lead</th>
                                <th class="py-3 px-2">Datum</th>
                                <th class="py-3 px-2">Åtgärder</th>
                            </tr>
                        </thead>
                        <tbody id="reports-table" class="text-sm"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const criterionLabels = {
            'lead_magnets': 'Lead Magnets',
            'social_proof': 'Social Proof',
            'form_design': 'Formulärdesign',
            'call_to_action': 'Call to Action',
            'value_proposition': 'Värdeerbjudande',
            'guiding_content': 'Vägledande innehåll'
        };

        async function loadDashboard() {
            try {
                const [statsRes, leadsRes, reportsRes] = await Promise.all([
                    fetch('/api/admin/stats'),
                    fetch('/api/admin/leads?limit=20'),
                    fetch('/api/admin/reports?limit=20')
                ]);

                if (!statsRes.ok || !leadsRes.ok || !reportsRes.ok) {
                    throw new Error('Failed to load data');
                }

                const stats = await statsRes.json();
                const leads = await leadsRes.json();
                const reports = await reportsRes.json();

                // Update stats
                document.getElementById('stat-leads').textContent = stats.total_leads;
                document.getElementById('stat-reports').textContent = stats.total_reports;
                document.getElementById('stat-leads-today').textContent = stats.leads_today;
                document.getElementById('stat-avg-score').textContent = stats.average_score ? stats.average_score.toFixed(1) + '/5' : '-';

                // Update top issues
                const issuesHtml = (stats.top_issues || []).map(issue => {
                    const label = criterionLabels[issue.criterion] || issue.criterion;
                    const percentage = Math.round((issue.count / stats.total_reports) * 100);
                    return '<div class="flex items-center gap-3">' +
                        '<div class="flex-1">' +
                            '<div class="flex justify-between mb-1">' +
                                '<span class="text-graphite">' + label + '</span>' +
                                '<span class="text-steel">' + issue.count + ' (' + percentage + '%)</span>' +
                            '</div>' +
                            '<div class="h-2 bg-lightgrey rounded-full overflow-hidden">' +
                                '<div class="h-full bg-primary-500 rounded-full" style="width: ' + percentage + '%"></div>' +
                            '</div>' +
                        '</div>' +
                    '</div>';
                }).join('');
                document.getElementById('top-issues').innerHTML = issuesHtml || '<p class="text-steel">Inga data</p>';

                // Update leads table
                const leadsHtml = leads.map(lead => {
                    const date = new Date(lead.created_at).toLocaleDateString('sv-SE');
                    return '<tr class="border-b border-lightgrey hover:bg-softwhite">' +
                        '<td class="py-3 px-2 text-graphite">' + (lead.name || '-') + '</td>' +
                        '<td class="py-3 px-2"><a href="mailto:' + lead.email + '" class="text-primary-500 hover:text-primary-600">' + lead.email + '</a></td>' +
                        '<td class="py-3 px-2 text-steel">' + (lead.company_name || '-') + '</td>' +
                        '<td class="py-3 px-2 text-steel max-w-xs truncate">' + (lead.analyzed_url || '-') + '</td>' +
                        '<td class="py-3 px-2 text-steel">' + date + '</td>' +
                    '</tr>';
                }).join('');
                document.getElementById('leads-table').innerHTML = leadsHtml || '<tr><td colspan="5" class="py-4 text-center text-steel">Inga leads ännu</td></tr>';

                // Update reports table
                const reportsHtml = reports.map(report => {
                    const date = new Date(report.created_at).toLocaleDateString('sv-SE');
                    const score = report.overall_score ? report.overall_score.toFixed(1) : '-';
                    const scoreColor = report.overall_score >= 3 ? 'text-success' : report.overall_score >= 2 ? 'text-warning' : 'text-red-500';
                    const pdfUrl = report.access_token ? '/api/report/' + report.id + '/pdf?token=' + report.access_token : null;
                    const reportUrl = report.access_token ? '/report/' + report.id + '?token=' + report.access_token : null;
                    return '<tr class="border-b border-lightgrey hover:bg-softwhite">' +
                        '<td class="py-3 px-2 text-steel">#' + report.id + '</td>' +
                        '<td class="py-3 px-2 text-steel max-w-xs truncate">' + report.url + '</td>' +
                        '<td class="py-3 px-2 text-graphite">' + (report.company_name_detected || '-') + '</td>' +
                        '<td class="py-3 px-2 ' + scoreColor + ' font-medium">' + score + '</td>' +
                        '<td class="py-3 px-2 text-steel">' + (report.lead_email || '-') + '</td>' +
                        '<td class="py-3 px-2 text-steel">' + date + '</td>' +
                        '<td class="py-3 px-2">' +
                            (reportUrl ? '<a href="' + reportUrl + '" target="_blank" class="text-primary-500 hover:text-primary-600 mr-3">Visa</a>' : '') +
                            (pdfUrl ? '<a href="' + pdfUrl + '" class="text-steel hover:text-graphite">PDF</a>' : '') +
                        '</td>' +
                    '</tr>';
                }).join('');
                document.getElementById('reports-table').innerHTML = reportsHtml || '<tr><td colspan="7" class="py-4 text-center text-steel">Inga rapporter ännu</td></tr>';

                // Show dashboard
                document.getElementById('loading').classList.add('hidden');
                document.getElementById('dashboard').classList.remove('hidden');

            } catch (err) {
                console.error('Error loading dashboard:', err);
                document.getElementById('loading').innerHTML = '<p class="text-red-500">Kunde inte ladda data</p>';
            }
        }

        loadDashboard();
    </script>
</body>
</html>
'''


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(username: str = Depends(verify_admin)):
    """
    Admin dashboard page - requires Basic Auth.
    """
    return HTMLResponse(content=ADMIN_DASHBOARD_TEMPLATE)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
