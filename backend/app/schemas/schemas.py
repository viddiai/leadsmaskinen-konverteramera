"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator


# ============== Analysis Schemas ==============

class AnalyzeRequest(BaseModel):
    """Request schema for URL analysis."""
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        url_str = str(v)
        # Ensure it's a web URL
        if not url_str.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class AnalysisCriterion(BaseModel):
    """Single analysis criterion result."""
    criterion: str
    criterion_label: str
    score: int = Field(ge=1, le=5)
    explanation: str


class ShortSummaryResponse(BaseModel):
    """Response schema for short (public) analysis summary."""
    report_id: int
    url: str
    company_name: Optional[str]
    company_description: Optional[str]
    overall_score: float
    issues_count: int
    logical_errors: List[str]
    teaser_text: str

    # Enhanced AI-generated fields
    short_description: Optional[str] = None  # 3 sentences about the company
    detected_industry: Optional[str] = None  # Industry key
    industry_label: Optional[str] = None     # Swedish industry label


class FullReportResponse(BaseModel):
    """Response schema for full analysis report."""
    report_id: int
    url: str
    company_name: Optional[str]
    company_description: Optional[str]
    overall_score: float
    issues_count: int

    # Industry detection
    detected_industry: Optional[str] = None
    industry_label: Optional[str] = None

    # AI-generated text sections (comprehensive analysis)
    short_description: Optional[str] = None  # 3-4 sentences positioning company
    logical_verdict: Optional[str] = None    # Hard critique of conversion issues
    final_hook: Optional[str] = None         # Teaser for consultation

    # Detailed category analysis (AI-generated - comprehensive)
    lead_magnets_analysis: Optional[str] = None  # 2-3 paragraphs on lead magnets
    forms_analysis: Optional[str] = None         # 2 paragraphs on form design
    cta_analysis: Optional[str] = None           # 1-2 paragraphs on CTAs

    # Legacy detailed fields (for backward compatibility)
    detailed_lead_magnets: Optional[str] = None
    detailed_forms: Optional[str] = None
    detailed_social_proof: Optional[str] = None
    detailed_mailto: Optional[str] = None
    detailed_ungated_pdfs: Optional[str] = None

    # AI-generated criteria explanations (hård och direkt)
    criteria_explanations: Optional[Dict[str, str]] = None

    # Detected elements (raw data)
    lead_magnets: List[Dict[str, Any]]
    forms: List[Dict[str, Any]]
    cta_buttons: List[Dict[str, Any]]
    social_proof: List[Dict[str, Any]]
    mailto_links: List[Dict[str, Any]]  # "läckande tratt"
    ungated_pdfs: List[Dict[str, Any]]  # "läckande tratt"

    # Analysis scores
    criteria_analysis: List[AnalysisCriterion]

    # Text sections
    summary_assessment: str  # Comprehensive assessment
    recommendations: List[str]  # 5 concrete recommendations

    # AI generation status
    ai_generated: bool = False  # True when genuine AI analysis succeeded
    ai_completed: bool = False  # True when background generation finished (even on fallback)

    created_at: datetime


# ============== Lead Schemas ==============

class LeadCreate(BaseModel):
    """Schema for creating a new lead."""
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    company_name: Optional[str] = Field(None, max_length=255)
    report_id: int


class LeadResponse(BaseModel):
    """Response after lead creation."""
    success: bool
    message: str
    lead_id: Optional[int] = None
    access_token: Optional[str] = None

    class Config:
        from_attributes = True


class LeadListItem(BaseModel):
    """Lead item for admin listing."""
    id: int
    name: str
    email: str
    company_name: Optional[str]
    analyzed_url: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Report Schemas ==============

class ReportListItem(BaseModel):
    """Report item for admin listing."""
    id: int
    url: str
    company_name_detected: Optional[str]
    overall_score: Optional[float]
    issues_found: int
    lead_email: Optional[str] = None
    access_token: Optional[str] = None  # For PDF download link
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Widget Schemas ==============

class WidgetConfig(BaseModel):
    """Configuration options for embedded widget."""
    theme: str = "light"  # 'light' or 'dark'
    primary_color: str = "#2563eb"
    button_text: str = "Analysera"
    placeholder_text: str = "Ange URL att analysera..."


# ============== Admin Schemas ==============

class DashboardStats(BaseModel):
    """Statistics for admin dashboard."""
    total_leads: int
    total_reports: int
    reports_today: int
    leads_today: int
    average_score: Optional[float]
    top_issues: List[Dict[str, Any]]
