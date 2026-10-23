# The 201 Invitational — Weekly Sleeper Auto-Update Pack

This is a GitHub-ready version of the existing **The 201 Invitational** website. It keeps the current design and historical league archive, and adds an automatic weekly Sleeper refresh for team lists, current standings, objective 2026 performance rankings, final matchup scores, and a downloadable all-matchups video **script**. No Sleeper password or API token is needed, because these endpoints are public and read-only.

**This ZIP does not publish anything on its own.** To activate, you need a GitHub account and to link that repository to **the existing Netlify project**, so the same public URL remains in use.

## Get it running — keep your existing Netlify URL

1. Extract this ZIP and create a private (or public) GitHub repository called `the-201-invitational`.
2. Upload **all** extracted files and folders to the **root** of that repository, preserving `.github/workflows/refresh.yml`, `site-template.html`, `public/index.html` and `netlify.toml`. Do not upload the ZIP file itself in place of its contents.
3. Open your existing Netlify project `bucolic-dasik-bae2a7` and navigate to **Project configuration > Developer settings > Continuous deployment > Repository**. Choose **Link repository**, then authorize GitHub and choose `the-201-invitational`. This connects the existing Netlify site, rather than creating a second one.
4. Verify Netlify publishes the `public` directory (the included `netlify.toml` does this); then check your familiar `https://bucolic-dasik-bae2a7.netlify.app/` address.
5. In GitHub, open **Actions > Refresh Sleeper scores and rankings > Run workflow** for a test refresh. The workflow will fetch Sleeper, generate and commit a new `public/index.html`, and Netlify will deploy it automatically. The scheduled run is weekly on Wednesdays at 14:00 UTC.
6. Open **Sleeper Hub** and **Power Rankings** to confirm the current data. Open **Weekly Wrap-Up** to download a factual all-matchups recap script. If the workflow fails, examine that GitHub Actions run; no new version gets deployed when the fetch/build step fails.

For detailed Netlify repository instructions: https://docs.netlify.com/build/git-workflows/repo-permissions-linking/

## Important boundaries

- The public site **is not yet a shared online CMS**: Commissioner Studio saves changes in your browser until you export them. Those browser edits are not automatically pushed into the GitHub repository or broadcast to other visitors. To keep editorial changes as the new base, edit `site-content.json` or provide an exported `index.html` for the content to be merged into it.
- Historical owner names, sprites, championship information, and league-history articles are kept as already authored. Linking Sleeper display names to historical real names is still an editorial step.
- Objective performance rankings use an explicit 40% PPG / 25% all-play / 20% recent PPG / 15% W% formula; they're *not* predictive dynasty rankings or subjective power rankings.
- Weekly **articles and narrated videos are not created/published automatically** by this package. Videos require original narration/production; the Week Wrap-Up page only generates a factual script that you can review.
- Before linking the repository, you should preserve any Commissioner Studio edits from your current live browser using **Edit Site > Publish / Backup > Export JSON**. The package starts from the V3 source data and does not carry over changes stored only on your computer.
- GitHub scheduled workflows can be delayed, particularly under load. Use **Run workflow** if you want a refresh sooner.
- When a live fetch is unavailable, the GitHub Action fails without publishing a guessed result. The included static `public/index.html` remains viewable.
- No claim is made that Sleeper's current 2026 data or league format has already been successfully verified; the scheduled run will fetch those details when connected.

## Technical layout

- `site-content.json` — persistent hand-curated content (historical seasons, articles, owner mapping, etc.)
- `site-template.html` — site layout, styling, and interaction code; **The 201 Weekly Wrap-Up** replaces preview video script with a rapid-fire results script
- `sleeper_sync.py` — fetches public, read-only league API data
- `build_site.py` — merges Sleeper data into the website and calculates latest game result list
- `public/index.html` — published output watched by Netlify
- `.github/workflows/refresh.yml` — scheduled / manual refresh job
- `netlify.toml` — sets the Netlify publish folder to `public`
