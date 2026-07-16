"""
Creative media subtypes, modality mapping, and file allowlists.
"""
from typing import Dict, Set, Tuple

# subtype -> modality
MEDIA_SUBTYPES: Dict[str, str] = {
    "video_ad": "video",
    "print_ad": "image",
    "display_banner": "image",
    "ooh": "image",
    "radio_ad": "audio",
    "streaming_audio_ad": "audio",
    "email_marketing": "text",
    "blog_article": "text",
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}
TEXT_FILE_EXTENSIONS = {".txt", ".html", ".htm", ".pdf", ".docx"}

# display banners may be static images, GIFs, or short video clips
DISPLAY_BANNER_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

MAX_SIZE_BY_MODALITY = {
    "video": 500 * 1024 * 1024,
    "image": 50 * 1024 * 1024,
    "audio": 100 * 1024 * 1024,
    "text": 10 * 1024 * 1024,
}

HF_PREFIX_BY_MODALITY = {
    "video": "videos",
    "image": "images",
    "audio": "audio",
    "text": "text",
}

SUBTYPE_LABELS = {
    "video_ad": "Video advertisement",
    "print_ad": "Print ad (magazine/newspaper/flyer/brochure)",
    "display_banner": "Display/banner ad",
    "ooh": "Out-of-home ad (billboard/bus wrap/poster/transit)",
    "radio_ad": "Radio advertisement",
    "streaming_audio_ad": "Streaming audio advertisement",
    "email_marketing": "Email marketing (newsletter/promotional email)",
    "blog_article": "Blog post / article",
}


def modality_for_subtype(subtype: str) -> str:
    if subtype not in MEDIA_SUBTYPES:
        raise ValueError(f"Unknown media subtype: {subtype}")
    return MEDIA_SUBTYPES[subtype]


def allowed_extensions_for_subtype(subtype: str) -> Set[str]:
    modality = modality_for_subtype(subtype)
    if subtype == "display_banner":
        return DISPLAY_BANNER_EXTENSIONS
    if modality == "video":
        return VIDEO_EXTENSIONS
    if modality == "image":
        return IMAGE_EXTENSIONS
    if modality == "audio":
        return AUDIO_EXTENSIONS
    return TEXT_FILE_EXTENSIONS


def max_size_for_subtype(subtype: str) -> int:
    return MAX_SIZE_BY_MODALITY[modality_for_subtype(subtype)]


def resolve_modality_from_extension(subtype: str, ext: str) -> str:
    """
    For subtypes that accept multiple modalities (display_banner),
    resolve the actual modality from the file extension.
    """
    base = modality_for_subtype(subtype)
    if subtype == "display_banner":
        if ext in VIDEO_EXTENSIONS:
            return "video"
        return "image"
    return base


LITERAL_PREAMBLE = """Describe what is present in the creative in detailed plain text.
Name brands, products, logos, slogans, and publicly recognisable people when you can identify them confidently.
If someone looks famous but you are unsure of their identity, say so and describe them physically instead of guessing.
Do not invent claims that are not supported by what you see or hear.
Do not use vague marketing-analysis language like 'appears to target', 'may offend', or 'suggests the brand wants'.
Write in plain paragraphs."""

# Shared focus blocks injected into every subtype prompt
CELEBRITY_AND_PEOPLE = """
FAMOUS / PUBLIC FIGURES (critical):
- Identify any recognisable celebrity, actor, actress, sportsman/sportswoman, singer, influencer, politician, or other public figure by name when confident.
- State their known role/field (e.g. film actor, cricketer, singer) and how they appear in the creative (spokesperson, cameo, voiceover, photo, jersey, etc.).
- Note if multiple famous people appear, and who is featured most prominently.
- If a person resembles a celebrity but identity is uncertain, write: "Unidentified person resembling [description]; identity uncertain."
"""

