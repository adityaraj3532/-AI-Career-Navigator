import math
from typing import Any, Dict, List, Tuple

RIASEC_DIMENSIONS: Tuple[str, ...] = ("R", "I", "A", "S", "E", "C")
MAX_EUCLIDEAN_DISTANCE: float = 100.0 * math.sqrt(6.0)  # ~244.9489742783178

DIMENSION_LABELS: Dict[str, str] = {
    "R": "Realistic",
    "I": "Investigative",
    "A": "Artistic",
    "S": "Social",
    "E": "Enterprising",
    "C": "Conventional",
}

DIMENSION_TRAITS: Dict[str, List[str]] = {
    "R": ["Practical problem-solver", "Hands-on builder", "Technically grounded"],
    "I": ["Analytical thinker", "Evidence-driven investigator", "Abstract problem-solver"],
    "A": ["Creative conceptualizer", "Expressive communicator", "Innovative designer"],
    "S": ["Empathetic collaborator", "Student & community mentor", "Team facilitator"],
    "E": ["Decisive initiator", "Persuasive communicator", "Strategic leader"],
    "C": ["Methodical organizer", "Process & data disciplined", "Detail-oriented planner"],
}

DIMENSION_SKILLS: Dict[str, List[str]] = {
    "R": ["Systems diagnostics", "Tool and equipment operation", "Physical prototyping"],
    "I": ["Data analysis", "Hypothesis testing", "Research synthesis"],
    "A": ["User experience design", "Creative storytelling", "Visual and interactive arts"],
    "S": ["Active listening", "Cross-functional coaching", "Stakeholder diplomacy"],
    "E": ["Negotiation", "Project pitching", "Strategic decision-making"],
    "C": ["Information architecture", "Quality assurance", "Workflow optimization"],
}

HOLLAND_ARCHETYPES: Dict[str, str] = {
    "RIA": "The Practical Researcher",
    "RIS": "The Diagnostic Specialist",
    "RIE": "The Technical Entrepreneur",
    "RIC": "The Systems Architect",
    "RAI": "The Industrial Designer",
    "RAS": "The Craft Educator",
    "RAE": "The Creative Producer",
    "RAC": "The Technical Drafter",
    "RSI": "The Health & Safety Technologist",
    "RSA": "The Adaptive Coach",
    "RSE": "The Operations Leader",
    "RSC": "The Facility Coordinator",
    "REI": "The Applied Engineering Manager",
    "REA": "The Media Operations Director",
    "RES": "The Field Project Leader",
    "REC": "The Logistics Director",
    "RCI": "The Forensic Auditor",
    "RCA": "The Production Specialist",
    "RCS": "The Compliance Inspector",
    "RCE": "The Supply Chain Coordinator",
    "IRA": "The Applied Scientist",
    "IRS": "The Medical Specialist",
    "IRE": "The Technology Strategist",
    "IRC": "The Systems Investigator",
    "IAR": "The Scientific Visualizer",
    "IAS": "The Compassionate Innovator",
    "IAE": "The Innovation Director",
    "IAC": "The Data Ethnographer",
    "ISR": "The Clinical Researcher",
    "ISA": "The Behavioral Scientist",
    "ISE": "The Healthcare Administrator",
    "ISC": "The Public Health Analyst",
    "IER": "The R&D Executive",
    "IEA": "The Strategic Designer",
    "IES": "The Organizational Psychologist",
    "IEC": "The Quantitative Strategist",
    "ICR": "The Systems Reliability Engineer",
    "ICA": "The Computational Linguist",
    "ICS": "The Health Informatician",
    "ICE": "The Data Science Director",
    "AIR": "The Computational Artist",
    "AIS": "The Educational Media Designer",
    "AIE": "The Creative Strategist",
    "AIC": "The Algorithmic Composer",
    "ARI": "The Environmental Sculptor",
    "ARS": "The Interactive Exhibit Designer",
    "ARE": "The Creative Director",
    "ARC": "The Architectural Draftsperson",
    "ASI": "The Art Therapist",
    "ASR": "The Community Arts Director",
    "ASE": "The Cultural Producer",
    "ASC": "The Curatorial Coordinator",
    "AEI": "The Digital Storytelling Lead",
    "AER": "The Immersive Experience Producer",
    "AES": "The Communications Director",
    "AEC": "The Brand Architecture Lead",
    "ACI": "The Technical Illustrator",
    "ACR": "The Production Designer",
    "ACS": "The Community Publisher",
    "ACE": "The Publication Director",
    "SIA": "The Human-Centered Researcher",
    "SIR": "The Ergonomic Consultant",
    "SIE": "The Clinical Program Director",
    "SIC": "The Epidemiological Coordinator",
    "SAI": "The Expressive Arts Educator",
    "SAR": "The Recreational Therapist",
    "SAE": "The Social Impact Strategist",
    "SAC": "The Community Program Manager",
    "SRI": "The Rehabilitation Technologist",
    "SRA": "The Adaptive Recreation Specialist",
    "SRE": "The Community Action Director",
    "SRC": "The Human Services Specialist",
    "SEI": "The Educational Policy Advocate",
    "SEA": "The Public Relations Director",
    "SER": "The Community Organizing Lead",
    "SEC": "The Non-Profit Executive",
    "SCI": "The Social Research Coordinator",
    "SCA": "The Youth Program Registrar",
    "SCR": "The Social Services Administrator",
    "SCE": "The Volunteer Services Director",
    "EIA": "The Venture Architect",
    "EIR": "The Deep-Tech Founder",
    "EIS": "The Health Ventures Director",
    "EIC": "The Fintech Strategist",
    "EAR": "The Industrial Brand Leader",
    "EAI": "The Media Tech Founder",
    "EAS": "The Public Affairs Director",
    "EAC": "The Creative Agency Principal",
    "ERI": "The Clean-Tech Entrepreneur",
    "ERA": "The Construction Project Principal",
    "ERS": "The Field Operations Director",
    "ERC": "The Infrastructure Developer",
    "ESI": "The Social Enterprise Founder",
    "ESA": "The Cause Campaign Director",
    "ESR": "The Workforce Development Lead",
    "ESC": "The Educational Institution Director",
    "ECI": "The Enterprise Analytics Executive",
    "ECA": "The Marketing Operations Director",
    "ECR": "The Supply Chain Executive",
    "ECS": "The Corporate Affairs Director",
    "CIR": "The Cryptographic Auditor",
    "CIA": "The Regulatory Informatics Analyst",
    "CIS": "The Clinical Data Manager",
    "CIE": "The Financial Risk Modeler",
    "CRI": "The Industrial Quality Engineer",
    "CRA": "The Technical Documentation Lead",
    "CRS": "The Operations Compliance Officer",
    "CRE": "The Procurement Specialist",
    "CAI": "The Information Architect",
    "CAR": "The Digital Archivist",
    "CAS": "The Educational Records Administrator",
    "CAE": "The Contract Publishing Manager",
    "CSI": "The Health Data Registrar",
    "CSR": "The Benefits Operations Coordinator",
    "CSA": "The Compliance Communications Lead",
    "CSE": "The Governance Program Manager",
    "CEI": "The Corporate Risk Assessor",
    "CER": "The Supply Chain Controller",
    "CEA": "The Commercial Operations Lead",
    "CES": "The Regulatory Relations Officer",
}


