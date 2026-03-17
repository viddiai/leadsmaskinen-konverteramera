"""
PDF Report Generator for Conversion Analyzer.
Generates professional PDF reports from analysis data.
"""
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, List
from xhtml2pdf import pisa


def generate_report_pdf(report_data: Dict[str, Any]) -> bytes:
    """
    Generate a PDF report from the analysis data.

    Args:
        report_data: Full report data including all analysis sections

    Returns:
        PDF file as bytes
    """
    html = _build_report_html(report_data)

    # Convert HTML to PDF
    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result, encoding='utf-8')

    if pisa_status.err:
        raise ValueError(f"PDF generation failed: {pisa_status.err}")

    return result.getvalue()


def _build_report_html(data: Dict[str, Any]) -> str:
    """Build HTML content for the PDF report."""

    company_name = data.get("company_name") or "Webbplatsen"
    url = data.get("url", "")
    overall_score = data.get("overall_score", 0)
    industry_label = data.get("industry_label", "")
    created_at = data.get("created_at", datetime.now().isoformat())

    # Format date
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            created_at = datetime.now()
    formatted_date = created_at.strftime("%Y-%m-%d")

    # Get analysis sections
    short_description = data.get("short_description") or data.get("company_description") or ""
    lead_magnets_analysis = data.get("lead_magnets_analysis") or data.get("detailed_lead_magnets") or ""
    forms_analysis = data.get("forms_analysis") or data.get("detailed_forms") or ""
    cta_analysis = data.get("cta_analysis") or ""
    logical_verdict = data.get("logical_verdict") or ""
    summary_assessment = data.get("summary_assessment") or ""
    recommendations = data.get("recommendations", [])

    # Get raw data counts
    scraped = data.get("scraped_data", {})
    lead_magnets = scraped.get("lead_magnets", []) if scraped else data.get("lead_magnets", [])
    forms = scraped.get("forms", []) if scraped else data.get("forms", [])
    cta_buttons = scraped.get("cta_buttons", []) if scraped else data.get("cta_buttons", [])
    mailto_links = scraped.get("mailto_links", []) if scraped else data.get("mailto_links", [])
    ungated_pdfs = scraped.get("ungated_pdfs", []) if scraped else data.get("ungated_pdfs", [])

    # Get criteria analysis
    criteria_analysis = data.get("criteria_analysis", [])
    criteria_explanations = data.get("criteria_explanations", {})

    # Build criteria rows
    criteria_rows = ""
    for criterion in criteria_analysis:
        name = criterion.get("criterion_label") or criterion.get("criterion", "")
        score = criterion.get("score", 0)
        explanation = criterion.get("explanation", "")

        # Get AI explanation if available
        criterion_key = criterion.get("criterion", "")
        ai_explanation = criteria_explanations.get(criterion_key, "")
        display_explanation = ai_explanation or explanation

        # Score color
        if score >= 4:
            score_color = "#22c55e"  # green
        elif score >= 3:
            score_color = "#eab308"  # yellow
        else:
            score_color = "#ef4444"  # red

        criteria_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{name}</td>
            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: center;">
                <span style="color: {score_color}; font-weight: bold;">{score}/5</span>
            </td>
            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; font-size: 12px;">{display_explanation}</td>
        </tr>
        """

    # Build recommendations list
    recommendations_html = ""
    for i, rec in enumerate(recommendations[:5], 1):
        recommendations_html += f'<li style="margin-bottom: 8px;">{rec}</li>'

    # Build CTA list
    ctas_html = ""
    for cta in cta_buttons[:8]:
        text = cta.get("text", "")
        if text:
            ctas_html += f'<span style="display: inline-block; background: #f3f4f6; padding: 4px 8px; margin: 2px; border-radius: 4px; font-size: 11px;">{text}</span>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: Helvetica, Arial, sans-serif;
                font-size: 12px;
                line-height: 1.5;
                color: #1f2937;
            }}
            h1 {{
                font-size: 22px;
                color: #111827;
                margin-bottom: 5px;
            }}
            h2 {{
                font-size: 16px;
                color: #374151;
                margin-top: 25px;
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 2px solid #10b981;
            }}
            .header {{
                border-bottom: 3px solid #10b981;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .meta {{
                color: #6b7280;
                font-size: 11px;
            }}
            .score-box {{
                background: #ecfdf5;
                border: 2px solid #10b981;
                border-radius: 8px;
                padding: 15px;
                text-align: center;
                width: 120px;
                float: right;
                margin-left: 20px;
            }}
            .score-value {{
                font-size: 36px;
                font-weight: bold;
                color: #10b981;
            }}
            .score-label {{
                font-size: 11px;
                color: #6b7280;
            }}
            .section {{
                margin-bottom: 20px;
            }}
            .section-content {{
                background: #f9fafb;
                padding: 12px;
                border-radius: 6px;
            }}
            .warning-box {{
                background: #fef2f2;
                border-left: 4px solid #ef4444;
                padding: 12px;
                margin: 15px 0;
            }}
            .success-box {{
                background: #ecfdf5;
                border-left: 4px solid #10b981;
                padding: 12px;
                margin: 15px 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            th {{
                background: #f3f4f6;
                padding: 10px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid #e5e7eb;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #e5e7eb;
                text-align: center;
                color: #9ca3af;
                font-size: 10px;
            }}
            .stats-grid {{
                display: table;
                width: 100%;
                margin: 15px 0;
            }}
            .stat-item {{
                display: table-cell;
                width: 25%;
                text-align: center;
                padding: 10px;
                background: #f9fafb;
                border: 1px solid #e5e7eb;
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #10b981;
            }}
            .stat-label {{
                font-size: 10px;
                color: #6b7280;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="score-box">
                <div class="score-value">{overall_score:.1f}</div>
                <div class="score-label">av 5 poäng</div>
            </div>
            <h1>Analys av leadgenerering och konverteringsoptimering</h1>
            <p style="font-size: 16px; color: #374151; margin: 5px 0;">{company_name}</p>
            <p class="meta">
                {f'Bransch: {industry_label} | ' if industry_label else ''}
                Analyserad: {formatted_date}<br/>
                URL: {url}
            </p>
        </div>

        <div style="clear: both;"></div>

        <!-- Quick Stats -->
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">{len(lead_magnets)}</div>
                <div class="stat-label">Leadmagneter</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{len(forms)}</div>
                <div class="stat-label">Formulär</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{len(mailto_links)}</div>
                <div class="stat-label">Mailto-läckor</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{len(ungated_pdfs)}</div>
                <div class="stat-label">Öppna PDFs</div>
            </div>
        </div>

        <!-- Short Description -->
        {f'''
        <div class="section">
            <h2>Kort beskrivning</h2>
            <p>{short_description}</p>
        </div>
        ''' if short_description else ''}

        <!-- Leadmagneter & Forms Analysis -->
        {f'''
        <div class="section">
            <h2>Leadmagneter, formulär och innehåll</h2>
            <div class="section-content">
                {f"<p>{lead_magnets_analysis}</p>" if lead_magnets_analysis else ""}
                {f"<p style='margin-top: 10px;'>{forms_analysis}</p>" if forms_analysis else ""}
                {f"<p style='margin-top: 10px;'>{cta_analysis}</p>" if cta_analysis else ""}
            </div>
            {f'<p style="margin-top: 10px;"><strong>CTAs:</strong> {ctas_html}</p>' if ctas_html else ''}
        </div>
        ''' if (lead_magnets_analysis or forms_analysis or cta_analysis) else ''}

        <!-- Avgörande insikter -->
        {f'''
        <div class="section">
            <h2>Avgörande insikter</h2>
            <div class="warning-box">
                {logical_verdict.replace(chr(10), "<br/>")}
            </div>
        </div>
        ''' if logical_verdict else ''}

        <!-- Criteria Analysis Table -->
        <div class="section">
            <h2>Konverteringsanalys</h2>
            <table>
                <thead>
                    <tr>
                        <th style="width: 25%;">Kriterium</th>
                        <th style="width: 10%; text-align: center;">Betyg</th>
                        <th style="width: 65%;">Förklaring</th>
                    </tr>
                </thead>
                <tbody>
                    {criteria_rows}
                </tbody>
            </table>
        </div>

        <!-- Summary Assessment -->
        {f'''
        <div class="section">
            <h2>Sammanfattande bedömning</h2>
            <p>{summary_assessment}</p>
        </div>
        ''' if summary_assessment else ''}

        <!-- Recommendations -->
        {f'''
        <div class="section">
            <h2>Rekommendationer</h2>
            <div class="success-box">
                <ol style="margin: 0; padding-left: 20px;">
                    {recommendations_html}
                </ol>
            </div>
        </div>
        ''' if recommendations_html else ''}

        <!-- CTA Section -->
        <div class="section" style="background: #ecfdf5; border: 2px solid #10b981; padding: 20px; text-align: center; margin-top: 30px;">
            <h2 style="border: none; margin-top: 0; color: #065f46;">Nästa steg</h2>
            <p style="color: #374151; margin-bottom: 15px;">
                Vill du ha hjälp att åtgärda problemen och öka din konvertering?
            </p>
            <table align="center" cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                <tr>
                    <td style="background-color: #10b981; padding: 12px 24px; text-align: center;">
                        <a href="https://calendly.com/stefan-245/30min" style="color: #ffffff; font-weight: bold; text-decoration: none; display: block;">
                            Boka genomgång för ökad konvertering
                        </a>
                    </td>
                </tr>
            </table>
        </div>

        <div class="footer">
            <p>Genererad av <a href="https://leadsmaskinen.io" style="color: inherit;">Leadsmaskinen.io</a></p>
            <p>Rapport-ID: {data.get('report_id', 'N/A')} | {formatted_date}</p>
        </div>
    </body>
    </html>
    """

    return html
