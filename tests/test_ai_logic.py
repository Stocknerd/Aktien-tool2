from types import SimpleNamespace

import ai_logic


DISCLAIMER = "Hinweis: Keine Anlageberatung. Bilde dir eine eigene Meinung."


def test_tool_caption_without_api_key_contains_concrete_evaluation_question(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    caption = ai_logic.get_tool_promotion_caption(
        False,
        "Beispiel AG",
        "BSP",
        ["KGV: 12", "Umsatzwachstum: 4 %"],
    )

    assert "Chance oder Risiko: Wie bewertest du Beispiel AG?" in caption
    assert caption.endswith(DISCLAIMER)
    assert len(caption) <= 280


def test_tool_caption_adds_discussion_question_before_final_disclaimer(monkeypatch):
    generated = (
        "📊 Beispiel AG wirkt günstig bewertet. "
        "Mehr Analysen & dieses Tool findest du auf schatzsuche40.de. "
        "#Aktien #Boerse\n\n"
        + DISCLAIMER
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=generated))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_logic, "OpenAI", lambda api_key: client)

    caption = ai_logic.get_tool_promotion_caption(
        False,
        "Beispiel AG",
        "BSP",
        ["KGV: 12", "Umsatzwachstum: 4 %"],
    )

    question = "Chance oder Risiko: Wie bewertest du Beispiel AG?"
    assert question in caption
    assert caption.index(question) < caption.index(DISCLAIMER)
    assert caption.endswith(DISCLAIMER)
    assert len(caption) <= 280


def test_comparison_caption_asks_for_a_choice(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    caption = ai_logic.get_tool_promotion_caption(
        True,
        "Alpha AG vs. Beta SE",
        "AAA / BBB",
        ["KGV: 10 vs. 18"],
    )

    assert "Wer ist für dich aktuell stärker: Alpha AG vs. Beta SE?" in caption
    assert caption.endswith(DISCLAIMER)
    assert len(caption) <= 280


def test_long_comparison_question_preserves_both_candidates(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    names = (
        "Alpha International Technologies Holding AG mit langem Namen vs. "
        "Beta Global Consumer Products Corporation mit langem Namen"
    )

    caption = ai_logic.get_tool_promotion_caption(
        True,
        names,
        "AAA / BBB",
        ["KGV: 10 vs. 18"],
    )

    question = caption.split("\n\n")[-2]
    assert "Alpha International" in question
    assert "Beta Global" in question
    assert question.endswith("?")
    assert "schatzsuche40.de" in caption
    assert len(caption) <= 280


def test_subject_matter_hint_is_preserved_and_variant_disclaimer_is_replaced(monkeypatch):
    generated = (
        "📊 Hinweis: Das KGV liegt unter dem Branchenwert. "
        "Mehr Analysen auf schatzsuche40.de.\n\n"
        "Disclaimer: Keine Anlageberatung; eigene Recherche ist nötig."
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=generated))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_logic, "OpenAI", lambda api_key: client)

    caption = ai_logic.get_tool_promotion_caption(
        False,
        "Beispiel AG",
        "BSP",
        ["KGV: 12"],
    )

    assert "Hinweis: Das KGV liegt unter dem Branchenwert" in caption
    assert "Disclaimer:" not in caption
    assert caption.lower().count("keine anlageberatung") == 1
    assert caption.endswith(DISCLAIMER)


def test_empty_model_caption_uses_the_content_fallback(monkeypatch):
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_logic, "OpenAI", lambda api_key: client)

    caption = ai_logic.get_tool_promotion_caption(
        False,
        "Beispiel AG",
        "BSP",
        ["KGV: 12"],
    )

    assert "Alle Daten & das Analysetool: schatzsuche40.de." in caption
    assert "Chance oder Risiko: Wie bewertest du Beispiel AG?" in caption
    assert caption.endswith(DISCLAIMER)
    assert len(caption) <= 280


def test_normal_sentence_containing_no_advice_claim_is_not_treated_as_disclaimer(monkeypatch):
    generated = (
        "Wir bieten keine Anlageberatung, sondern neutrale Kennzahlen. "
        "Mehr Analysen auf schatzsuche40.de."
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=generated))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_logic, "OpenAI", lambda api_key: client)

    caption = ai_logic.get_tool_promotion_caption(
        False,
        "Beispiel AG",
        "BSP",
        ["KGV: 12"],
    )

    assert "Wir bieten keine Anlageberatung, sondern neutrale Kennzahlen." in caption
    assert "schatzsuche40.de" in caption
    assert caption.endswith(DISCLAIMER)
    assert len(caption) <= 280


def test_emoji_prefixed_single_line_disclaimer_is_replaced_not_duplicated(monkeypatch):
    generated = "Solide Kennzahlen.\n⚠️ Hinweis: Keine Anlageberatung."
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=generated))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_logic, "OpenAI", lambda api_key: client)

    caption = ai_logic.get_tool_promotion_caption(
        False,
        "Beispiel AG",
        "BSP",
        ["KGV: 12"],
    )

    assert "⚠️ Hinweis" not in caption
    assert caption.lower().count("keine anlageberatung") == 1
    assert caption.endswith(DISCLAIMER)