DIMENSION_KEY_MAP: Dict[str, str] = {
    "REALISTIC": "R",
    "INVESTIGATIVE": "I",
    "ARTISTIC": "A",
    "SOCIAL": "S",
    "ENTERPRISING": "E",
    "CONVENTIONAL": "C",
    "R": "R",
    "I": "I",
    "A": "A",
    "S": "S",
    "E": "E",
    "C": "C",
}


def normalize_dimension_code(dim: str) -> str:
    cleaned = dim.strip().upper()
    return DIMENSION_KEY_MAP.get(cleaned, cleaned[0] if cleaned else "R")


def compute_riasec_scores(
    answers_by_order: Dict[int, int],
    questions_metadata: List[Dict[str, Any]],
) -> Dict[str, float]:
    """
    Computes normalized RIASEC dimension scores (0.0 to 100.0) from answers.
    - 5 questions per dimension (ordered Likert 1-5).
    - Reverse scored items: adjusted = 6 - raw_value.
    - Normalized = ((raw_sum - 5) / 20) * 100.
    """
    raw_sums: Dict[str, int] = {dim: 0 for dim in RIASEC_DIMENSIONS}
    counts: Dict[str, int] = {dim: 0 for dim in RIASEC_DIMENSIONS}

    for q in questions_metadata:
        order = q["question_order"]
        raw_dim = q["dimension"]
        dim = normalize_dimension_code(raw_dim)
        reverse = q.get("reverse_scored", False)

        if order not in answers_by_order:
            continue

        raw_val = answers_by_order[order]
        eff_val = (6 - raw_val) if reverse else raw_val
        raw_sums[dim] += eff_val
        counts[dim] += 1

    normalized_scores: Dict[str, float] = {}
    for dim in RIASEC_DIMENSIONS:
        count = counts[dim]
        if count == 0:
            normalized_scores[dim] = 0.0
            continue
        # Raw sum for 5 questions is in range [5, 25]
        # Normalized = ((raw_sum - count) / (count * 4)) * 100
        score = ((raw_sums[dim] - count) / (count * 4.0)) * 100.0
        normalized_scores[dim] = round(max(0.0, min(100.0, score)), 2)

    return normalized_scores


