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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        @keyframes fadeIn { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes scaleIn { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
        @keyframes scoreCount { from { opacity: 0; } to { opacity: 1; } }
        .fade-in { animation: fadeIn 0.5s ease-out forwards; }
        .fade-in-delay-1 { animation: fadeIn 0.5s ease-out 0.1s forwards; opacity: 0; }
        .fade-in-delay-2 { animation: fadeIn 0.5s ease-out 0.2s forwards; opacity: 0; }
        .fade-in-delay-3 { animation: fadeIn 0.5s ease-out 0.3s forwards; opacity: 0; }
        .scale-in { animation: scaleIn 0.4s ease-out forwards; }
        .stars { font-size: 1.1em; letter-spacing: 2px; }
        .stars-large { font-size: 1.8em; letter-spacing: 3px; }
        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; }
        ::selection { background-color: rgba(255, 106, 61, 0.15); color: #FF6A3D; }
        .score-ring { transition: stroke-dashoffset 1s ease-out; }
        .section-card { background: white; border-radius: 16px; border: 1px solid #E7E7E7; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
        .score-bar { height: 6px; border-radius: 3px; background: #E7E7E7; overflow: hidden; }
        .score-bar-fill { height: 100%; border-radius: 3px; transition: width 0.8s ease-out; }
        .criteria-row { transition: background-color 0.15s ease; }
        .criteria-row:hover { background-color: #FAFAFA; }
    </style>
</head>
<body class="bg-softwhite min-h-screen text-steel">
    <!-- Top brand bar -->
    <div class="bg-graphite">
        <div class="container mx-auto px-4 max-w-4xl">
            <div class="flex items-center justify-between py-3">
                <a href="https://leadsmaskinen.se" target="_blank" class="flex items-center gap-2 text-white hover:text-primary-400 transition-colors">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect width="24" height="24" rx="6" fill="#FF6A3D"/>
                        <path d="M7 12L10.5 15.5L17 8.5" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span class="font-display font-bold text-sm tracking-wide">LEADSMASKINEN</span>
                </a>
                <span class="text-xs text-gray-400">Konverteringsanalys</span>
            </div>
        </div>
    </div>

    <div id="app" class="container mx-auto px-4 py-10 max-w-4xl">
        <div id="loading" class="text-center py-24">
            <div class="inline-block w-14 h-14 border-4 border-lightgrey border-t-primary-500 rounded-full animate-spin"></div>
            <p class="mt-5 text-steel text-lg">Laddar din rapport...</p>
        </div>
        <div id="error" class="hidden text-center py-24">
            <div class="w-20 h-20 bg-lightgrey rounded-full flex items-center justify-center mx-auto mb-5">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#6E7378" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            </div>
            <h2 class="text-2xl font-bold text-graphite mb-2">Ingen tillgang</h2>
            <p class="text-steel max-w-md mx-auto" id="error-message"></p>
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
                showError('Ingen atkomsttoken angiven');
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
                showError('Nagot gick fel: ' + err.message);
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

        function getScoreColor(score) {
            if (score >= 4) return '#2ECC71';
            if (score >= 3) return '#F4D03F';
            if (score >= 2) return '#FF6A3D';
            return '#e55a2f';
        }

        function getScoreLabel(score) {
            if (score >= 4) return 'Bra';
            if (score >= 3) return 'Godkant';
            if (score >= 2) return 'Svagt';
            return 'Kritiskt';
        }

        function renderReport(data) {
            document.getElementById('loading').classList.add('hidden');
            const container = document.getElementById('report');
            container.classList.remove('hidden');

            const stars = (score) => {
                const filled = Math.round(score);
                const empty = 5 - filled;
                const color = getScoreColor(score);
                const filledStars = '<span style="color:' + color + '">' + '&#9733;'.repeat(filled) + '</span>';
                const emptyStars = '<span class="text-lightgrey">' + '&#9734;'.repeat(empty) + '</span>';
                return '<span class="stars">' + filledStars + emptyStars + '</span>';
            };

            const scorePercent = Math.round((data.overall_score / 5) * 100);
            const scoreColor = getScoreColor(data.overall_score);
            const circumference = 2 * Math.PI * 54;
            const dashOffset = circumference - (scorePercent / 100) * circumference;

            const criteriaExplanations = data.criteria_explanations || {};

            container.innerHTML = `
                <div class="fade-in">
                    <!-- Hero header -->
                    <header class="mb-12">
                        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-8">
                            <div class="flex-1">
                                <h1 class="font-display text-3xl md:text-4xl font-extrabold text-graphite leading-tight mb-4">
                                    Konverteringsanalys for<br>${escapeHtml(data.company_name) || 'Er Webbsida'}
                                </h1>
                                <div class="flex flex-wrap items-center gap-3 mb-3">
                                    ${data.industry_label ? `<span class="inline-flex items-center gap-1.5 bg-primary-50 text-primary-600 text-xs font-semibold px-3 py-1.5 rounded-full border border-primary-100">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                                        ${escapeHtml(data.industry_label)}
                                    </span>` : ''}
                                    <span class="inline-flex items-center gap-1.5 bg-white text-steel text-xs font-medium px-3 py-1.5 rounded-full border border-lightgrey">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                                        ${new Date(data.created_at).toLocaleDateString('sv-SE')}
                                    </span>
                                </div>
                                <a href="${escapeHtml(data.url)}" target="_blank" class="text-sm text-primary-500 hover:text-primary-600 transition-colors underline decoration-primary-200 hover:decoration-primary-400">${escapeHtml(data.url)}</a>
                            </div>
                            <!-- Score circle -->
                            <div class="scale-in flex-shrink-0 flex flex-col items-center">
                                <div class="relative w-36 h-36">
                                    <svg class="w-36 h-36 -rotate-90" viewBox="0 0 120 120">
                                        <circle cx="60" cy="60" r="54" fill="none" stroke="#E7E7E7" stroke-width="8"/>
                                        <circle cx="60" cy="60" r="54" fill="none" stroke="${scoreColor}" stroke-width="8" stroke-linecap="round" stroke-dasharray="${circumference}" stroke-dashoffset="${dashOffset}" class="score-ring"/>
                                    </svg>
                                    <div class="absolute inset-0 flex flex-col items-center justify-center">
                                        <span class="text-3xl font-extrabold text-graphite">${data.overall_score.toFixed(1)}</span>
                                        <span class="text-xs text-steel">av 5.0</span>
                                    </div>
                                </div>
                                <span class="mt-2 text-xs font-semibold uppercase tracking-wider" style="color: ${scoreColor}">${getScoreLabel(data.overall_score)}</span>
                                <span class="text-xs text-steel mt-0.5">${data.issues_count} problem identifierade</span>
                            </div>
                        </div>
                    </header>

                    <!-- Kort beskrivning -->
                    <section class="section-card p-6 md:p-8 mb-6 fade-in-delay-1">
                        <h2 class="font-display text-xl font-bold text-graphite mb-3">Sammanfattning</h2>
                        <p class="text-steel leading-relaxed text-base">${escapeHtml(data.short_description || data.company_description) || 'Ingen beskrivning tillganglig.'}</p>
                    </section>

                    <!-- Resultat: Leadmagneter, formular och innehall -->
                    <section class="section-card p-6 md:p-8 mb-6 fade-in-delay-2">
                        <h2 class="font-display text-xl font-bold text-graphite mb-5">Identifierade element</h2>

                        ${data.lead_magnets_analysis ? `
                        <p class="text-steel leading-relaxed mb-5">${escapeHtml(data.lead_magnets_analysis)}</p>
                        ` : `
                        <p class="text-steel mb-5">${escapeHtml(data.company_name) || 'Webbplatsen'} har ${data.lead_magnets?.length || 0} identifierade leadmagneter.</p>
                        `}

                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
                            <div class="bg-softwhite rounded-xl p-4 border border-lightgrey">
                                <div class="flex items-center gap-2 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-primary-50 flex items-center justify-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                                    </div>
                                    <span class="text-sm font-semibold text-graphite">Leadmagneter</span>
                                </div>
                                <p class="text-2xl font-bold text-graphite">${data.lead_magnets?.length || 0}</p>
                                <p class="text-xs text-steel mt-1">${escapeHtml((data.lead_magnets || []).slice(0, 2).map(lm => lm.text || '').filter(Boolean).join(', ')) || 'Inga hittades'}</p>
                            </div>
                            <div class="bg-softwhite rounded-xl p-4 border border-lightgrey">
                                <div class="flex items-center gap-2 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-primary-50 flex items-center justify-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="18" rx="2"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="10" y1="3" x2="10" y2="21"/></svg>
                                    </div>
                                    <span class="text-sm font-semibold text-graphite">Formular</span>
                                </div>
                                <p class="text-2xl font-bold text-graphite">${data.forms?.length || 0}</p>
                                <p class="text-xs text-steel mt-1">st identifierade</p>
                            </div>
                            <div class="bg-softwhite rounded-xl p-4 border border-lightgrey">
                                <div class="flex items-center gap-2 mb-2">
                                    <div class="w-8 h-8 rounded-lg bg-primary-50 flex items-center justify-center">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
                                    </div>
                                    <span class="text-sm font-semibold text-graphite">CTAs</span>
                                </div>
                                <p class="text-2xl font-bold text-graphite">${data.cta_buttons?.length || 0}</p>
                                <p class="text-xs text-steel mt-1">${escapeHtml((data.cta_buttons || []).slice(0, 2).map(c => c.text || '').filter(Boolean).join(', ')) || 'Inga hittades'}</p>
                            </div>
                        </div>

                        ${data.forms_analysis ? `<p class="text-steel leading-relaxed mb-3">${escapeHtml(data.forms_analysis)}</p>` : ''}
                        ${data.cta_analysis ? `<p class="text-steel leading-relaxed">${escapeHtml(data.cta_analysis)}</p>` : ''}
                    </section>

                    <!-- Avgorande insikter -->
                    <section class="section-card p-6 md:p-8 mb-6 fade-in-delay-3 border-l-4 border-l-primary-500">
                        <div class="flex items-center gap-2 mb-4">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                            <h2 class="font-display text-xl font-bold text-graphite">Avgorande insikter</h2>
                        </div>
                        <div class="text-steel leading-relaxed whitespace-pre-line text-base">
                            ${data.logical_verdict ? escapeHtml(data.logical_verdict) : (data.ai_generated ? 'Ingen detaljerad analys tillganglig.' : '<div class="flex items-center gap-2 text-steel"><svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Genererar AI-analys...</div>')}
                        </div>
                    </section>

                    <!-- Konverteringsanalys -->
                    <section class="section-card p-6 md:p-8 mb-6">
                        <h2 class="font-display text-xl font-bold text-graphite mb-6">Konverteringsanalys</h2>
                        <div class="space-y-0">
                            <!-- Table header -->
                            <div class="hidden md:grid md:grid-cols-12 gap-4 pb-3 border-b border-lightgrey mb-1">
                                <div class="col-span-3 text-xs font-semibold text-steel uppercase tracking-wider">Kriterium</div>
                                <div class="col-span-2 text-xs font-semibold text-steel uppercase tracking-wider">Betyg</div>
                                <div class="col-span-7 text-xs font-semibold text-steel uppercase tracking-wider">Analys</div>
                            </div>
                            ${(data.criteria_analysis || []).map(c => {
                                const criterionKey = c.criterion.toLowerCase().replace(/_/g, '_');
                                const aiExplanation = criteriaExplanations[criterionKey] || criteriaExplanations[c.criterion] || c.explanation;
                                const barWidth = (c.score / 5) * 100;
                                const barColor = getScoreColor(c.score);
                                return `
                                <div class="criteria-row py-4 border-b border-lightgrey last:border-0 md:grid md:grid-cols-12 gap-4">
                                    <div class="col-span-3 mb-2 md:mb-0">
                                        <span class="font-semibold text-graphite text-sm">${escapeHtml(c.criterion_label)}</span>
                                    </div>
                                    <div class="col-span-2 mb-2 md:mb-0 flex flex-col gap-1.5">
                                        <div class="flex items-center gap-2">
                                            ${stars(c.score)}
                                            <span class="text-xs font-medium text-steel">${c.score}/5</span>
                                        </div>
                                        <div class="score-bar w-full max-w-[100px]">
                                            <div class="score-bar-fill" style="width: ${barWidth}%; background-color: ${barColor}"></div>
                                        </div>
                                    </div>
                                    <div class="col-span-7">
                                        <p class="text-steel text-sm leading-relaxed">${escapeHtml(aiExplanation)}</p>
                                    </div>
                                </div>
                                `;
                            }).join('')}
                        </div>
                    </section>

                    <!-- Sammanfattande bedomning -->
                    <section class="section-card p-6 md:p-8 mb-6">
                        <h2 class="font-display text-xl font-bold text-graphite mb-5">Sammanfattande bedomning</h2>
                        <div class="space-y-4">
                            ${(data.summary_assessment || 'Ingen sammanfattning tillganglig.').split(String.fromCharCode(10)).filter(line => line.trim()).map((line, i) => `
                            <div class="flex items-start gap-3 ${i > 0 ? 'pt-4 border-t border-lightgrey/50' : ''}">
                                <div class="w-6 h-6 rounded-full bg-primary-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                                    <div class="w-2 h-2 bg-primary-500 rounded-full"></div>
                                </div>
                                <p class="text-steel leading-relaxed text-sm">${escapeHtml(line.trim())}</p>
                            </div>
                            `).join('')}
                        </div>
                    </section>

                    <!-- Rekommendationer -->
                    <section class="section-card p-6 md:p-8 mb-6 bg-gradient-to-br from-primary-50 to-white border-primary-100">
                        <div class="flex items-center gap-2 mb-5">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                            <h2 class="font-display text-xl font-bold text-primary-700">Rekommendationer</h2>
                        </div>
                        <ol class="space-y-4">
                            ${(data.recommendations || []).map((r, i) => `
                            <li class="flex gap-4 items-start">
                                <span class="flex-shrink-0 w-7 h-7 bg-primary-500 text-white rounded-lg flex items-center justify-center text-sm font-bold shadow-sm">${i + 1}</span>
                                <p class="text-steel text-sm leading-relaxed pt-0.5">${escapeHtml(r)}</p>
                            </li>
                            `).join('')}
                        </ol>
                    </section>

                    <!-- Nasta steg CTA -->
                    <section class="relative overflow-hidden rounded-2xl mb-8 bg-graphite p-8 md:p-10">
                        <div class="absolute top-0 right-0 w-64 h-64 bg-primary-500/10 rounded-full -translate-y-1/2 translate-x-1/2"></div>
                        <div class="absolute bottom-0 left-0 w-48 h-48 bg-primary-500/5 rounded-full translate-y-1/2 -translate-x-1/2"></div>
                        <div class="relative">
                            <h2 class="font-display text-2xl md:text-3xl font-extrabold text-white mb-3">
                                Redo att fixa luckorna?
                            </h2>
                            <p class="text-gray-300 leading-relaxed mb-6 max-w-lg">
                                Vi har identifierat ${data.issues_count} problem som hindrar er fran att maximera konverteringen. Boka en kostnadsfri genomgang for att se exakt hur ni kan atgarda dem.
                            </p>
                            <div class="flex flex-col sm:flex-row gap-3">
                                <a href="https://calendly.com/stefan-245/30min"
                                   target="_blank"
                                   class="inline-flex items-center justify-center gap-2 px-8 py-4 bg-primary-500 text-white font-bold rounded-xl hover:bg-primary-600 transition-all shadow-lg shadow-primary-500/30 text-base hover:-translate-y-0.5">
                                    Boka genomgang
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                                </a>
                                <a href="/api/report/${data.report_id}/pdf?token=${new URLSearchParams(window.location.search).get('token')}"
                                   class="inline-flex items-center justify-center gap-2 px-6 py-4 bg-white/10 text-white font-medium rounded-xl hover:bg-white/20 transition-all text-sm border border-white/20">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                    Ladda ner som PDF
                                </a>
                            </div>
                        </div>
                    </section>

                    <!-- Footer -->
                    <footer class="text-center py-8">
                        <a href="https://leadsmaskinen.se" target="_blank" class="inline-flex items-center gap-2 text-steel hover:text-primary-500 transition-colors text-sm">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <rect width="24" height="24" rx="6" fill="#FF6A3D"/>
                                <path d="M7 12L10.5 15.5L17 8.5" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                            Genererad av Leadsmaskinen
                        </a>
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
