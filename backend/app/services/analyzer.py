"""
Analysis service that scores and generates recommendations.
Uses structured problem tagging according to the analyzer prompt methodology.
"""
from typing import Dict, List, Any, Tuple, Optional
from app.models.models import CRITERIA_LABELS
from app.services.scraper import contains_keyword

# Viktning enligt analyzer_prompt.md
CATEGORY_WEIGHTS = {
    "value_proposition": 2.0,
    "call_to_action": 1.5,
    "lead_magnets": 1.5,
    "social_proof": 1.0,
    "form_design": 1.0,
    "guiding_content": 1.0,
    "offer_structure": 1.0,
}
TOTAL_WEIGHT = sum(CATEGORY_WEIGHTS.values())  # 9.0

# Ikoner för varje kategori
CATEGORY_ICONS = {
    "value_proposition": "💎",
    "call_to_action": "🎯",
    "social_proof": "⭐",
    "lead_magnets": "🧲",
    "form_design": "📝",
    "guiding_content": "🗺️",
    "offer_structure": "💰",
}


def get_status_from_score(score: int) -> str:
    """Determine status based on score."""
    if score <= 2:
        return "critical"
    elif score == 3:
        return "improvement"
    else:
        return "good"


class ConversionAnalyzer:
    """
    Analyzes scraped data and generates scores, issues, and recommendations.
    All text output is in Swedish with a direct, no-nonsense tone.
    Uses structured problem tagging with severity levels.
    """

    def __init__(self, scraped_data: Dict[str, Any]):
        self.data = scraped_data

    def analyze_value_proposition(self) -> Dict[str, Any]:
        """
        Score the clarity and effectiveness of the value proposition.

        Problemtaggar:
        - unclear_headline – Otydlig eller vag rubrik
        - features_not_benefits – Fokus på egenskaper istället för fördelar
        - missing_usp – Saknar tydlig differentiering
        - value_prop_too_complex – För komplex eller lång förklaring
        - no_proof_points – Påståenden utan bevis

        Poängguide:
        1 = Rubriken förklarar inte vad företaget gör
        2 = Värdeerbjudande finns men fokuserar på egenskaper
        3 = Förståeligt men saknar differentiering
        4 = Tydliga fördelar men vissa påståenden saknar bevis
        5 = Kristallklart värde, tydliga fördelar med bevis
        """
        vp = self.data.get("value_proposition", {})
        problems = []

        h1 = vp.get("h1")
        h1_length = vp.get("h1_length", 0)
        has_hero = vp.get("has_hero", False)
        has_subheadline = vp.get("has_subheadline", False)

        # Kontrollera H1
        if not h1:
            problems.append({
                "tag": "unclear_headline",
                "severity": "high",
                "description": "Ingen H1-rubrik hittades. Besökare vet inte vad ni erbjuder inom de kritiska första sekunderna.",
                "recommendation": "Skriv en H1-rubrik som tydligt kommunicerar: (1) Vad ni gör, (2) För vem, och (3) Vilket resultat kunden kan förvänta sig.",
                "evidence": None
            })
        elif h1_length < 10:
            problems.append({
                "tag": "unclear_headline",
                "severity": "medium",
                "description": "H1-rubriken är för kort för att kommunicera ert värdeerbjudande effektivt.",
                "recommendation": "Utöka rubriken så den förklarar inte bara VAD ni gör utan också VARFÖR det är värdefullt.",
                "evidence": f"Hittade H1: '{h1}'"
            })
        elif h1_length > 80:
            problems.append({
                "tag": "value_prop_too_complex",
                "severity": "medium",
                "description": "H1-rubriken är för lång. Budskapet drunknar och besökare tappar intresset.",
                "recommendation": "Förkorta rubriken till max 60-70 tecken. Flytta detaljer till underrubriken.",
                "evidence": f"Hittade H1 ({h1_length} tecken): '{h1[:50]}...'"
            })

        # Kontrollera vaga rubriker (hela ord — "hem" ska inte matcha "hemleverans")
        vague_phrases = ["välkommen", "welcome", "vi är", "we are", "hem", "home"]
        if h1 and contains_keyword(h1.lower(), vague_phrases):
            problems.append({
                "tag": "unclear_headline",
                "severity": "high",
                "description": "Rubriken är vag och förklarar inte vad företaget faktiskt erbjuder eller vilket problem ni löser.",
                "recommendation": "Ersätt 'Välkommen'-rubriker med ett konkret värdeerbjudande. Exempel: 'Vi hjälper svenska e-handlare att dubbla sin konvertering'.",
                "evidence": f"Hittade rubrik: '{h1}'"
            })

        # Kontrollera hero-sektion
        if not has_hero:
            problems.append({
                "tag": "missing_usp",
                "severity": "medium",
                "description": "Ingen tydlig hero-sektion identifierades. Ert huvuderbjudande kan vara svårt att hitta.",
                "recommendation": "Skapa en framträdande hero-sektion ovanför fold med rubrik, underrubrik och CTA.",
                "evidence": None
            })

        # Kontrollera underrubrik
        if h1 and not has_subheadline:
            problems.append({
                "tag": "features_not_benefits",
                "severity": "low",
                "description": "Ingen underrubrik hittades som förtydligar eller expanderar på värdeerbjudandet.",
                "recommendation": "Lägg till en underrubrik som specificerar fördelarna för kunden eller differentierar från konkurrenter.",
                "evidence": None
            })

        # Beräkna poäng baserat på promptens poängguide
        if not h1 or (h1 and contains_keyword(h1.lower(), vague_phrases)):
            score = 1  # Rubriken förklarar inte vad företaget gör
        elif not has_hero and not has_subheadline:
            score = 2  # Värdeerbjudande finns men fokuserar på egenskaper
        elif has_hero and (not has_subheadline or h1_length > 80):
            score = 3  # Förståeligt men saknar differentiering
        elif has_hero and has_subheadline and h1_length <= 80:
            score = 4  # Tydliga fördelar men kan sakna bevis
        else:
            score = 3  # Default: förståeligt men kan förbättras

        # Justera uppåt om inga problem hittades
        if not problems:
            score = 5

        return {
            "score": max(1, min(5, score)),
            "problems": problems,
        }

    def analyze_cta(self) -> Dict[str, Any]:
        """
        Score Call-to-Action buttons and their effectiveness.

        Problemtaggar:
        - no_cta_found – Ingen CTA hittades
        - cta_below_fold – CTA inte synlig utan scroll (kan inte detekteras utan rendering)
        - generic_cta_text – Generisk knapptext ("Skicka")
        - low_contrast_cta – CTA smälter in visuellt (kräver CSS-analys)
        - single_cta_placement – Endast en CTA-placering

        Poängguide:
        1 = Ingen tydlig CTA hittades
        2 = CTA finns men generisk text eller svår att hitta
        3 = Tydlig CTA men dåligt placerad
        4 = Bra CTA, synlig placering, kan förstärkas
        5 = Optimala CTA:er med starkt språk, multipla placeringar
        """
        ctas = self.data.get("cta_buttons", [])
        problems = []

        if not ctas:
            problems.append({
                "tag": "no_cta_found",
                "severity": "high",
                "description": "Ingen tydlig Call-to-Action hittades. Besökare vet inte vad de ska göra på sidan.",
                "recommendation": "Lägg till tydliga CTA-knappar med handlingsorienterad text som 'Få din kostnadsfria offert' eller 'Boka ett samtal'.",
                "evidence": None
            })
            return {"score": 1, "problems": problems}

        # Kontrollera antal CTA:er
        if len(ctas) == 1:
            problems.append({
                "tag": "single_cta_placement",
                "severity": "medium",
                "description": "Endast en CTA-knapp hittades. Besökare kan missa den när de scrollar.",
                "recommendation": "Upprepa er CTA på strategiska platser genom hela sidan – efter varje sektion som bygger värde.",
                "evidence": f"Hittade 1 CTA: '{ctas[0].get('text', '')}'"
            })

        # Kontrollera svaga/generiska CTA-texter
        weak_texts = ["läs mer", "read more", "mer info", "more info", "klicka här",
                      "click here", "skicka", "submit", "send", "vidare", "continue"]

        for cta in ctas:
            cta_text = cta.get("text", "").lower().strip()
            if cta_text in weak_texts or any(weak in cta_text for weak in ["läs mer", "klicka"]):
                problems.append({
                    "tag": "generic_cta_text",
                    "severity": "high",
                    "description": f"CTA-texten '{cta.get('text')}' är generisk och motiverar inte till handling.",
                    "recommendation": "Byt till handlingsorienterat språk som kommunicerar värde: 'Få din kostnadsfria analys', 'Boka ditt gratis samtal', 'Starta din provperiod'.",
                    "evidence": f"Hittade CTA: '{cta.get('text')}'"
                })
                break  # Rapportera bara första svaga CTA:n

        # Kontrollera om det finns starka CTA:er
        strong_patterns = ["gratis", "free", "starta", "start", "prova", "try",
                          "boka", "book", "få", "get", "hämta", "ladda"]
        has_strong_cta = any(
            contains_keyword(cta.get("text", "").lower(), strong_patterns)
            for cta in ctas
        )

        # Beräkna poäng
        if not ctas:
            score = 1
        elif len([p for p in problems if p["severity"] == "high"]) > 0:
            score = 2  # Har generisk text
        elif len(ctas) == 1:
            score = 3  # Tydlig men ej multipel
        elif has_strong_cta and len(ctas) >= 2:
            score = 4 if problems else 5
        else:
            score = 3

        return {
            "score": max(1, min(5, score)),
            "problems": problems,
        }

    def analyze_social_proof(self) -> Dict[str, Any]:
        """
        Score the presence and quality of social proof.

        Problemtaggar:
        - no_social_proof – Ingen social proof hittades
        - no_testimonials – Inga kundcitat
        - anonymous_testimonials – Testimonials utan namn/företag
        - no_client_logos – Inga kundlogotyper
        - no_quantitative_proof – Inga siffror (antal kunder, år)
        - social_proof_poor_placement – Social proof inte nära beslutspunkter

        Poängguide:
        1 = Ingen social proof
        2 = Minimal social proof – anonym eller gömd
        3 = Grundläggande social proof men ej strategiskt placerad
        4 = Flera typer av social proof, bra placering
        5 = Omfattande proof magnets – testimonials, siffror, logotyper
        """
        proof = self.data.get("social_proof", [])
        problems = []

        if not proof:
            problems.append({
                "tag": "no_social_proof",
                "severity": "high",
                "description": "Ingen social proof hittades. Besökare har ingen anledning att lita på er förutom ert eget ord.",
                "recommendation": "Börja med att samla in 3-5 kundcitat med namn och företag. Placera dem på startsidan, gärna nära era CTA:er.",
                "evidence": None
            })
            return {"score": 1, "problems": problems}

        # Analysera vilka typer som finns
        types_found = set(p.get("type") for p in proof)

        has_testimonials = "testimonial" in types_found or "quote" in types_found
        has_logos = "client_logos" in types_found
        has_ratings = "ratings" in types_found

        if not has_testimonials:
            problems.append({
                "tag": "no_testimonials",
                "severity": "medium",
                "description": "Inga kundcitat eller testimonials hittades. Testimonials är den mest övertygande formen av social proof.",
                "recommendation": "Lägg till 2-3 kundcitat med fullständigt namn, företag och gärna foto. Citat som nämner konkreta resultat är mest effektiva.",
                "evidence": None
            })

        if not has_logos:
            problems.append({
                "tag": "no_client_logos",
                "severity": "low",
                "description": "Inga kundlogotyper synliga. Logotyper ger snabb visuell trovärdighet.",
                "recommendation": "Lägg till en sektion med logotyper från era mest igenkännbara kunder eller partners.",
                "evidence": None
            })

        if not has_ratings:
            problems.append({
                "tag": "no_quantitative_proof",
                "severity": "low",
                "description": "Inga kvantitativa bevis hittades (antal kunder, år i branschen, betyg).",
                "recommendation": "Lägg till konkreta siffror: 'X nöjda kunder', 'Y års erfarenhet', eller externa betyg från Trustpilot/Google.",
                "evidence": None
            })

        # Beräkna poäng
        proof_types_count = sum([has_testimonials, has_logos, has_ratings])

        if proof_types_count == 0:
            score = 1
        elif proof_types_count == 1 and not has_testimonials:
            score = 2
        elif proof_types_count == 1:
            score = 3
        elif proof_types_count == 2:
            score = 4
        else:
            score = 5

        return {
            "score": max(1, min(5, score)),
            "problems": problems,
        }

    def analyze_lead_magnets(self) -> Dict[str, Any]:
        """
        Score the presence and quality of lead magnets.

        Problemtaggar:
        - no_lead_magnet – Ingen leadmagnet hittades
        - mailto_link_leak – mailto:-länk istället för formulär
        - open_pdf_leak – Värdefull PDF utan lead capture
        - weak_lead_magnet_value – Svagt värdeerbjudande ("Prenumerera")
        - lead_magnet_hidden – Leadmagnet svår att hitta
        - lead_magnet_too_many_fields – För många fält i formuläret

        Poängguide:
        1 = Ingen leadmagnet
        2 = Har "nyhetsbrev" utan värde, eller läckande trattar
        3 = Leadmagnet finns men svår att hitta
        4 = Bra leadmagnet med tydligt värde, men för många fält
        5 = Oemotståndlig leadmagnet, minimalt formulär, strategiskt placerad
        """
        magnets = self.data.get("lead_magnets", [])
        ungated = self.data.get("ungated_pdfs", [])
        mailto = self.data.get("mailto_links", [])
        problems = []

        # Kritiskt: Inga leadmagneter
        if not magnets:
            problems.append({
                "tag": "no_lead_magnet",
                "severity": "high",
                "description": "Ingen leadmagnet hittades. Besökare som inte är köpklara har inget sätt att stanna i kontakt.",
                "recommendation": "Skapa en lead magnet – en checklista, guide eller kalkylator som löser ett konkret problem för er målgrupp. Erbjud den i utbyte mot e-post.",
                "evidence": None
            })

        # Kritiskt: mailto-länkar (läckande trattar)
        if mailto:
            for m in mailto[:2]:  # Max 2 exempel
                problems.append({
                    "tag": "mailto_link_leak",
                    "severity": "high",
                    "description": f"mailto:-länk exponerar er e-post direkt och gör det omöjligt att spåra konverteringar.",
                    "recommendation": "Ersätt mailto-länken med ett kontaktformulär som samlar in namn och e-post innan ni svarar.",
                    "evidence": f"Hittade: mailto:{m.get('email', '')}"
                })

        # Kritiskt: Ungated PDFs (läckande trattar)
        if ungated:
            for pdf in ungated[:2]:  # Max 2 exempel
                problems.append({
                    "tag": "open_pdf_leak",
                    "severity": "high",
                    "description": "Värdefull PDF ges bort utan att fånga kontaktuppgifter. Detta är en läckande tratt.",
                    "recommendation": "Placera PDF:en bakom ett enkelt formulär (namn + e-post). Behåll värdet ni erbjuder, men fånga leadet.",
                    "evidence": f"Hittade: {pdf.get('text', pdf.get('url', ''))[:50]}"
                })

        # Kontrollera gated vs ungated
        gated = [m for m in magnets if m.get("is_gated")]

        # Svagt värdeerbjudande ("prenumerera på nyhetsbrev")
        weak_value_keywords = ["nyhetsbrev", "newsletter", "prenumerera", "subscribe"]
        for magnet in magnets:
            text = magnet.get("text", "").lower()
            if any(kw in text for kw in weak_value_keywords):
                problems.append({
                    "tag": "weak_lead_magnet_value",
                    "severity": "medium",
                    "description": "'Prenumerera på nyhetsbrev' är ett svagt värdeerbjudande. Få besökare vill ha mer e-post.",
                    "recommendation": "Erbjud något konkret värdefullt: en guide, checklista, mall eller kostnadsfri konsultation.",
                    "evidence": f"Hittade: '{magnet.get('text', '')}'"
                })
                break

        # Beräkna poäng
        has_leaks = len(mailto) > 0 or len(ungated) > 0
        has_gated_magnets = len(gated) > 0

        if not magnets and not has_leaks:
            score = 1  # Ingen leadmagnet
        elif has_leaks and not has_gated_magnets:
            score = 2  # Har läckor men inga gated magnets
        elif has_leaks and has_gated_magnets:
            score = 3  # Har både läckor och bra magnets
        elif has_gated_magnets and len(gated) >= 2:
            score = 4 if problems else 5
        elif has_gated_magnets:
            score = 4
        else:
            score = 3

        return {
            "score": max(1, min(5, score)),
            "problems": problems,
        }

    def analyze_form_design(self) -> Dict[str, Any]:
        """
        Score form design and usability.

        Problemtaggar:
        - too_many_form_fields – För många fält
        - unnecessary_required_fields – Onödiga obligatoriska fält
        - generic_submit_button – Generisk submit-knapp
        - unclear_field_labels – Otydliga fältetiketter
        - captcha_friction – CAPTCHA skapar friktion

        Poängguide:
        1 = Formulär med många onödiga fält, betydande friktion
        2 = Fungerar men generisk knapp och/eller för många fält
        3 = Rimligt formulär men saknar optimering
        4 = Strömlinjeformat, få fält, bra knapptext
        5 = Friktionsfritt, minimala fält, handlingsorienterad knapp
        """
        forms = self.data.get("forms", [])
        problems = []

        # Filtrera bort sökformulär
        lead_forms = [f for f in forms if f.get("type") != "search"]

        if not lead_forms:
            problems.append({
                "tag": "no_form_found",
                "severity": "high",
                "description": "Inga lead capture-formulär hittades. Hur ska ni samla in leads från webbplatsen?",
                "recommendation": "Lägg till ett kontaktformulär eller lead capture-formulär på startsidan.",
                "evidence": None
            })
            return {"score": 1, "problems": problems}

        # Analysera formulären
        has_generic_button = False
        has_too_many_fields = False

        for form in lead_forms:
            fields = form.get("fields", [])
            submit_text = form.get("submit_text", "").lower().strip()

            # Kontrollera antal fält
            if len(fields) > 5:
                has_too_many_fields = True
                problems.append({
                    "tag": "too_many_form_fields",
                    "severity": "high",
                    "description": f"Formuläret har {len(fields)} fält. Varje extra fält minskar konverteringen med ca 10%.",
                    "recommendation": "Reducera till max 3-4 fält. Samla in övrig information senare i säljprocessen.",
                    "evidence": f"Fält: {', '.join([f.get('name', 'okänt') for f in fields[:5]])}"
                })
                break

            # Kontrollera generisk knapptext
            generic_buttons = ["submit", "skicka", "send", "ok", "continue", "vidare"]
            if submit_text in generic_buttons:
                has_generic_button = True
                problems.append({
                    "tag": "generic_submit_button",
                    "severity": "medium",
                    "description": f"Knappen '{form.get('submit_text')}' är generisk och motiverar inte till handling.",
                    "recommendation": "Byt till handlingsorienterad text som kommunicerar värde: 'Få mitt svar inom 24h', 'Skicka min förfrågan', 'Boka mitt samtal'.",
                    "evidence": f"Hittade knapp: '{form.get('submit_text')}'"
                })

        # Beräkna poäng
        if has_too_many_fields and has_generic_button:
            score = 1
        elif has_too_many_fields or (has_generic_button and len(problems) > 1):
            score = 2
        elif has_generic_button:
            score = 3
        elif not problems:
            score = 5
        else:
            score = 4

        return {
            "score": max(1, min(5, score)),
            "problems": problems,
        }

    def analyze_guiding_content(self) -> Dict[str, Any]:
        """
        Score how well the page guides visitors toward conversion.

        Problemtaggar:
        - no_process_explanation – Ingen förklaring av processen
        - no_next_step_info – Oklart vad som händer härnäst
        - no_timeline_info – Inga tidsförväntningar
        - no_visual_process – Saknar visuell processförklaring
        - contact_info_hidden – Kontaktinfo svår att hitta

        Poängguide:
        1 = Ingen processinfo. Besökaren måste "hoppa i mörkret"
        2 = Vag eller ofullständig processinformation
        3 = Grundläggande info men inte visuellt eller detaljerat
        4 = Tydlig process med steg och tidsramar
        5 = Komplett future-pacing med visuellt flödesschema
        """
        problems = []

        forms = self.data.get("forms", [])
        ctas = self.data.get("cta_buttons", [])
        lead_forms = [f for f in forms if f.get("type") != "search"]

        # Kontrollera om det finns någon väg till konvertering
        if not lead_forms and not ctas:
            problems.append({
                "tag": "no_next_step_info",
                "severity": "high",
                "description": "Ingen tydlig väg till konvertering hittades. Besökare vet inte hur de ska ta kontakt.",
                "recommendation": "Lägg till tydliga konverteringsvägar: formulär, CTA-knappar och kontaktinformation.",
                "evidence": None
            })

        # mailto-länkar som indikerar dold kontaktinfo
        mailto = self.data.get("mailto_links", [])
        if mailto and not lead_forms:
            problems.append({
                "tag": "contact_info_hidden",
                "severity": "medium",
                "description": "Kontaktmöjligheten är begränsad till e-postlänkar. Många besökare föredrar formulär.",
                "recommendation": "Komplettera e-postadressen med ett kontaktformulär för att sänka tröskeln.",
                "evidence": None
            })

        # Beräkna poäng baserat på grundläggande struktur
        has_forms = len(lead_forms) > 0
        has_ctas = len(ctas) > 0
        has_multiple_ctas = len(ctas) >= 3

        if not has_forms and not has_ctas:
            score = 1
        elif has_forms and not has_ctas:
            score = 2
        elif has_forms and has_ctas:
            score = 3 if not has_multiple_ctas else 4
        else:
            score = 3

        # Om inga allvarliga problem, ge högre poäng
        high_severity_problems = [p for p in problems if p["severity"] == "high"]
        if not high_severity_problems and has_forms and has_ctas:
            score = min(5, score + 1)

        return {
            "score": max(1, min(5, score)),
            "problems": problems,
        }

    def analyze_offer_structure(self) -> Dict[str, Any]:
        """
        Score the offer structure - pricing, barriers, and value communication.

        Problemtaggar:
        - no_low_barrier_entry – Inget enkelt första steg
        - pricing_not_transparent – Otydlig eller saknad prissättning
        - single_offering – Endast ett alternativ
        - no_premiums – Inga bonusar eller extra värde
        - value_not_communicated – Värdet inte tydligt relativt pris

        Poängguide:
        1 = Inget enkelt första steg, otydligt erbjudande, hög tröskel
        2 = Erbjudande finns men inte optimerat, ingen låg tröskel
        3 = Rimligt erbjudande men kan förbättras med segmentering
        4 = Bra erbjudande med låg tröskel och viss segmentering
        5 = "No-brainer" erbjudande, transparent prissättning, bonusar
        """
        problems = []
        ctas = self.data.get("cta_buttons", [])
        offer_data = self.data.get("offer_structure", {})

        # Kontrollera efter låg tröskel-erbjudanden från scraper
        has_free_offer = offer_data.get("has_free_offer", False)

        # Backup: kontrollera CTAs om scraper inte hittade något
        if not has_free_offer:
            low_barrier_keywords = ["gratis", "free", "kostnadsfri", "prova", "try",
                                   "demo", "test", "provperiod", "trial", "ingen bindning",
                                   "no commitment", "konsultation", "consultation"]
            has_free_offer = any(
                contains_keyword(cta.get("text", "").lower(), low_barrier_keywords)
                for cta in ctas
            )

        if not has_free_offer:
            problems.append({
                "tag": "no_low_barrier_entry",
                "severity": "high",
                "description": "Inget 'no-brainer' första steg hittades. Besökare måste förplikta sig utan att först kunna testa.",
                "recommendation": "Skapa ett erbjudande med låg tröskel: gratis konsultation, provperiod, eller introduktionspris. Detta minskar risken för besökaren.",
                "evidence": None
            })

        # Kontrollera prissättning
        has_pricing = offer_data.get("has_pricing", False)
        has_segmented_pricing = offer_data.get("has_segmented_pricing", False)
        pricing_tiers = offer_data.get("pricing_tiers", 0)

        if not has_pricing:
            problems.append({
                "tag": "pricing_not_transparent",
                "severity": "medium",
                "description": "Ingen tydlig prissättning hittades på sidan. Besökare kan tveka när de inte vet vad det kostar.",
                "recommendation": "Lägg till priser eller åtminstone prisintervall. Transparent prissättning ökar förtroendet och filtrerar bort fel leads tidigt.",
                "evidence": None
            })

        # Kontrollera segmentering
        if has_pricing and not has_segmented_pricing:
            problems.append({
                "tag": "single_offering",
                "severity": "low",
                "description": "Endast ett prisalternativ verkar finnas. Segmenterade erbjudanden (Basic/Pro/Premium) ökar konverteringen.",
                "recommendation": "Överväg att erbjuda 2-3 nivåer för att fånga olika kundsegment. Det mittresstående alternativet väljs oftast (decoy-effekten).",
                "evidence": None
            })

        # Beräkna poäng baserat på strukturen
        score = 3  # Default: rimligt erbjudande

        if not ctas and not has_free_offer:
            score = 1  # Inget första steg, hög tröskel
        elif not has_free_offer and not has_pricing:
            score = 2  # Erbjudande finns men inte optimerat
        elif has_free_offer and not has_pricing:
            score = 3  # Har låg tröskel men saknar prisinfo
        elif has_free_offer and has_pricing and not has_segmented_pricing:
            score = 4  # Bra erbjudande med låg tröskel
        elif has_free_offer and has_pricing and has_segmented_pricing:
            score = 5  # No-brainer med segmentering

        # Justera nedåt om det finns allvarliga problem
        high_severity_problems = [p for p in problems if p["severity"] == "high"]
        if high_severity_problems:
            score = min(score, 2)

        return {
            "score": max(1, min(5, score)),
            "problems": problems,
        }

    def generate_leaking_funnels(self) -> List[Dict[str, Any]]:
        """
        Generate a dedicated leaking funnels section.
        These are critical issues where leads are being lost.
        """
        leaking_funnels = []

        # mailto-länkar
        mailto = self.data.get("mailto_links", [])
        for m in mailto:
            leaking_funnels.append({
                "type": "mailto_link_leak",
                "severity": "high",
                "location": m.get("context", "Kontaktsektionen")[:50],
                "details": f"mailto:{m.get('email', '')}",
                "recommendation": "Ersätt med kontaktformulär"
            })

        # Ungated PDFs
        ungated = self.data.get("ungated_pdfs", [])
        for pdf in ungated:
            leaking_funnels.append({
                "type": "open_pdf_leak",
                "severity": "high",
                "location": pdf.get("text", "PDF-länk")[:50],
                "details": pdf.get("url", "")[:100],
                "recommendation": "Gate PDF:en bakom formulär"
            })

        return leaking_funnels

    def generate_analysis(self) -> Dict[str, Any]:
        """
        Generate complete analysis with all scores, problems, and explanations.
        """
        criteria_analysis = []

        # Analyze each criterion
        analysis_methods = [
            ("value_proposition", self.analyze_value_proposition),
            ("call_to_action", self.analyze_cta),
            ("social_proof", self.analyze_social_proof),
            ("lead_magnets", self.analyze_lead_magnets),
            ("form_design", self.analyze_form_design),
            ("guiding_content", self.analyze_guiding_content),
            ("offer_structure", self.analyze_offer_structure),
        ]

        for criterion, method in analysis_methods:
            result = method()
            score = result["score"]
            weight = CATEGORY_WEIGHTS[criterion]

            criteria_analysis.append({
                "criterion": criterion,
                "criterion_label": CRITERIA_LABELS.get(criterion, criterion),
                "icon": CATEGORY_ICONS.get(criterion, "📊"),
                "score": score,
                "weight": weight,
                "weighted_score": round(score * weight, 2),
                "status": get_status_from_score(score),
                "problems": result["problems"],
                # Legacy: Keep explanation for backwards compatibility
                "explanation": " | ".join([p["description"] for p in result["problems"]]) if result["problems"] else "Inga problem identifierade",
            })

        # Calculate weighted overall score
        weighted_sum = sum(c["weighted_score"] for c in criteria_analysis)
        # Normalisera till 1-5 skala
        overall_score = round((weighted_sum / TOTAL_WEIGHT), 1)

        # Count issues
        issues_found = self._count_issues()

        # Generate logical errors (for short summary)
        logical_errors = self._generate_logical_errors()

        # Generate leaking funnels
        leaking_funnels = self.generate_leaking_funnels()

        return {
            "criteria_analysis": criteria_analysis,
            "overall_score": overall_score,
            "issues_found": issues_found,
            "logical_errors": logical_errors,
            "leaking_funnels": leaking_funnels,
        }

    def _count_issues(self) -> int:
        """Count total number of issues found."""
        count = 0
        count += len(self.data.get("mailto_links", []))
        count += len(self.data.get("ungated_pdfs", []))

        forms = self.data.get("forms", [])
        lead_forms = [f for f in forms if f.get("type") != "search"]
        if not lead_forms:
            count += 1

        if not self.data.get("lead_magnets"):
            count += 1

        if not self.data.get("social_proof"):
            count += 1

        if not self.data.get("cta_buttons"):
            count += 1

        vp = self.data.get("value_proposition", {})
        if not vp.get("h1"):
            count += 1

        return count

    def _generate_logical_errors(self) -> List[str]:
        """Generate list of logical errors for short summary."""
        errors = []

        mailto = self.data.get("mailto_links", [])
        if mailto:
            errors.append(f"Ni har {len(mailto)} mailto-länkar som läcker leads till era konkurrenter")

        ungated = self.data.get("ungated_pdfs", [])
        if ungated:
            errors.append(f"{len(ungated)} värdefulla PDF-resurser ges bort utan att fånga e-postadresser")

        if not self.data.get("lead_magnets"):
            errors.append("Inga lead magnets identifierade - ni missar alla passiva leads")

        if not self.data.get("social_proof"):
            errors.append("Ingen synlig social proof - besökare har ingen anledning att lita på er")

        forms = self.data.get("forms", [])
        lead_forms = [f for f in forms if f.get("type") != "search"]
        if not lead_forms:
            errors.append("Inga lead capture-formulär - hur tänker ni konvertera trafik?")

        vp = self.data.get("value_proposition", {})
        if not vp.get("h1"):
            errors.append("Ingen H1-rubrik - besökare vet inte vad ni erbjuder inom 3 sekunder")

        return errors[:5]  # Max 5 errors for summary

    def generate_summary_assessment(self) -> str:
        """
        Generate 8 lines of 'obarmhärtig analys' (ruthless analysis).
        """
        lines = []
        company = self.data.get("company_info", {}).get("company_name", "Ert företag")

        mailto = self.data.get("mailto_links", [])
        ungated = self.data.get("ungated_pdfs", [])
        forms = self.data.get("forms", [])
        lead_forms = [f for f in forms if f.get("type") != "search"]
        social = self.data.get("social_proof", [])
        magnets = self.data.get("lead_magnets", [])

        # Line 1: Overall assessment
        issues = self._count_issues()
        if issues > 5:
            lines.append(f"{company} har allvarliga brister i sin lead generation-strategi.")
        elif issues > 2:
            lines.append(f"{company} har flera tydliga förbättringsområden i sin konverteringstratt.")
        else:
            lines.append(f"{company} har en grundläggande struktur på plats men missar viktiga möjligheter.")

        # Line 2: mailto links
        if mailto:
            lines.append(f"Att exponera {len(mailto)} e-postadresser via mailto-länkar är amatörmässigt - ni ger bort leads gratis.")
        else:
            lines.append("Bra att ni undviker direkta mailto-länkar, men det räcker inte.")

        # Line 3: Lead magnets
        if not magnets:
            lines.append("Utan lead magnets förlitar ni er helt på att besökare aktivt kontaktar er - det gör de inte.")
        elif ungated:
            lines.append(f"Att ge bort {len(ungated)} PDF-resurser utan att fånga e-post är att kasta pengar i sjön.")

        # Line 4: Forms
        if not lead_forms:
            lines.append("Avsaknaden av konverteringsformulär betyder att er webbplats är en digital broschyr, inte ett säljverktyg.")
        else:
            lines.append(f"Med {len(lead_forms)} formulär har ni åtminstone grunderna på plats.")

        # Line 5: Social proof
        if not social:
            lines.append("Ingen social proof syns - varje besökare måste lita blint på er, och det gör de inte.")
        else:
            lines.append("Social proof finns men kan troligen stärkas med fler kundcase och resultat.")

        # Line 6: The reality
        lines.append("Varje dag er webbsida ser ut så här förlorar ni potentiella kunder till konkurrenter som förstår lead generation.")

        # Line 7: The cost
        lines.append("Kostnaden för dessa brister är inte synlig i er budget, men den är verklig i förlorade affärer.")

        # Line 8: The path forward
        lines.append("Fixarna nedan är konkreta och mätbara - frågan är om ni prioriterar tillväxt eller status quo.")

        return "\n\n".join(lines)

    def generate_recommendations(self) -> List[str]:
        """
        Generate 5 concrete, actionable recommendations.
        """
        recommendations = []

        mailto = self.data.get("mailto_links", [])
        ungated = self.data.get("ungated_pdfs", [])
        forms = self.data.get("forms", [])
        lead_forms = [f for f in forms if f.get("type") != "search"]
        magnets = self.data.get("lead_magnets", [])
        social = self.data.get("social_proof", [])
        ctas = self.data.get("cta_buttons", [])
        vp = self.data.get("value_proposition", {})

        # Priority 1: Fix leaks
        if mailto:
            recommendations.append(
                f"Ersätt alla {len(mailto)} mailto-länkar med kontaktformulär. "
                "Varje mailto är en lead som försvinner ospårad."
            )

        if ungated:
            recommendations.append(
                f"Gate era {len(ungated)} öppna PDF:er bakom enkla formulär. "
                "Begär endast e-post - minimera friktionen men fånga leadet."
            )

        # Priority 2: Add what's missing
        if not magnets:
            recommendations.append(
                "Skapa en lead magnet inom 2 veckor. "
                "En enkel checklista eller guide som löser ett konkret problem för er målgrupp."
            )

        if not lead_forms:
            recommendations.append(
                "Lägg till ett lead capture-formulär above the fold. "
                "Erbjud något värdefullt i utbyte mot e-postadress."
            )

        if not social:
            recommendations.append(
                "Samla 3-5 kundcitat med namn och foto. "
                "Placera dem strategiskt nära era CTA:er."
            )

        # Priority 3: Optimize existing
        if not vp.get("h1"):
            recommendations.append(
                "Skriv en H1-rubrik som tydligt kommunicerar ert värdeerbjudande. "
                "Besökare bestämmer inom 3 sekunder om de stannar."
            )

        if len(ctas) < 3:
            recommendations.append(
                "Lägg till fler CTA:er genom hela sidan. "
                "Varje scrolldjup ska ha en tydlig handlingsuppmaning."
            )

        # Generic strong recommendations if we haven't filled 5
        generic = [
            "Implementera exit-intent popups för att fånga besökare som är på väg att lämna.",
            "A/B-testa era formulär - även små ändringar i knapptext kan öka konverteringen 20-30%.",
            "Installera heatmap-verktyg för att se var besökare faktiskt klickar och scrollar.",
            "Skapa en dedikerad landningssida för varje trafikskälla ni använder.",
            "Bygg en e-postsekvens som automatiskt nurturar leads som laddar ner ert material.",
        ]

        while len(recommendations) < 5 and generic:
            recommendations.append(generic.pop(0))

        return recommendations[:5]
