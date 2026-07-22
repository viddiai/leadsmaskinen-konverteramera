"""
API routes for the Conversion Analyzer.
"""
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

logger = logging.getLogger(__name__)
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db, SessionLocal
from app.core.config import settings
from app.models.models import Lead, Report, AnalysisData
from app.schemas.schemas import (
    AnalyzeRequest,
    ShortSummaryResponse,
    FullReportResponse,
    LeadCreate,
    LeadResponse,
    LeadListItem,
    ReportListItem,
    DashboardStats,
    AnalysisCriterion,
)
from app.services.scraper import WebScraper
from app.services.analyzer import ConversionAnalyzer
from app.services.ai_report_generator import generate_enhanced_report
from app.services.industry_detector import IndustryDetector
from app.services.pdf_generator import generate_report_pdf
from app.core.auth import verify_admin


def generate_ai_sync(report_id: int, scraped_data: dict, analysis: dict):
    """
    Generate AI-enhanced sections synchronously in a background thread.
    This runs AFTER the HTTP response is sent to the client.
    """
    import asyncio
    print(f"🚀 Starting background AI generation for report {report_id}")

    async def _generate():
        try:
            # Generate AI sections
            print(f"📝 Calling Claude API for report {report_id}...")
            enhanced_sections = await generate_enhanced_report(scraped_data, analysis)
            print(f"📝 Claude API returned for report {report_id}")
            print(f"📋 AI sections received: {list(enhanced_sections.keys())}")
            logical_verdict_preview = (enhanced_sections.get("logical_verdict", "") or "")[:100]
            print(f"📋 logical_verdict preview: '{logical_verdict_preview}...'")

            # Update report in database
            db = SessionLocal()
            try:
                report = db.query(Report).filter(Report.id == report_id).first()
                if report and report.full_report:
                    # Merge AI sections into existing report
                    full_report = dict(report.full_report)  # Make mutable copy

                    ai_success = bool(enhanced_sections.get("ai_success"))

                    # Comprehensive AI sections (new format).
                    # Skriv bara över befintlig text om AI faktiskt levererade innehåll —
                    # annars behålls analyzerns ursprungliga texter.
                    mergeable_fields = [
                        "short_description",
                        "lead_magnets_analysis",
                        "forms_analysis",
                        "cta_analysis",
                        "logical_verdict",
                        "summary_assessment",
                        "criteria_explanations",
                    ]
                    for field in mergeable_fields:
                        value = enhanced_sections.get(field)
                        if value:
                            full_report[field] = value

                    # Apply AI-adjusted scores (quality-based, not just structural)
                    adjusted_scores = enhanced_sections.get("adjusted_scores", {})
                    if adjusted_scores and full_report.get("criteria_analysis"):
                        criteria_analysis = list(full_report["criteria_analysis"])
                        score_map = {
                            "value_proposition": adjusted_scores.get("value_proposition"),
                            "call_to_action": adjusted_scores.get("call_to_action"),
                            "social_proof": adjusted_scores.get("social_proof"),
                            "lead_magnets": adjusted_scores.get("lead_magnets"),
                            "form_design": adjusted_scores.get("form_design"),
                            "guiding_content": adjusted_scores.get("guiding_content"),
                            "offer_structure": adjusted_scores.get("offer_structure"),
                        }
                        for i, criterion in enumerate(criteria_analysis):
                            key = criterion.get("criterion")
                            if key in score_map and score_map[key] is not None:
                                try:
                                    new_score = int(score_map[key])
                                    new_score = max(1, min(5, new_score))  # Clamp 1-5
                                    criteria_analysis[i] = dict(criterion)
                                    criteria_analysis[i]["score"] = new_score
                                except (ValueError, TypeError):
                                    pass  # Keep original score if AI returned invalid
                        full_report["criteria_analysis"] = criteria_analysis
                        # Recalculate overall score using WEIGHTED formula
                        # Viktning: value_proposition=2.0, call_to_action=1.5, lead_magnets=1.5, resten=1.0
                        weights = {
                            "value_proposition": 2.0,
                            "call_to_action": 1.5,
                            "lead_magnets": 1.5,
                            "social_proof": 1.0,
                            "form_design": 1.0,
                            "guiding_content": 1.0,
                            "offer_structure": 1.0,
                        }
                        # Nämnaren beräknas från de kriterier som faktiskt finns i analysen,
                        # så att en saknad/extra rad inte skevar totalpoängen.
                        total_weight = sum(
                            weights.get(c["criterion"], 1.0)
                            for c in criteria_analysis
                        )
                        weighted_sum = sum(
                            c["score"] * weights.get(c["criterion"], 1.0)
                            for c in criteria_analysis
                        )
                        new_overall = round(weighted_sum / total_weight, 1) if total_weight else 0.0
                        full_report["overall_score"] = new_overall
                        report.overall_score = new_overall  # Update Report model too
                        print(f"📊 Applied AI-adjusted scores for report {report_id}: overall {new_overall}/5 (weighted)")

                        # Synka AnalysisData-raderna så adminstatistiken visar samma
                        # poäng som kundens rapport
                        criteria_by_key = {c["criterion"]: c for c in criteria_analysis}
                        explanations = full_report.get("criteria_explanations") or {}
                        for row in db.query(AnalysisData).filter(
                            AnalysisData.report_id == report_id
                        ).all():
                            updated = criteria_by_key.get(row.criterion)
                            if updated:
                                row.score = updated["score"]
                                if explanations.get(row.criterion):
                                    row.explanation = explanations[row.criterion]

                    # Legacy fields (backward compatibility)
                    legacy_fields = [
                        "final_hook",
                        "detailed_lead_magnets",
                        "detailed_forms",
                        "detailed_social_proof",
                        "detailed_mailto",
                        "detailed_ungated_pdfs",
                    ]
                    for field in legacy_fields:
                        value = enhanced_sections.get(field)
                        if value:
                            full_report[field] = value

                    # ai_generated = äkta AI-analys; ai_completed = bakgrundsjobbet klart
                    # (rapportsidan slutar polla på ai_completed)
                    full_report["ai_generated"] = ai_success
                    full_report["ai_completed"] = True

                    report.full_report = full_report
                    db.commit()
                    status_label = "AI" if ai_success else "fallback"
                    print(f"✅ Background generation complete for report {report_id} ({status_label})")
            finally:
                db.close()
        except Exception as e:
            print(f"❌ Background AI generation failed for report {report_id}: {e}")
            # Markera jobbet som avslutat så rapportsidan inte pollar i onödan
            try:
                db = SessionLocal()
                try:
                    report = db.query(Report).filter(Report.id == report_id).first()
                    if report and report.full_report:
                        full_report = dict(report.full_report)
                        full_report["ai_completed"] = True
                        full_report["ai_generated"] = False
                        report.full_report = full_report
                        db.commit()
                finally:
                    db.close()
            except Exception as inner:
                print(f"❌ Could not mark report {report_id} as completed: {inner}")

    # Run in a new event loop (since BackgroundTasks runs in a thread)
    asyncio.run(_generate())

