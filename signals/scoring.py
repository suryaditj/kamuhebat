def calculate_score(analysis: dict, signal: dict) -> dict:
    """
    Menilai kualitas setup berdasarkan bukti SMC.

    Skor maksimal 100.
    Skor bukan probabilitas kemenangan.
    """

    if signal.get("status") not in ("BULLISH", "BEARISH"):
        return {
            "score": 0,
            "quality": "TIDAK ADA SETUP",
            "details": {}
        }

    direction = signal["status"]

    h1 = analysis.get("h1", {})
    m15 = analysis.get("m15", {})
    evidence = signal.get("evidence", {})

    score = 0
    details = {}

    # 1. Arah H1
    h1_valid = h1.get("bias") == direction

    details["h1_bias"] = 20 if h1_valid else 0
    score += details["h1_bias"]

    # 2. Struktur M15
    m15_valid = m15.get("trend") == direction

    details["m15_structure"] = 15 if m15_valid else 0
    score += details["m15_structure"]

    # 3. Zona searah
    zone = m15.get("target_zone")

    expected_zone = (
        "DEMAND" if direction == "BULLISH"
        else "SUPPLY"
    )

    zone_valid = (
        zone is not None
        and zone.get("type") == expected_zone
        and evidence.get("zone_touched", False)
    )

    details["zone"] = 20 if zone_valid else 0
    score += details["zone"]

    # 4. Rejection
    rejection_valid = evidence.get("rejection", False)

    details["rejection"] = 15 if rejection_valid else 0
    score += details["rejection"]

    # 5. Struktur M5
    structure_valid = evidence.get("structure", False)

    details["m5_structure"] = 10 if structure_valid else 0
    score += details["m5_structure"]

    # 6. BOS / CHoCH
    bos_valid = evidence.get("bos", False)

    details["bos_choch"] = 10 if bos_valid else 0
    score += details["bos_choch"]

    # 7. Displacement
    displacement_valid = evidence.get("displacement", False)

    details["displacement"] = (
        5 if displacement_valid else 0
    )
    score += details["displacement"]

    # 8. Pullback
    pullback_valid = evidence.get("pullback", False)

    details["pullback"] = 5 if pullback_valid else 0
    score += details["pullback"]

    if score >= 80:
        quality = "KUAT"
    elif score >= 60:
        quality = "SEDANG"
    else:
        quality = "LEMAH"

    return {
        "score": score,
        "quality": quality,
        "details": details,
        "explanation": (
            f"Setup memperoleh {score}/100. "
            f"Kualitas: {quality}."
        )
    }
