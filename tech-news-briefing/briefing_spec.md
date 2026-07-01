# Technology News Briefing Specification

## Schedule

- Run at 18:00 every weekday, Asia/Shanghai time.
- Weekday means Monday through Friday for the first version.
- News window: same-day 00:00 to 18:00, Asia/Shanghai time.

## Coverage

- Focus areas: AI, chips, new energy, and education.
- Company scope: public companies with market capitalization over USD 100B or CNY 100B-equivalent influence, plus important technology unicorns.
- Opinion leader scope: CEOs, CTOs, prominent researchers, influential technical bloggers, and creators of high-star GitHub projects.
- Search map: use `sources.yaml` for official sources, media sources, opinion leaders, GitHub repositories, and query templates.

## Source Priority

1. Company and research blogs: official company blogs, research blogs, engineering blogs, technical blogs, and official product/research announcements.
2. KOL blogs and newsletters: personal blogs, technical essays, founder blogs, high-signal newsletters, and long-form posts from recognized builders/researchers.
3. Authoritative media: Reuters, Bloomberg, The Verge, TechCrunch, MIT Technology Review, 36Kr, LatePost, and similar high-signal outlets.
4. Other opinion sources: public social posts, podcasts, GitHub discussions, and repository updates from recognized industry voices.

## Blog Coverage Rules

- Every run must explicitly check the `blog_sources.company_blogs` and `blog_sources.kol_blogs` sections in `sources.yaml` before using general media search.
- Prefer at least one company/research blog item and at least one KOL blog/newsletter item in the final briefing when there are relevant same-day or recent updates.
- If no blog item is selected, add one sentence in the opening note explaining that no sufficiently fresh/high-signal company or KOL blog update was found in today's window.
- Label blog-derived items with the source type in the source sentence, for example: `来源：OpenAI News（官方 blog）...` or `来源：Simon Willison（KOL blog）...`.

## Selection Rules

- Pick 3 to 5 high-signal items when available.
- If fewer than 3 high-quality items exist, send 2 items and mention that today's high-value news volume was limited.
- Do not pad the briefing with low-impact marketing updates.
- Prefer launches, model releases, product availability, research breakthroughs, platform shifts, regulation-relevant industry changes, and unusually insightful commentary.
- Blog posts can be selected even if they are less "breaking" than media reports, as long as they provide first-party technical detail or a strong original viewpoint.
- Avoid repeating a topic covered in the last 48 hours unless there is a substantial new development.

## Email Format

- Subject: `技术新闻简报 | YYYY-MM-DD`
- Language: Chinese.
- Body structure:
  - Short opening sentence.
  - 3 to 5 numbered briefing items.
  - Each item includes a title, 2 to 3 sentence summary, and source links.
  - End with a short "今日观察" paragraph.