def derive_holland_code(scores: Dict[str, float]) -> Tuple[str, str]:
    """
    Derives top-3 Holland Code with canonical tie-breaker:
    Canonical priority: R -> I -> A -> S -> E -> C.
    Sort key: (-score, canonical_index).
    """
    dim_order = {dim: idx for idx, dim in enumerate(RIASEC_DIMENSIONS)}

    # Sort dimensions descending by score; on ties, ascending by canonical index
    sorted_dims = sorted(
        RIASEC_DIMENSIONS,
        key=lambda d: (-scores.get(d, 0.0), dim_order[d]),
    )
    top_3 = "".join(sorted_dims[:3])
    label = HOLLAND_ARCHETYPES.get(
        top_3,
        f"{DIMENSION_LABELS[top_3[0]]}-{DIMENSION_LABELS[top_3[1]]}-{DIMENSION_LABELS[top_3[2]]}",
    )
    return top_3, label


def derive_traits_and_skills(holland_code: str) -> Tuple[List[str], List[str]]:
    """
    Derives lists of traits and skills from top Holland dimensions.
    """
    traits: List[str] = []
    skills: List[str] = []
    seen_traits = set()
    seen_skills = set()

    for dim in holland_code:
        for t in DIMENSION_TRAITS.get(dim, []):
            if t not in seen_traits:
                seen_traits.add(t)
                traits.append(t)
        for s in DIMENSION_SKILLS.get(dim, []):
            if s not in seen_skills:
                seen_skills.add(s)
                skills.append(s)

    return traits[:6], skills[:6]


def calculate_career_similarity(
    user_scores: Dict[str, float],
    career_weights: Dict[str, Any],
) -> float:
    """
    Calculates Euclidean vector similarity (0.0 to 1.0) between student scores and career weights.
    Both vectors are 6D in [0, 100].
    similarity = 1.0 - (euclidean_dist / max_euclidean_dist).
    """
    sq_dist = 0.0
    for dim in RIASEC_DIMENSIONS:
        u_val = float(user_scores.get(dim, 0.0))
        c_val = float(career_weights.get(dim, 0.0))
        diff = u_val - c_val
        sq_dist += diff * diff

    dist = math.sqrt(sq_dist)
    sim = 1.0 - (dist / MAX_EUCLIDEAN_DISTANCE)
    return round(max(0.0, min(1.0, sim)), 4)


def rank_careers(
    user_scores: Dict[str, float],
    careers: List[Dict[str, Any]],
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    """
    Ranks careers using pure vector similarity with deterministic tie-breaking:
    1. Similarity score descending
    2. Career title ascending (alphabetical)
    """
    scored_careers = []
    for c in careers:
        weights = c.get("dimension_weights", {})
        sim = calculate_career_similarity(user_scores, weights)
        scored_careers.append({
            "career_id": str(c["id"]),
            "code": c["code"],
            "title": c["title"],
            "cluster": c["cluster"],
            "overview": c["overview"],
            "source_url": c.get("source_url", ""),
            "similarity_score": sim,
        })

    # Sort: descending similarity (-sim), ascending title
    scored_careers.sort(key=lambda x: (-x["similarity_score"], x["title"]))
    return scored_careers[:top_n]


def map_streams_for_grade_11_12(
    user_scores: Dict[str, float],
    holland_code: str,
) -> List[str]:
    """
    For class_11_12 users, returns ordered stream recommendations prior to career recommendations.
    Synthesizes academic stream alignment with high school curricula (e.g. CBSE/ICSE):
    - Science (PCM - Physics, Chemistry, Mathematics): High R & I
    - Science (PCB - Physics, Chemistry, Biology): High I & S
    - Commerce with Mathematics: High C & E
    - Humanities & Social Sciences: High A & S
    """
    streams: List[str] = []
    top_2 = set(holland_code[:2])

    if "I" in top_2 and ("R" in top_2 or user_scores.get("R", 0.0) >= 50.0):
        streams.append("Science (PCM - Engineering, Computer Science, Physical Sciences)")

    if "I" in top_2 and ("S" in top_2 or user_scores.get("S", 0.0) >= 50.0):
        streams.append("Science (PCB - Medicine, Healthcare, Biological Sciences)")

    if "E" in top_2 or "C" in top_2:
        streams.append("Commerce with Mathematics (Finance, Economics, Business Analytics)")

    if "A" in top_2 or "S" in top_2:
        streams.append("Humanities & Liberal Arts (Design, Psychology, Media, Social Sciences)")

    # Ensure at least one primary stream is suggested
    if not streams:
        streams.append("General Studies & Interdisciplinary Stream")

    return streams[:3]