BRAND_AWARENESS = """
BRAND AWARENESS (critical — agents need this):
- Primary brand name(s) and any parent company if shown or spoken.
- Product or service name, category (e.g. soft drink, bank, telecom, fashion), and what is being sold or promoted.
- Logos, wordmarks, pack shots, product colour schemes, taglines, jingles, and brand mascots — describe and transcribe exactly.
- Competing brands or other brand marks visible in the creative, if any.
- How strongly the brand is featured (opening logo, end card, repeated mentions, product close-ups, etc.).
- Any sponsorship, partnership, or co-branding (e.g. "Brand X presents", sports team jersey logos).
"""


PROMPTS: Dict[str, str] = {
    "video_ad": f"""Watch this video advertisement and transcribe everything you observe into detailed plain text.
{LITERAL_PREAMBLE}
{CELEBRITY_AND_PEOPLE}
{BRAND_AWARENESS}

Describe the following:

1. SCENES: For each scene or shot, describe what is visible — people, objects, setting, actions, movement.

2. PEOPLE: Physical appearance, approximate age, gender, clothing, any visible religious or cultural markers (e.g. clothing style, jewellery, head coverings). Call out famous people by name in this section too.

3. TEXT ON SCREEN: Transcribe every word of text, slogans, logos, or captions that appear. Note the language.

4. AUDIO (if detectable): Any spoken words, voiceover lines, song lyrics, celebrity names spoken, or notable sounds. Transcribe brand/product mentions verbatim.

5. PRODUCT / BRAND: Expand using the BRAND AWARENESS rules above. What product or service is advertised? How is the brand shown?

6. SETTING: Where does the ad take place? Indoor/outdoor, urban/rural, home/workplace/public space, any recognisable locations or venues.

7. SEQUENCE: Briefly describe the order of events — what happens first, then next, then last.

Be exhaustive. Prefer naming brands and public figures over vague descriptions.""",

    "print_ad": f"""This is a print advertisement (magazine/newspaper spread, flyer, or brochure).
Describe everything you see as detailed plain text.
{LITERAL_PREAMBLE}
{CELEBRITY_AND_PEOPLE}
{BRAND_AWARENESS}

Describe the following:

1. LAYOUT: Overall page structure — columns, panels, fold, white space.

2. HEADLINE AND COPY: Transcribe every headline, subhead, body paragraph, fine print, and slogan. Note the language.

3. IMAGERY: People, products, objects, illustrations, or photographs shown. Describe appearance and placement. Name recognisable people.

4. BRAND / LOGO: Expand using the BRAND AWARENESS rules above.

5. CTA: Any call-to-action, contact details, URLs, QR codes, or offers.

6. DESIGN ELEMENTS: Colors (literal), typography style if obvious, borders, icons.

Be exhaustive. Prefer naming brands and public figures over vague descriptions.""",

    "display_banner": f"""This is a web display or banner advertisement (static or animated).
Describe everything you observe as detailed plain text.
{LITERAL_PREAMBLE}
{CELEBRITY_AND_PEOPLE}
{BRAND_AWARENESS}

Describe the following:

1. FORMAT: Approximate aspect/shape if visible; static vs animated frames if applicable.

2. VISUALS: Imagery, characters, products, background, motion sequence if animated. Name recognisable people.

3. TEXT: Transcribe every word of on-banner copy, slogans, and disclaimers. Note the language.

4. BRAND / LOGO: Expand using the BRAND AWARENESS rules above.

5. CTA: Buttons, links, or offer language shown.

Be exhaustive. Prefer naming brands and public figures over vague descriptions.""",

    "ooh": f"""This is an out-of-home (OOH) advertisement such as a billboard, bus wrap, poster, or transit ad.
Describe everything you see as detailed plain text.
{LITERAL_PREAMBLE}
{CELEBRITY_AND_PEOPLE}
{BRAND_AWARENESS}

Describe the following:

1. PLACEMENT CONTEXT: What kind of OOH surface is shown if identifiable (billboard, bus, poster, shelter, etc.) and surrounding environment if visible.

2. VISUALS: Imagery, people, products, scale cues. Name recognisable people.

3. COPY: Transcribe every word of headline, body, slogans, and fine print. Note the language.

4. BRAND / LOGO: Expand using the BRAND AWARENESS rules above.

5. CTA: Phone numbers, URLs, QR codes, or offers if present.

Be exhaustive. Prefer naming brands and public figures over vague descriptions.""",

    "radio_ad": f"""This is a radio advertisement. Transcribe and describe the audio as detailed plain text.
{LITERAL_PREAMBLE}
{CELEBRITY_AND_PEOPLE}
{BRAND_AWARENESS}

Describe the following:

1. SPOKEN SCRIPT: Full transcript of spoken words and voiceover lines. Note language. If a famous person's voice or name is used, identify them when confident.

2. MUSIC / SFX: Background music style if identifiable, jingles, sound effects, silence. Note branded jingles.

3. BRAND / PRODUCT: Expand using the BRAND AWARENESS rules above. Transcribe every brand/product mention.

4. CTA: Phone numbers, URLs, slogans, or offers spoken.

5. STRUCTURE: Opening, middle, closing order of the spot.

Be exhaustive. Prefer naming brands and public figures over vague descriptions.""",

    "streaming_audio_ad": f"""This is a streaming audio advertisement. Transcribe and describe the audio as detailed plain text.
{LITERAL_PREAMBLE}
{CELEBRITY_AND_PEOPLE}
{BRAND_AWARENESS}

Describe the following:

1. SPOKEN SCRIPT: Full transcript of spoken words and voiceover lines. Note language. Identify celebrity voices/names when confident.

2. MUSIC / SFX: Background music, jingles, sound effects. Note branded jingles.

3. BRAND / PRODUCT: Expand using the BRAND AWARENESS rules above.

4. CTA: URLs, app names, promo codes, or offers spoken.

5. STRUCTURE: Opening, middle, closing order of the spot.

Be exhaustive. Prefer naming brands and public figures over vague descriptions.""",

    "email_marketing": f"""This is email marketing creative (newsletter or promotional email), provided as text or a document image/PDF.
Produce a detailed plain-text brief of the email content.
{LITERAL_PREAMBLE}
{CELEBRITY_AND_PEOPLE}
{BRAND_AWARENESS}

Describe / extract:

1. SUBJECT / PREHEADER: If present.

2. FROM / BRAND: Sender or brand identity if present — expand using BRAND AWARENESS rules.

3. BODY STRUCTURE: Sections, headlines, paragraphs — transcribe the copy. Note any celebrity or spokesperson names.

4. OFFERS / CTA: Promotions, buttons, links, codes.

5. FOOTER / LEGAL: Unsubscribe or legal lines if present.

Be exhaustive. Prefer naming brands and public figures over vague descriptions.""",

    "blog_article": f"""This is a blog post or article (SEO/thought-leadership content), provided as text or a document.
Produce a detailed plain-text brief of the article.
{LITERAL_PREAMBLE}
{CELEBRITY_AND_PEOPLE}
{BRAND_AWARENESS}

Describe / extract:

1. TITLE / HEADLINES: Main title and section headings.

2. BODY: Summarize by section while preserving key claims, quotes, celebrity/public-figure mentions, and product/brand mentions with enough detail for a reader who cannot see the original. Prefer direct excerpts for slogans and CTAs.

3. AUTHOR / BYLINE: If present. Note if the author is a known public figure.

4. CTA / LINKS: Calls to action, product mentions, related links if present.

Be exhaustive. Prefer naming brands and public figures over vague descriptions.""",
}


def prompt_for_subtype(subtype: str) -> str:
    if subtype not in PROMPTS:
        raise ValueError(f"No prompt for subtype: {subtype}")
    return PROMPTS[subtype]


def validate_subtype(subtype: str) -> Tuple[str, str]:
    """Returns (subtype, modality). Raises ValueError if invalid."""
    modality = modality_for_subtype(subtype)
    return subtype, modality