router = APIRouter()


# ============== Analysis Endpoints ==============

@router.post("/analyze", response_model=ShortSummaryResponse)
async def analyze_url(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Analyze a URL and return a short summary (public teaser) IMMEDIATELY.
    AI-enhanced text is generated in background and will be ready for full report.

    This provides sub-second response times while AI generates in parallel.
    """
    url = str(request.url)
    total_start = time.time()

    try:
        # Scrape the page
        scraper = WebScraper()
        scraped_data = await scraper.scrape_and_analyze(url)

        # Detect industry
        detector = IndustryDetector(scraped_data)
        industry, industry_confidence, industry_label = detector.detect()

        # Analyze the scraped data (scoring) - FAST, no AI
        analyzer = ConversionAnalyzer(scraped_data)
        analysis = analyzer.generate_analysis()

        # Generate quick teaser from analysis (no AI needed)
        quick_description = _generate_quick_description(
            scraped_data.get("company_info", {}),
            analysis,
            industry_label
        )

        # Build initial report data (will be enhanced with AI in background)
        full_report = {
            "scraped_data": scraped_data,
            "criteria_analysis": analysis["criteria_analysis"],
            "summary_assessment": analyzer.generate_summary_assessment(),
            "recommendations": analyzer.generate_recommendations(),
            # Leaking funnels - dedicated section for critical lead leaks
            "leaking_funnels": analysis.get("leaking_funnels", []),
            # Placeholder for AI sections (will be filled by background task)
            "short_description": quick_description,
            "logical_verdict": "",
            "final_hook": "",
            "detailed_lead_magnets": "",
            "detailed_forms": "",
            "detailed_social_proof": "",
            "detailed_mailto": "",
            "detailed_ungated_pdfs": "",
            # Industry detection
            "detected_industry": industry,
            "industry_label": industry_label,
            "industry_confidence": industry_confidence,
            "ai_generated": False,  # Will be set to True when AI completes
            "ai_completed": False,  # True när bakgrundsjobbet är klart (även vid fallback)
        }

        # Create report in database
        report = Report(
            url=url,
            company_name_detected=scraped_data.get("company_info", {}).get("company_name"),
            company_description=scraped_data.get("company_info", {}).get("description"),
            short_summary="; ".join(analysis["logical_errors"][:3]),
            full_report=full_report,
            overall_score=analysis["overall_score"],
            issues_found=analysis["issues_found"],
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Store individual analysis data
        for criterion in analysis["criteria_analysis"]:
            analysis_item = AnalysisData(
                report_id=report.id,
                criterion=criterion["criterion"],
                score=criterion["score"],
                explanation=criterion["explanation"],
            )
            db.add(analysis_item)
        db.commit()

        # Start AI generation in TRUE background (runs AFTER response is sent)
        background_tasks.add_task(generate_ai_sync, report.id, scraped_data, analysis)

        # Generate teaser text
        teaser = f"Vi har identifierat {analysis['issues_found']} specifika fel som hindrar er från att dominera marknaden"

        print(f"⏱️ TOTAL analyze endpoint took {time.time() - total_start:.2f}s (AI generating in background)")

        return ShortSummaryResponse(
            report_id=report.id,
            url=url,
            company_name=report.company_name_detected,
            company_description=report.company_description,
            overall_score=analysis["overall_score"],
            issues_count=analysis["issues_found"],
            logical_errors=analysis["logical_errors"],
            teaser_text=teaser,
            # Quick description (non-AI)
            short_description=quick_description,
            detected_industry=industry,
            industry_label=industry_label,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Kunde inte analysera URL: {str(e)}")


def _generate_quick_description(company_info: dict, analysis: dict, industry_label: str) -> str:
    """
    Generate a quick company description without AI.
    Used for immediate response while AI generates in background.
    """
    company_name = company_info.get("company_name", "Webbplatsen")
    issues = analysis.get("logical_errors", [])
    score = analysis.get("overall_score", 0)

    if score <= 2:
        severity = "allvarliga brister"
    elif score <= 3:
        severity = "betydande förbättringsmöjligheter"
    else:
        severity = "vissa förbättringsområden"

    main_issue = issues[0] if issues else "saknar tydlig konverteringsstrategi"

    return f"{company_name} ({industry_label}) har {severity} i sin lead generation. {main_issue}."


@router.post("/lead", response_model=LeadResponse)
async def create_lead(lead_data: LeadCreate, db: Session = Depends(get_db)):
    """
    Capture lead information and grant access to full report.
    """
    # Check if report exists
    report = db.query(Report).filter(Report.id == lead_data.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Rapport hittades inte")

    # Check if email already exists
    existing_lead = db.query(Lead).filter(Lead.email == lead_data.email).first()

    if existing_lead:
        # Update existing lead with new analyzed URL if different
        if existing_lead.analyzed_url != report.url:
            existing_lead.analyzed_url = report.url

        # Link report to existing lead
        report.lead_id = existing_lead.id

        # Generate access token
        access_token = secrets.token_urlsafe(32)
        report.access_token = access_token
        db.commit()

        return LeadResponse(
            success=True,
            message="Välkommen tillbaka! Din fullständiga rapport är redo.",
            lead_id=existing_lead.id,
            access_token=access_token,
        )

    # Create new lead
    lead = Lead(
        name=lead_data.name,
        email=lead_data.email,
        company_name=lead_data.company_name,
        analyzed_url=report.url,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Link report to lead and generate access token
    report.lead_id = lead.id
    access_token = secrets.token_urlsafe(32)
    report.access_token = access_token
    db.commit()

    return LeadResponse(
        success=True,
        message="Tack! Din fullständiga rapport är redo.",
        lead_id=lead.id,
        access_token=access_token,
    )


@router.get("/report/{report_id}")
async def get_full_report(
    report_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get full report. Requires valid access token.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Rapport hittades inte")

    # Verify access token
    if not token or report.access_token != token:
        raise HTTPException(
            status_code=403,
            detail="Åtkomst nekad. Vänligen fyll i formuläret för att få tillgång till rapporten."
        )

    # Check token expiry (72 hours from creation)
    expiry = report.created_at + timedelta(hours=settings.REPORT_ACCESS_TOKEN_EXPIRE_HOURS)
    if datetime.utcnow() > expiry:
        raise HTTPException(status_code=403, detail="Länken har upphört. Analysera sidan igen.")

    # Build full report response
    full_data = report.full_report or {}
    scraped = full_data.get("scraped_data", {})

    # Helper to convert lists to strings (AI sometimes returns lists instead of strings)
    def ensure_string(value):
        if isinstance(value, list):
            return "\n\n".join(str(item) for item in value)
        return value if value else None

    # Safely build criteria_analysis with validation
    criteria_list = []
    for c in full_data.get("criteria_analysis", []):
        try:
            criteria_list.append(AnalysisCriterion(
                criterion=c.get("criterion", "unknown"),
                criterion_label=c.get("criterion_label", c.get("criterion", "Unknown")),
                score=int(c.get("score", 1)),
                explanation=c.get("explanation", "")
            ))
        except Exception as e:
            logger.error(f"Failed to parse criterion {c}: {e}")
            # Add a fallback criterion
            criteria_list.append(AnalysisCriterion(
                criterion=c.get("criterion", "unknown"),
                criterion_label=c.get("criterion_label", "Unknown"),
                score=1,
                explanation="Data kunde inte parsas"
            ))

    try:
        return FullReportResponse(
            report_id=report.id,
            url=report.url,
            company_name=report.company_name_detected,
            company_description=report.company_description,
            overall_score=float(report.overall_score) if report.overall_score else 0.0,
            issues_count=report.issues_found or 0,
            # Industry detection
            detected_industry=full_data.get("detected_industry"),
            industry_label=full_data.get("industry_label"),
            # AI-generated text sections (comprehensive) - ensure strings
            short_description=ensure_string(full_data.get("short_description")),
            logical_verdict=ensure_string(full_data.get("logical_verdict")),
            final_hook=ensure_string(full_data.get("final_hook")),
            # New comprehensive analysis sections
            lead_magnets_analysis=ensure_string(full_data.get("lead_magnets_analysis")),
            forms_analysis=ensure_string(full_data.get("forms_analysis")),
            cta_analysis=ensure_string(full_data.get("cta_analysis")),
            # Legacy detailed category analysis (backward compatibility)
            detailed_lead_magnets=ensure_string(full_data.get("detailed_lead_magnets")),
            detailed_forms=ensure_string(full_data.get("detailed_forms")),
            detailed_social_proof=ensure_string(full_data.get("detailed_social_proof")),
            detailed_mailto=ensure_string(full_data.get("detailed_mailto")),
            detailed_ungated_pdfs=ensure_string(full_data.get("detailed_ungated_pdfs")),
            # AI-generated criteria explanations
            criteria_explanations=full_data.get("criteria_explanations"),
            # Raw detected elements
            lead_magnets=scraped.get("lead_magnets", []),
            forms=scraped.get("forms", []),
            cta_buttons=scraped.get("cta_buttons", []),
            social_proof=scraped.get("social_proof", []),
            mailto_links=scraped.get("mailto_links", []),
            ungated_pdfs=scraped.get("ungated_pdfs", []),
            # Analysis scores
            criteria_analysis=criteria_list,
            summary_assessment=ensure_string(full_data.get("summary_assessment")) or "",
            recommendations=full_data.get("recommendations", []),
            ai_generated=full_data.get("ai_generated", False),
            ai_completed=full_data.get("ai_completed", full_data.get("ai_generated", False)),
            created_at=report.created_at,
        )
    except Exception as e:
        logger.error(f"Failed to build FullReportResponse for report {report_id}: {e}")
        logger.error(f"full_data keys: {list(full_data.keys())}")
        logger.error(f"scraped keys: {list(scraped.keys())}")
        raise HTTPException(status_code=500, detail=f"Kunde inte bygga rapport: {str(e)}")


@router.get("/report/{report_id}/pdf")
async def download_report_pdf(
    report_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Download report as PDF. Requires valid access token.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Rapport hittades inte")

    # Verify access token
    if not token or report.access_token != token:
        raise HTTPException(
            status_code=403,
            detail="Åtkomst nekad. Vänligen fyll i formuläret för att få tillgång till rapporten."
        )

    # Check token expiry
    expiry = report.created_at + timedelta(hours=settings.REPORT_ACCESS_TOKEN_EXPIRE_HOURS)
    if datetime.utcnow() > expiry:
        raise HTTPException(status_code=403, detail="Länken har upphört. Analysera sidan igen.")

    # Build report data for PDF
    full_data = report.full_report or {}
    scraped = full_data.get("scraped_data", {})

    pdf_data = {
        "report_id": report.id,
        "url": report.url,
        "company_name": report.company_name_detected,
        "company_description": report.company_description,
        "overall_score": float(report.overall_score) if report.overall_score else 0.0,
        "issues_count": report.issues_found,
        "detected_industry": full_data.get("detected_industry"),
        "industry_label": full_data.get("industry_label"),
        "short_description": full_data.get("short_description"),
        "logical_verdict": full_data.get("logical_verdict"),
        "lead_magnets_analysis": full_data.get("lead_magnets_analysis"),
        "forms_analysis": full_data.get("forms_analysis"),
        "cta_analysis": full_data.get("cta_analysis"),
        "detailed_lead_magnets": full_data.get("detailed_lead_magnets"),
        "detailed_forms": full_data.get("detailed_forms"),
        "criteria_analysis": full_data.get("criteria_analysis", []),
        "criteria_explanations": full_data.get("criteria_explanations", {}),
        "summary_assessment": full_data.get("summary_assessment", ""),
        "recommendations": full_data.get("recommendations", []),
        "scraped_data": scraped,
        "lead_magnets": scraped.get("lead_magnets", []),
        "forms": scraped.get("forms", []),
        "cta_buttons": scraped.get("cta_buttons", []),
        "mailto_links": scraped.get("mailto_links", []),
        "ungated_pdfs": scraped.get("ungated_pdfs", []),
        "created_at": report.created_at.isoformat(),
    }

    try:
        pdf_bytes = generate_report_pdf(pdf_data)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail="Kunde inte generera PDF")

    # Create filename
    company_slug = (report.company_name_detected or "rapport").replace(" ", "-").lower()[:30]
    filename = f"konverteringsanalys-{company_slug}-{report.id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ============== Widget Endpoint ==============

WIDGET_JS_TEMPLATE = '''
(function() {
  const WIDGET_API_URL = '%API_URL%';

  // Create widget container
  function createWidget(config) {
    config = config || {};
    const theme = config.theme || 'light';
    const primaryColor = config.primaryColor || '#2563eb';
    const buttonText = config.buttonText || 'Analysera';
    const placeholder = config.placeholder || 'Ange URL att analysera...';

    const container = document.getElementById('conversion-analyzer-widget');
    if (!container) {
      console.error('Widget container not found');
      return;
    }

    const isDark = theme === 'dark';
    const bgColor = isDark ? '#1f2937' : '#ffffff';
    const textColor = isDark ? '#f9fafb' : '#111827';
    const borderColor = isDark ? '#374151' : '#e5e7eb';

    container.innerHTML = `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                  max-width: 500px; padding: 24px; background: ${bgColor};
                  border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
        <h3 style="margin: 0 0 16px; color: ${textColor}; font-size: 18px; font-weight: 600;">
          Analysera din webbsidas konverteringsförmåga
        </h3>
        <div id="caw-input-section">
          <div style="display: flex; gap: 8px;">
            <input type="url" id="caw-url-input"
                   placeholder="${placeholder}"
                   style="flex: 1; padding: 12px 16px; border: 1px solid ${borderColor};
                          border-radius: 8px; font-size: 14px; background: ${bgColor};
                          color: ${textColor};">
            <button id="caw-analyze-btn"
                    style="padding: 12px 24px; background: ${primaryColor}; color: white;
                           border: none; border-radius: 8px; font-size: 14px; font-weight: 500;
                           cursor: pointer; transition: opacity 0.2s;">
              ${buttonText}
            </button>
          </div>
          <p id="caw-error" style="color: #ef4444; margin: 8px 0 0; font-size: 13px; display: none;"></p>
        </div>
        <div id="caw-loading" style="display: none; text-align: center; padding: 40px 0;">
          <div style="width: 40px; height: 40px; border: 3px solid ${borderColor};
                      border-top-color: ${primaryColor}; border-radius: 50%;
                      animation: caw-spin 1s linear infinite; margin: 0 auto;"></div>
          <p style="margin: 16px 0 0; color: ${textColor};">Analyserar webbsidan...</p>
        </div>
        <div id="caw-result" style="display: none;"></div>
        <div id="caw-lead-form" style="display: none;"></div>
      </div>
      <style>
        @keyframes caw-spin { to { transform: rotate(360deg); } }
        #caw-analyze-btn:hover { opacity: 0.9; }
        #caw-url-input:focus { outline: 2px solid ${primaryColor}; outline-offset: -1px; }
      </style>
    `;

    // Attach event listeners
    const btn = document.getElementById('caw-analyze-btn');
    const input = document.getElementById('caw-url-input');

    btn.addEventListener('click', () => analyzeUrl(config));
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') analyzeUrl(config);
    });
  }

  async function analyzeUrl(config) {
    const input = document.getElementById('caw-url-input');
    const error = document.getElementById('caw-error');
    const loading = document.getElementById('caw-loading');
    const inputSection = document.getElementById('caw-input-section');
    const result = document.getElementById('caw-result');

    const url = input.value.trim();
    if (!url) {
      error.textContent = 'Ange en URL';
      error.style.display = 'block';
      return;
    }

    // Basic URL validation
    try {
      new URL(url.startsWith('http') ? url : 'https://' + url);
    } catch {
      error.textContent = 'Ogiltig URL';
      error.style.display = 'block';
      return;
    }

    error.style.display = 'none';
    inputSection.style.display = 'none';
    loading.style.display = 'block';

    try {
      const response = await fetch(WIDGET_API_URL + '/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.startsWith('http') ? url : 'https://' + url })
      });

      if (!response.ok) throw new Error('Analys misslyckades');

      const data = await response.json();
      loading.style.display = 'none';
      showResult(data, config);
    } catch (err) {
      loading.style.display = 'none';
      inputSection.style.display = 'block';
      error.textContent = err.message || 'Något gick fel';
      error.style.display = 'block';
    }
  }

  function showResult(data, config) {
    const result = document.getElementById('caw-result');
    const isDark = (config.theme || 'light') === 'dark';
    const textColor = isDark ? '#ffffff' : '#111827';
    const mutedColor = isDark ? 'rgba(255,255,255,0.5)' : '#6b7280';
    const primaryColor = config.primaryColor || '#10b981';
    const borderColor = isDark ? 'rgba(255,255,255,0.1)' : '#e5e7eb';
    const cardBg = isDark ? 'rgba(255,255,255,0.02)' : '#f9fafb';

    const score = Math.round(data.overall_score);
    const starsHtml = Array(5).fill(0).map((_, i) =>
      i < score
        ? '<span style="color: ' + primaryColor + ';">★</span>'
        : '<span style="color: rgba(255,255,255,0.2);">★</span>'
    ).join('');

    result.style.display = 'block';
    result.innerHTML = `
      <div style="color: ${textColor};">
        <!-- Header med företagsinfo och betyg -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
          <div style="flex: 1;">
            <h4 style="margin: 0 0 6px; font-size: 20px; font-weight: 500; letter-spacing: -0.02em;">${data.company_name || 'Analysresultat'}</h4>
            ${data.industry_label ? '<span style="font-size: 10px; color: ' + primaryColor + '; text-transform: uppercase; letter-spacing: 1px; font-weight: 500;">' + data.industry_label + '</span>' : ''}
          </div>
          <div style="text-align: right;">
            <div style="font-size: 18px; letter-spacing: 2px;">${starsHtml}</div>
            <span style="font-size: 13px; font-weight: 500; color: ${mutedColor};">${data.overall_score}/5</span>
          </div>
        </div>

        <!-- Kort beskrivning -->
        <p style="margin: 0 0 24px; color: ${mutedColor}; font-size: 14px; line-height: 1.6; font-weight: 300;">
          ${(data.company_description || '').substring(0, 200)}${(data.company_description || '').length > 200 ? '...' : ''}
        </p>

        <!-- Identifierade problem - minimalistisk stil -->
        <div style="border: 1px solid ${borderColor}; border-radius: 16px; padding: 20px; margin-bottom: 20px; background: ${cardBg};">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
            <div style="width: 32px; height: 32px; background: rgba(239, 68, 68, 0.1); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"></path>
                <path d="M12 9v4"></path>
                <path d="M12 17h.01"></path>
              </svg>
            </div>
            <span style="font-size: 14px; font-weight: 500; color: ${textColor};">Identifierade problem</span>
            <span style="margin-left: auto; font-size: 12px; color: ${mutedColor};">${data.issues_count || data.logical_errors.length} st</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 12px;">
            ${data.logical_errors.map(e => `
              <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="width: 6px; height: 6px; background: #ef4444; border-radius: 50%; margin-top: 6px; flex-shrink: 0;"></div>
                <span style="font-size: 13px; color: rgba(255,255,255,0.7); line-height: 1.5; font-weight: 300;">${e}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Sammanfattning -->
        <div style="border: 1px solid ${borderColor}; border-radius: 16px; padding: 20px; margin-bottom: 20px; background: ${cardBg};">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <div style="width: 32px; height: 32px; background: rgba(255,255,255,0.05); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${mutedColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
            </div>
            <span style="font-size: 14px; font-weight: 500; color: ${textColor};">Sammanfattning</span>
          </div>
          <p style="margin: 0; font-size: 13px; color: rgba(255,255,255,0.6); line-height: 1.6; font-weight: 300;">
            ${data.short_description || data.teaser_text}
          </p>
        </div>

        <!-- Vad rapporten innehåller -->
        <div style="border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 16px; padding: 20px; margin-bottom: 24px; background: rgba(16, 185, 129, 0.05);">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px;">
            <div style="width: 32px; height: 32px; background: rgba(16, 185, 129, 0.1); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${primaryColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"></line>
                <line x1="12" y1="20" x2="12" y2="4"></line>
                <line x1="6" y1="20" x2="6" y2="14"></line>
              </svg>
            </div>
            <span style="font-size: 14px; font-weight: 500; color: ${textColor};">Den fullständiga rapporten</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px;">
            ${['Detaljerad analys av leadmagneter och formulär', 'Granskning av CTA-knappar och konverteringselement', 'Betyg på varje konverteringskriterium', '5 konkreta rekommendationer för ökad konvertering'].map(item => `
              <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 18px; height: 18px; background: rgba(16, 185, 129, 0.1); border-radius: 6px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="${primaryColor}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </div>
                <span style="font-size: 13px; color: rgba(255,255,255,0.7); font-weight: 300;">${item}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- CTA knapp -->
        <button id="caw-get-report-btn"
                style="width: 100%; padding: 16px 24px; background: ${primaryColor}; color: white;
                       border: none; border-radius: 50px; font-size: 15px; font-weight: 500;
                       cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px;">
          <span>Få den fullständiga rapporten</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14"></path>
            <path d="m12 5 7 7-7 7"></path>
          </svg>
        </button>
        <p style="text-align: center; margin: 16px 0 0; font-size: 11px; color: ${mutedColor}; font-weight: 300;">
          Gratis • Ingen spam • Levereras direkt
        </p>
      </div>
    `;

    document.getElementById('caw-get-report-btn').addEventListener('click', () => {
      showLeadForm(data.report_id, config);
    });

    window.CAW_REPORT_ID = data.report_id;
  }

  function showLeadForm(reportId, config) {
    const result = document.getElementById('caw-result');
    const form = document.getElementById('caw-lead-form');
    const isDark = (config.theme || 'light') === 'dark';
    const textColor = isDark ? '#f9fafb' : '#111827';
    const borderColor = isDark ? '#374151' : '#e5e7eb';
    const bgColor = isDark ? '#1f2937' : '#ffffff';
    const primaryColor = config.primaryColor || '#2563eb';

    result.style.display = 'none';
    form.style.display = 'block';

    form.innerHTML = `
      <div style="color: ${textColor};">
        <h4 style="margin: 0 0 16px; font-size: 16px;">Fyll i för att få rapporten</h4>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <input type="text" id="caw-name" placeholder="Ditt namn *" required
                 style="padding: 12px 16px; border: 1px solid ${borderColor}; border-radius: 8px;
                        font-size: 14px; background: ${bgColor}; color: ${textColor};">
          <input type="email" id="caw-email" placeholder="Din e-post *" required
                 style="padding: 12px 16px; border: 1px solid ${borderColor}; border-radius: 8px;
                        font-size: 14px; background: ${bgColor}; color: ${textColor};">
          <input type="text" id="caw-company" placeholder="Företagsnamn (valfritt)"
                 style="padding: 12px 16px; border: 1px solid ${borderColor}; border-radius: 8px;
                        font-size: 14px; background: ${bgColor}; color: ${textColor};">
          <button id="caw-submit-lead"
                  style="padding: 14px; background: ${primaryColor}; color: white; border: none;
                         border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer;">
            Få den fullständiga rapporten
          </button>
          <p id="caw-form-error" style="color: #ef4444; margin: 0; font-size: 13px; display: none;"></p>
        </div>
      </div>
    `;

    document.getElementById('caw-submit-lead').addEventListener('click', () => submitLead(reportId, config));
  }

  async function submitLead(reportId, config) {
    const name = document.getElementById('caw-name').value.trim();
    const email = document.getElementById('caw-email').value.trim();
    const company = document.getElementById('caw-company').value.trim();
    const error = document.getElementById('caw-form-error');

    if (!name || !email) {
      error.textContent = 'Namn och e-post krävs';
      error.style.display = 'block';
      return;
    }

    if (!email.includes('@')) {
      error.textContent = 'Ogiltig e-postadress';
      error.style.display = 'block';
      return;
    }

    error.style.display = 'none';

    try {
      const response = await fetch(WIDGET_API_URL + '/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          email: email,
          company_name: company || null,
          report_id: reportId
        })
      });

      if (!response.ok) throw new Error('Något gick fel');

      const data = await response.json();

      // Redirect to full report
      window.location.href = WIDGET_API_URL.replace('/api', '') +
        '/report/' + reportId + '?token=' + data.access_token;
    } catch (err) {
      error.textContent = err.message || 'Något gick fel';
      error.style.display = 'block';
    }
  }

  // Initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => createWidget(window.CAWidgetConfig));
  } else {
    createWidget(window.CAWidgetConfig);
  }
})();
'''


@router.get("/widget.js")
async def get_widget_js():
    """
    Return the embeddable widget JavaScript.
    """
    # Replace API URL placeholder - use PUBLIC_URL if set, otherwise fallback to HOST:PORT
    if settings.PUBLIC_URL:
        api_url = f"{settings.PUBLIC_URL.rstrip('/')}/api"
    else:
        api_url = f"http://{settings.HOST}:{settings.PORT}/api"
    js_content = WIDGET_JS_TEMPLATE.replace('%API_URL%', api_url)

    return Response(
        content=js_content,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


# ============== Admin Endpoints ==============

@router.get("/admin/leads", response_model=list[LeadListItem])
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """
    List all captured leads. Requires admin authentication.
    """
    leads = db.query(Lead).order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return [LeadListItem.model_validate(lead) for lead in leads]


@router.get("/admin/reports", response_model=list[ReportListItem])
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """
    List all reports. Requires admin authentication.
    """
    reports = db.query(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for report in reports:
        lead_email = None
        if report.lead:
            lead_email = report.lead.email

        result.append(ReportListItem(
            id=report.id,
            url=report.url,
            company_name_detected=report.company_name_detected,
            overall_score=float(report.overall_score) if report.overall_score else None,
            issues_found=report.issues_found,
            lead_email=lead_email,
            access_token=report.access_token,  # For PDF download
            created_at=report.created_at,
        ))

    return result


@router.get("/admin/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin)
):
    """
    Get dashboard statistics. Requires admin authentication.
    """
    today = datetime.utcnow().date()

    total_leads = db.query(func.count(Lead.id)).scalar()
    total_reports = db.query(func.count(Report.id)).scalar()

    leads_today = db.query(func.count(Lead.id)).filter(
        func.date(Lead.created_at) == today
    ).scalar()

    reports_today = db.query(func.count(Report.id)).filter(
        func.date(Report.created_at) == today
    ).scalar()

    avg_score = db.query(func.avg(Report.overall_score)).scalar()

    # Get top issues (most common low-scoring criteria)
    low_scores = db.query(
        AnalysisData.criterion,
        func.count(AnalysisData.id).label("count")
    ).filter(
        AnalysisData.score <= 2
    ).group_by(
        AnalysisData.criterion
    ).order_by(
        func.count(AnalysisData.id).desc()
    ).limit(5).all()

    top_issues = [{"criterion": r[0], "count": r[1]} for r in low_scores]

    return DashboardStats(
        total_leads=total_leads or 0,
        total_reports=total_reports or 0,
        reports_today=reports_today or 0,
        leads_today=leads_today or 0,
        average_score=round(float(avg_score), 1) if avg_score else None,
        top_issues=top_issues,
    )
