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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --orange: #FF6A3D;
            --orange-light: #fff4f0;
            --orange-border: #ffe8df;
            --orange-hover: #e55a2f;
            --graphite: #2B2F33;
            --steel: #6E7378;
            --softwhite: #FAFAFA;
            --lightgrey: #E7E7E7;
            --white: #FFFFFF;
            --success: #2ECC71;
            --warning: #F4D03F;
            --danger: #e55a2f;
        }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: var(--softwhite);
            color: var(--steel);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        ::selection { background: rgba(255,106,61,0.15); color: var(--orange); }

        .container { max-width: 800px; margin: 0 auto; padding: 0 24px; }

        /* Top bar */
        .top-bar {
            background: var(--graphite);
            padding: 12px 0;
        }
        .top-bar-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .top-bar a {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--white);
            text-decoration: none;
            font-family: 'Poppins', sans-serif;
            font-weight: 700;
            font-size: 13px;
            letter-spacing: 0.5px;
        }
        .top-bar a:hover { color: var(--orange); }
        .top-bar .label { font-family: 'Inter', sans-serif; font-size: 12px; color: #9ca3af; font-weight: 400; }

        /* Loading & error */
        .state-screen { text-align: center; padding: 96px 24px; }
        .spinner {
            width: 48px; height: 48px;
            border: 4px solid var(--lightgrey);
            border-top-color: var(--orange);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* Hero */
        .hero { padding: 48px 0 0; margin-bottom: 40px; }
        .hero-grid { display: flex; gap: 32px; align-items: flex-start; }
        .hero-content { flex: 1; }
        .hero h1 {
            font-family: 'Poppins', sans-serif;
            font-weight: 800;
            font-size: 32px;
            line-height: 1.2;
            color: var(--graphite);
            margin-bottom: 16px;
        }
        .meta-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
        .tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            font-weight: 500;
            padding: 6px 12px;
            border-radius: 100px;
            border: 1px solid var(--lightgrey);
            background: var(--white);
            color: var(--steel);
        }
        .tag--orange {
            background: var(--orange-light);
            border-color: var(--orange-border);
            color: var(--orange);
            font-weight: 600;
        }
        .hero-url {
            font-size: 14px;
            color: var(--orange);
            text-decoration: underline;
            text-decoration-color: var(--orange-border);
        }
        .hero-url:hover { text-decoration-color: var(--orange); }

        /* Score ring */
        .score-wrap { flex-shrink: 0; text-align: center; }
        .score-ring-svg { width: 136px; height: 136px; }
        .score-ring-bg { fill: none; stroke: var(--lightgrey); stroke-width: 8; }
        .score-ring-value { fill: none; stroke-width: 8; stroke-linecap: round; transition: stroke-dashoffset 1s ease-out; }
        .score-number { font-size: 28px; font-weight: 800; fill: var(--graphite); }
        .score-sub { font-size: 11px; fill: var(--steel); }
        .score-label {
            display: block;
            margin-top: 8px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .score-issues { font-size: 12px; color: var(--steel); margin-top: 2px; }

        /* Cards */
        .card {
            background: var(--white);
            border: 1px solid var(--lightgrey);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }
        .card h2 {
            font-family: 'Poppins', sans-serif;
            font-weight: 700;
            font-size: 20px;
            color: var(--graphite);
            margin-bottom: 16px;
        }
        .card p { color: var(--steel); font-size: 15px; line-height: 1.7; }

        /* Insights card - orange left border */
        .card--insight { border-left: 4px solid var(--orange); }
        .card--insight .card-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
        }

        /* Stats grid */
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
        .stat-box {
            background: var(--softwhite);
            border: 1px solid var(--lightgrey);
            border-radius: 12px;
            padding: 16px;
        }
        .stat-box .stat-icon {
            width: 32px; height: 32px;
            background: var(--orange-light);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 8px;
        }
        .stat-box .stat-label { font-size: 13px; font-weight: 600; color: var(--graphite); margin-bottom: 4px; }
        .stat-box .stat-value { font-size: 24px; font-weight: 700; color: var(--graphite); }
        .stat-box .stat-detail { font-size: 11px; color: var(--steel); margin-top: 4px; }

        /* Criteria table */
        .criteria-header {
            display: grid;
            grid-template-columns: 200px 120px 1fr;
            gap: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--lightgrey);
            margin-bottom: 4px;
        }
        .criteria-header span {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--steel);
        }
        .criteria-row {
            display: grid;
            grid-template-columns: 200px 120px 1fr;
            gap: 16px;
            padding: 16px 0;
            border-bottom: 1px solid var(--lightgrey);
            transition: background 0.15s;
        }
        .criteria-row:last-child { border-bottom: none; }
        .criteria-row:hover { background: var(--softwhite); margin: 0 -16px; padding-left: 16px; padding-right: 16px; border-radius: 8px; }
        .criteria-name { font-size: 14px; font-weight: 600; color: var(--graphite); }
        .criteria-score-col { display: flex; flex-direction: column; gap: 6px; }
        .stars { font-size: 14px; letter-spacing: 2px; }
        .star-filled { color: var(--orange); }
        .star-empty { color: var(--lightgrey); }
        .score-text { font-size: 11px; color: var(--steel); font-weight: 500; }
        .score-bar { height: 4px; background: var(--lightgrey); border-radius: 2px; overflow: hidden; max-width: 80px; }
        .score-bar-fill { height: 100%; border-radius: 2px; transition: width 0.8s ease-out; }
        .criteria-explanation { font-size: 13px; color: var(--steel); line-height: 1.6; }

        /* Summary assessment */
        .assessment-item { display: flex; gap: 12px; align-items: flex-start; }
        .assessment-item + .assessment-item { margin-top: 16px; padding-top: 16px; border-top: 1px solid #f3f4f6; }
        .assessment-dot {
            flex-shrink: 0;
            width: 24px; height: 24px;
            background: var(--orange-light);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 2px;
        }
        .assessment-dot::after {
            content: '';
            width: 8px; height: 8px;
            background: var(--orange);
            border-radius: 50%;
        }
        .assessment-item p { font-size: 14px; color: var(--steel); line-height: 1.7; }

        /* Recommendations */
        .card--recs {
            background: linear-gradient(135deg, var(--orange-light) 0%, var(--white) 100%);
            border-color: var(--orange-border);
        }
        .card--recs h2 { color: var(--orange-hover); }
        .rec-list { list-style: none; }
        .rec-item { display: flex; gap: 14px; align-items: flex-start; }
        .rec-item + .rec-item { margin-top: 14px; }
        .rec-num {
            flex-shrink: 0;
            width: 28px; height: 28px;
            background: var(--orange);
            color: var(--white);
            font-size: 13px;
            font-weight: 700;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 1px 3px rgba(255,106,61,0.3);
        }
        .rec-item p { font-size: 14px; color: var(--steel); line-height: 1.6; padding-top: 3px; }

        /* CTA section */
        .cta-section {
            background: var(--graphite);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 32px;
            position: relative;
            overflow: hidden;
        }
        .cta-section::before {
            content: '';
            position: absolute;
            top: -80px; right: -80px;
            width: 240px; height: 240px;
            background: rgba(255,106,61,0.08);
            border-radius: 50%;
        }
        .cta-section::after {
            content: '';
            position: absolute;
            bottom: -60px; left: -60px;
            width: 180px; height: 180px;
            background: rgba(255,106,61,0.04);
            border-radius: 50%;
        }
        .cta-section > * { position: relative; }
        .cta-section h2 {
            font-family: 'Poppins', sans-serif;
            font-weight: 800;
            font-size: 26px;
            color: var(--white);
            margin-bottom: 12px;
        }
        .cta-section p { color: #d1d5db; font-size: 15px; line-height: 1.6; margin-bottom: 24px; max-width: 480px; }
        .cta-buttons { display: flex; gap: 12px; flex-wrap: wrap; }
        .btn-primary {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 14px 32px;
            background: var(--orange);
            color: var(--white);
            font-weight: 700;
            font-size: 15px;
            border-radius: 12px;
            text-decoration: none;
            box-shadow: 0 4px 16px rgba(255,106,61,0.3);
            transition: all 0.2s;
        }
        .btn-primary:hover { background: var(--orange-hover); transform: translateY(-1px); }
        .btn-secondary {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 14px 24px;
            background: rgba(255,255,255,0.1);
            color: var(--white);
            font-weight: 500;
            font-size: 14px;
            border-radius: 12px;
            text-decoration: none;
            border: 1px solid rgba(255,255,255,0.2);
            transition: all 0.2s;
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.18); }

        /* Footer */
        .report-footer {
            text-align: center;
            padding: 32px 0;
        }
        .report-footer a {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--steel);
            text-decoration: none;
            font-size: 13px;
            transition: color 0.2s;
        }
        .report-footer a:hover { color: var(--orange); }

        /* Animations */
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(16px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .fade-up { animation: fadeUp 0.5s ease-out forwards; }
        .fade-up-1 { animation: fadeUp 0.5s ease-out 0.1s forwards; opacity: 0; }
        .fade-up-2 { animation: fadeUp 0.5s ease-out 0.2s forwards; opacity: 0; }
        .fade-up-3 { animation: fadeUp 0.5s ease-out 0.3s forwards; opacity: 0; }

        /* Mobile */
        @media (max-width: 768px) {
            .hero h1 { font-size: 24px; }
            .hero-grid { flex-direction: column; }
            .score-wrap { align-self: center; }
            .stats-grid { grid-template-columns: 1fr; }
            .criteria-header { display: none; }
            .criteria-row {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .card { padding: 24px; }
            .cta-section { padding: 32px 24px; }
            .cta-buttons { flex-direction: column; }
        }
    </style>
</head>
<body>
    <!-- Top bar -->
    <div class="top-bar">
        <div class="container">
            <div class="top-bar-inner">
                <a href="https://leadsmaskinen.se" target="_blank">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="6" fill="#FF6A3D"/><path d="M7 12L10.5 15.5L17 8.5" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    LEADSMASKINEN
                </a>
                <span class="label">Konverteringsanalys</span>
            </div>
        </div>
    </div>

    <div class="container">
        <div id="loading" class="state-screen">
            <div class="spinner"></div>
            <p style="color:var(--steel);font-size:16px;">Laddar din rapport...</p>
        </div>
        <div id="error" class="state-screen" style="display:none;">
            <div style="width:64px;height:64px;background:var(--lightgrey);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--steel)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            </div>
            <h2 style="font-family:'Poppins',sans-serif;font-size:22px;font-weight:700;color:var(--graphite);margin-bottom:8px;">Ingen tillgång</h2>
            <p id="error-message" style="color:var(--steel);max-width:400px;margin:0 auto;"></p>
        </div>
        <div id="report" style="display:none;"></div>
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
                    setTimeout(() => { refreshReport(reportId, token); }, 2000);
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
                        setTimeout(() => { refreshReport(reportId, token); }, 2000);
                    }
                }
            } catch (err) {
                console.error('Error refreshing report:', err);
            }
        }

        function showError(message) {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('error').style.display = '';
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
            if (score >= 3) return 'Godkänt';
            if (score >= 2) return 'Svagt';
            return 'Kritiskt';
        }

        function renderStars(score) {
            const filled = Math.round(score);
            let html = '<span class="stars">';
            for (let i = 0; i < 5; i++) {
                html += i < filled
                    ? '<span class="star-filled">&#9733;</span>'
                    : '<span class="star-empty">&#9734;</span>';
            }
            html += '</span>';
            return html;
        }

        function renderReport(data) {
            document.getElementById('loading').style.display = 'none';
            const container = document.getElementById('report');
            container.style.display = '';

            const scorePercent = Math.round((data.overall_score / 5) * 100);
            const scoreColor = getScoreColor(data.overall_score);
            const circumference = 2 * Math.PI * 54;
            const dashOffset = circumference - (scorePercent / 100) * circumference;
            const criteriaExplanations = data.criteria_explanations || {};

            container.innerHTML = `
                <div class="fade-up">
                <!-- Hero -->
                <div class="hero">
                    <div class="hero-grid">
                        <div class="hero-content">
                            <h1>Konverteringsanalys för<br>${escapeHtml(data.company_name) || 'Er Webbsida'}</h1>
                            <div class="meta-tags">
                                ${data.industry_label ? '<span class="tag tag--orange"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>' + escapeHtml(data.industry_label) + '</span>' : ''}
                                <span class="tag"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>${new Date(data.created_at).toLocaleDateString('sv-SE')}</span>
                            </div>
                            <a href="${escapeHtml(data.url)}" target="_blank" class="hero-url">${escapeHtml(data.url)}</a>
                        </div>
                        <div class="score-wrap">
                            <svg class="score-ring-svg" viewBox="0 0 120 120" style="transform:rotate(-90deg);">
                                <circle class="score-ring-bg" cx="60" cy="60" r="54"/>
                                <circle class="score-ring-value" cx="60" cy="60" r="54" stroke="${scoreColor}" stroke-dasharray="${circumference}" stroke-dashoffset="${dashOffset}"/>
                            </svg>
                            <svg viewBox="0 0 120 120" style="position:absolute;width:136px;height:136px;top:0;left:50%;transform:translateX(-50%);">
                                <text x="60" y="56" text-anchor="middle" class="score-number">${data.overall_score.toFixed(1)}</text>
                                <text x="60" y="72" text-anchor="middle" class="score-sub">av 5.0</text>
                            </svg>
                            <span class="score-label" style="color:${scoreColor}">${getScoreLabel(data.overall_score)}</span>
                            <span class="score-issues">${data.issues_count} problem identifierade</span>
                        </div>
                    </div>
                </div>

                <!-- Sammanfattning -->
                <div class="card fade-up-1">
                    <h2>Sammanfattning</h2>
                    <p>${escapeHtml(data.short_description || data.company_description) || 'Ingen beskrivning tillgänglig.'}</p>
                </div>

                <!-- Identifierade element -->
                <div class="card fade-up-2">
                    <h2>Identifierade element</h2>
                    ${data.lead_magnets_analysis ? '<p style="margin-bottom:16px;">' + escapeHtml(data.lead_magnets_analysis) + '</p>' : '<p style="margin-bottom:16px;">' + (escapeHtml(data.company_name) || 'Webbplatsen') + ' har ' + (data.lead_magnets?.length || 0) + ' identifierade leadmagneter.</p>'}

                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                            </div>
                            <div class="stat-label">Leadmagneter</div>
                            <div class="stat-value">${data.lead_magnets?.length || 0}</div>
                            <div class="stat-detail">${escapeHtml((data.lead_magnets || []).slice(0, 2).map(lm => lm.text || '').filter(Boolean).join(', ')) || 'Inga hittades'}</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="18" rx="2"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="10" y1="3" x2="10" y2="21"/></svg>
                            </div>
                            <div class="stat-label">Formulär</div>
                            <div class="stat-value">${data.forms?.length || 0}</div>
                            <div class="stat-detail">st identifierade</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
                            </div>
                            <div class="stat-label">CTAs</div>
                            <div class="stat-value">${data.cta_buttons?.length || 0}</div>
                            <div class="stat-detail">${escapeHtml((data.cta_buttons || []).slice(0, 2).map(c => c.text || '').filter(Boolean).join(', ')) || 'Inga hittades'}</div>
                        </div>
                    </div>

                    ${data.forms_analysis ? '<p style="margin-bottom:8px;">' + escapeHtml(data.forms_analysis) + '</p>' : ''}
                    ${data.cta_analysis ? '<p>' + escapeHtml(data.cta_analysis) + '</p>' : ''}
                </div>

                <!-- Avgörande insikter -->
                <div class="card card--insight fade-up-3">
                    <div class="card-header">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                        <h2 style="margin-bottom:0;">Avgörande insikter</h2>
                    </div>
                    <p style="white-space:pre-line;">
                        ${data.logical_verdict ? escapeHtml(data.logical_verdict) : (data.ai_generated ? 'Ingen detaljerad analys tillgänglig.' : '<span style="display:inline-flex;align-items:center;gap:8px;color:var(--steel)"><span class="spinner" style="width:16px;height:16px;border-width:2px;margin:0;"></span> Genererar AI-analys...</span>')}
                    </p>
                </div>

                <!-- Konverteringsanalys -->
                <div class="card">
                    <h2>Konverteringsanalys</h2>
                    <div class="criteria-header">
                        <span>Kriterium</span>
                        <span>Betyg</span>
                        <span>Analys</span>
                    </div>
                    ${(data.criteria_analysis || []).map(c => {
                        const criterionKey = c.criterion.toLowerCase().replace(/_/g, '_');
                        const aiExplanation = criteriaExplanations[criterionKey] || criteriaExplanations[c.criterion] || c.explanation;
                        const barWidth = (c.score / 5) * 100;
                        const barColor = getScoreColor(c.score);
                        return '<div class="criteria-row">' +
                            '<div class="criteria-name">' + escapeHtml(c.criterion_label) + '</div>' +
                            '<div class="criteria-score-col">' +
                                '<div>' + renderStars(c.score) + ' <span class="score-text">' + c.score + '/5</span></div>' +
                                '<div class="score-bar"><div class="score-bar-fill" style="width:' + barWidth + '%;background:' + barColor + '"></div></div>' +
                            '</div>' +
                            '<div class="criteria-explanation">' + escapeHtml(aiExplanation) + '</div>' +
                        '</div>';
                    }).join('')}
                </div>

                <!-- Sammanfattande bedömning -->
                <div class="card">
                    <h2>Sammanfattande bedömning</h2>
                    ${(data.summary_assessment || 'Ingen sammanfattning tillgänglig.').split(String.fromCharCode(10)).filter(line => line.trim()).map(line =>
                        '<div class="assessment-item"><div class="assessment-dot"></div><p>' + escapeHtml(line.trim()) + '</p></div>'
                    ).join('')}
                </div>

                <!-- Rekommendationer -->
                <div class="card card--recs">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:20px;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF6A3D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                        <h2 style="margin-bottom:0;">Rekommendationer</h2>
                    </div>
                    <ol class="rec-list">
                        ${(data.recommendations || []).map((r, i) =>
                            '<li class="rec-item"><span class="rec-num">' + (i + 1) + '</span><p>' + escapeHtml(r) + '</p></li>'
                        ).join('')}
                    </ol>
                </div>

                <!-- CTA -->
                <div class="cta-section">
                    <h2>Redo att fixa luckorna?</h2>
                    <p>Vi har identifierat ${data.issues_count} problem som hindrar er från att maximera konverteringen. Boka en kostnadsfri genomgång för att se exakt hur ni kan åtgärda dem.</p>
                    <div class="cta-buttons">
                        <a href="https://calendly.com/stefan-245/30min" target="_blank" class="btn-primary">
                            Boka genomgång
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                        </a>
                        <a href="/api/report/${data.report_id}/pdf?token=${new URLSearchParams(window.location.search).get('token')}" class="btn-secondary">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Ladda ner som PDF
                        </a>
                    </div>
                </div>

                <!-- Footer -->
                <footer class="report-footer">
                    <a href="https://leadsmaskinen.se" target="_blank">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect width="24" height="24" rx="6" fill="#FF6A3D"/><path d="M7 12L10.5 15.5L17 8.5" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        Genererad av Leadsmaskinen
                    </a>
                </footer>
                </div>
            `;

            /* Fix score-wrap relative positioning for overlapping SVGs */
            const wrap = container.querySelector('.score-wrap');
            if (wrap) wrap.style.position = 'relative';
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
