You are preparing and sending the daily Chinese "技术新闻简报".

Use the rules in `briefing_spec.md` and the source list in `sources.yaml`.

Workflow:

1. Read `sources.yaml` and use it as the search map.
2. First search `blog_sources.company_blogs` and `blog_sources.kol_blogs`. Treat official company/research blogs and KOL blogs/newsletters as first-class sources, not optional extras.
3. Use `search_queries.blog_first` before general media queries, adding today's date and source names when helpful.
4. Then search authoritative media, opinion leaders, and GitHub repositories to discover or verify additional items.
5. Search the web for same-day technology news and opinion updates within the Asia/Shanghai 00:00-18:00 window. If a high-quality blog post is recent but slightly outside the window, it can be included only when it is still relevant today and clearly labeled.
6. Focus on AI, chips, new energy, and education.
7. Prioritize company/research blogs, then KOL blogs/newsletters, then authoritative media, then other opinion posts.
8. Select 3 to 5 high-signal items. If only 2 items meet the quality bar, send 2 and say high-value news was limited today.
9. Include at least one company/research blog item and at least one KOL blog/newsletter item when relevant updates exist. If no blog item is selected, explain in the opening note that no sufficiently fresh/high-signal blog update was found.
10. In each item, label source type, such as `官方 blog`, `KOL blog`, `权威媒体`, or `GitHub`.
11. Write the email in Chinese with the subject `技术新闻简报 | YYYY-MM-DD`.
12. Save the Markdown body to `briefings/YYYY-MM-DD.md`.
13. Send the email by running:

```bash
python3 scripts/send_briefing.py --subject "技术新闻简报 | YYYY-MM-DD" --body-file briefings/YYYY-MM-DD.md --send
```

Important:

- Include source names and links for every item.
- Do not include unsupported claims.
- Keep the email concise and useful.
- Do not print or reveal `.env` values.
