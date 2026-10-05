"""Item 1A extraction against a synthetic 10-K that mimics the layouts seen in
real filings (Apple, Microsoft, NVIDIA, JPMorgan, Coca-Cola, Amazon, 2025-26)."""

from app.providers.edgar_provider import parse_risk_factors

B = 'style="font-weight:700"'
BI = 'style="font-weight:700;font-style:italic"'
BODY = "This is body text describing the risk in detail. " * 12


def doc(section: str, tail: str = "") -> str:
    return f"""<html><body>
    <div>Table of Contents</div>
    <div><span>Item 1A.</span></div><div><span>Risk Factors</span></div><div>9</div>
    <div><span>Item 1B.</span></div><div>Unresolved Staff Comments</div><div>20</div>
    <div>Item 1. Business</div><div>{"Business overview text. " * 40}</div>
    <div>See Item 1A of this Form 10-K under the heading Risk Factors.</div>
    {section}
    <div><span {B}>Item 1B. Unresolved Staff Comments</span></div><div>None.</div>
    <div><span {B}>Item 2. Properties</span></div><div>{"Properties text. " * 30}</div>
    {tail}
    </body></html>"""


def test_categories_and_italic_titles_apple_style():
    html = doc(f"""
      <div><span {B}>Item 1A. Risk Factors</span></div>
      <div>The following summarizes factors that could affect the Company.</div>
      <div><span {B}>Macroeconomic and Industry Risks</span></div>
      <div><span {BI}>The Company depends on global economic conditions.</span></div>
      <div>{BODY}</div>
      <div>Apple Inc. | 2025 Form 10-K | 7</div>
      <div>{BODY}</div>
      <div><span {BI}>Competition is intense.</span></div>
      <div>{BODY}</div>
      <div><span {B}>Financial Risks</span></div>
      <div><span {BI}>Tax rates may change.</span></div>
      <div>{BODY}</div>
    """)
    risks = parse_risk_factors(html, max_chars_per_risk=None)
    assert [r.title for r in risks] == [
        "The Company depends on global economic conditions.",
        "Competition is intense.",
        "Tax rates may change.",
    ]
    assert [r.category for r in risks] == ["Macroeconomic and Industry Risks"] * 2 + ["Financial Risks"]
    assert "Form 10-K |" not in risks[0].text  # page footer dropped


def test_cross_reference_after_section_is_not_mistaken_for_it():
    # A late 'Refer to "Item 1A. Risk Factors"' has no Item 1B after it; it must not win.
    tail = f'<div>Item 1A. Risk Factors – see above</div><div>{"Financial statements text. " * 400}</div>'
    html = doc(f"""
      <div><span {B}>Item 1A. Risk Factors</span></div>
      <div><span {BI}>A real risk.</span></div><div>{BODY * 6}</div>
    """, tail)
    risks = parse_risk_factors(html)
    assert [r.title for r in risks] == ["A real risk."]


def test_microsoft_style_caps_categories_runin_titles_subheadings_and_page_headers():
    html = doc(f"""
      <p><span {B}>ITEM 1A. RIS K FACTORS</span></p>
      <p>Our operations are subject to various risks.</p>
      <p>STRATEGIC AND COMPETITIVE RISKS</p>
      <p><span {B}>We face intense competition across all markets for our products.</span></p>
      <p><span {BI}>Competition in the technology sector</span></p>
      <p>{BODY}</p>
      <p>14</p><p>PART I</p><p>Item 1A</p>
      <p><span {BI}>Business model competition</span></p>
      <p>{BODY}</p>
      <p><span {B}>Our cloud strategy requires substantial investments in datacenters.</span><span> We have made {BODY}</span></p>
    """)
    risks = parse_risk_factors(html, max_chars_per_risk=None)
    assert [r.title for r in risks] == [
        "We face intense competition across all markets for our products.",
        "Our cloud strategy requires substantial investments in datacenters.",
    ]
    assert all(r.category == "STRATEGIC AND COMPETITIVE RISKS" for r in risks)
    assert risks[0].text.startswith("Competition in the technology sector:")
    assert "Business model competition:" in risks[0].text
    assert "PART I" not in risks[0].text
    assert risks[1].text.startswith("We have made")


def test_summary_bullets_and_intro_are_skipped_nvidia_style():
    html = doc(f"""
      <div><span {B}>Item 1A. Risk Factors</span></div>
      <div><span {BI}>The following risk factors should be considered.</span></div>
      <div><span {B}>Risk Factors Summary</span></div>
      <div><span {B}>Risks Related to Our Industry</span></div>
      <div>• Failure to meet the needs of our markets may hurt results.</div>
      <div><span {B}>Risks Related to Our Industry</span></div>
      <div><span {BI}>Failure to meet the needs of our markets may hurt results.</span></div>
      <div>{BODY * 6}</div>
    """)
    risks = parse_risk_factors(html)
    assert len(risks) == 1
    assert risks[0].category == "Risks Related to Our Industry"


def test_long_bodies_are_trimmed_at_sentence_end():
    html = doc(f"""
      <div><span {B}>Item 1A. Risk Factors</span></div>
      <div><span {BI}>A risk.</span></div><div>{BODY * 10}</div>
    """)
    risk = parse_risk_factors(html, max_chars_per_risk=300)[0]
    assert len(risk.text) <= 302
    assert risk.text.endswith(". …")


def test_document_without_item_1a_returns_nothing():
    assert parse_risk_factors("<html><body><div>Annual report</div></body></html>") == []
